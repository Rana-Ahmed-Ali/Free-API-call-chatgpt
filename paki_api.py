import os
import asyncio
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from playwright.async_api import async_playwright, Page, Browser, BrowserContext
from playwright_stealth import Stealth
import uvicorn

# ============================================================
# Global application state (single browser / page instance)
# ============================================================
state: dict[str, Page | Browser | BrowserContext | None] = {
    "playwright": None,
    "browser": None,
    "context": None,
    "page": None,
}

CHAT_URL = "https://chatgpt.com/"
PROMPT_SELECTOR = "#prompt-textarea"
STOP_BUTTON_SELECTOR = 'button[data-testid="stop-button"]'
ASSISTANT_SELECTOR = 'div[data-message-author-role="assistant"]'
POPUP_XPATH = "//a[contains(text(), 'Stay logged out')]"


# ============================================================
# Application lifespan (startup / shutdown)
# ============================================================
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Initializes Playwright and warms up ChatGPT session on startup.
    Ensures clean shutdown of browser resources.
    """
    print("Initializing Playwright...")

    state["playwright"] = await async_playwright().start()

    # ---- Launch browser ----
    try:
        state["browser"] = await state["playwright"].chromium.launch(
            channel="chrome",
            headless=False,  # set True for production
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
            ],
        )
    except Exception as e:
        print(f"Chrome launch failed ({e}), falling back to Chromium.")
        state["browser"] = await state["playwright"].chromium.launch(
            headless=False,
            args=["--disable-blink-features=AutomationControlled"],
        )

    # ---- Load authenticated context ----
    if not os.path.exists("auth.json"):
        print("ERROR: auth.json not found. Run save_auth.py first.")
    else:
        print("Loading session and warming up ChatGPT...")
        state["context"] = await state["browser"].new_context(
            storage_state="auth.json"
        )
        state["page"] = await state["context"].new_page()

        # Apply stealth once
        stealth = Stealth()
        await stealth.apply_stealth_async(state["page"])

        print("Navigating to ChatGPT...")
        await state["page"].goto(
            CHAT_URL,
            timeout=60_000,
            wait_until="domcontentloaded",
        )

        try:
            await state["page"].wait_for_selector(
                PROMPT_SELECTOR, timeout=60_000
            )
            print("SUCCESS: ChatGPT session is ready.")
        except Exception:
            print(
                "WARNING: Prompt box not found. "
                "You may be on a Cloudflare or login screen."
            )

    yield  # ---- Application runs here ----

    # ---- Shutdown ----
    print("Shutting down Playwright...")
    try:
        if state["context"]:
            await state["context"].close()
        if state["browser"]:
            await state["browser"].close()
        if state["playwright"]:
            await state["playwright"].stop()
    except Exception:
        # Avoid noisy shutdown errors on Windows
        pass


app = FastAPI(lifespan=lifespan)


# ============================================================
# Utility helpers
# ============================================================
async def dismiss_popup(page: Page) -> None:
    """
    Non-blocking popup dismissal.
    """
    popup = page.locator(POPUP_XPATH)
    # Check count first to avoid error if locator matches nothing
    if await popup.count() > 0 and await popup.first.is_visible():
        await popup.first.click()


async def get_last_assistant_message(page: Page) -> str | None:
    """
    Returns the text of the last assistant message, if any.
    """
    messages = await page.query_selector_all(ASSISTANT_SELECTOR)
    if not messages:
        return None
    return (await messages[-1].inner_text()).strip()


async def safe_fill_input(page: Page, prompt: str) -> None:
    """
    Safely fills the ChatGPT input box using evaluated JavaScript.
    This works much better for large multi-line prompts than page.fill().
    """
    # 1. Focus the element
    await page.focus(PROMPT_SELECTOR)
    
    # 2. Use JS to set the text content directly (bypass slow typing)
    # We must trigger an 'input' event so React/ChatGPT knows the text changed
    await page.evaluate(f"""
        const el = document.querySelector('{PROMPT_SELECTOR}');
        el.innerText = `{{}}`;
        el.dispatchEvent(new Event('input', {{ bubbles: true }}));
    """.format(prompt.replace('`', '\\`').replace('${', '\\${')))
    
    # 3. Small wait to let the UI react
    await asyncio.sleep(0.5)

# ============================================================
# /ask endpoint (non-streaming)
# ============================================================
@app.get("/ask")
async def ask(prompt: str):
    page: Page | None = state["page"]
    if not page:
        return {"error": "Browser not initialized or auth.json invalid."}

    try:
        await dismiss_popup(page)

        # Send prompt securely
        await safe_fill_input(page, prompt)
        await page.press(PROMPT_SELECTOR, "Enter")

        # Wait for generation to start
        await page.wait_for_selector(
            STOP_BUTTON_SELECTOR, timeout=15_000
        )

        # Wait until generation finishes (timeout=0 for infinite wait)
        await page.wait_for_selector(
            STOP_BUTTON_SELECTOR, state="hidden", timeout=0
        )

        # Allow final DOM paint
        await asyncio.sleep(0.1)

        response = await get_last_assistant_message(page)
        if response:
            return {"response": response}

        return {"error": "No response captured."}

    except Exception as e:
        # Reset page for next request
        await page.reload(wait_until="domcontentloaded")
        return {"error": f"Task failed: {e}. Page reloaded."}


# ============================================================
# /chat_stream endpoint (streaming)
# ============================================================
@app.get("/chat_stream")
async def chat_stream(prompt: str):
    page: Page | None = state["page"]
    if not page:
        return StreamingResponse(
            iter(["Error: Browser not initialized.\n"]),
            media_type="text/plain",
        )

    async def response_generator():
        try:
            await dismiss_popup(page)

            # Use JS-injected input (FASTER & SAFER)
            # This fixes the "Timeout 30000ms exceeded" error on large inputs
            # because we don't wait for 'typing' animation.
            await page.evaluate(f"""
                const el = document.querySelector('{PROMPT_SELECTOR}');
                el.innerText = `{prompt.replace('`', '\\`').replace('${', '\\${')}`;
                el.dispatchEvent(new Event('input', {{ bubbles: true }}));
            """)
            await asyncio.sleep(0.5)
            await page.press(PROMPT_SELECTOR, "Enter")

            # Wait for generation to start
            try:
                await page.wait_for_selector(
                    STOP_BUTTON_SELECTOR, timeout=30_000
                )
            except Exception:
                yield "Error: Generation did not start."
                return

            last_text = ""

            while True:
                is_generating = await page.locator(
                    STOP_BUTTON_SELECTOR
                ).is_visible()

                current_text = await get_last_assistant_message(page)
                if current_text and len(current_text) > len(last_text):
                    yield current_text[len(last_text):]
                    last_text = current_text

                if not is_generating:
                    break

                # Balanced polling (CPU vs latency)
                await asyncio.sleep(0.05)

            # Final sweep
            current_text = await get_last_assistant_message(page)
            if current_text and len(current_text) > len(last_text):
                yield current_text[len(last_text):]

        except Exception as e:
            yield f"Error: {e}"

    return StreamingResponse(response_generator(), media_type="text/plain")


# ============================================================
# Entrypoint
# ============================================================
if __name__ == "__main__":
    # IMPORTANT: Do NOT override event loop policy on Windows
    uvicorn.run(app, host="127.0.0.1", port=8000)