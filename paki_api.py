import os
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from playwright.async_api import async_playwright
from playwright_stealth import Stealth
import uvicorn

# Global state
state = {
    "page": None,
    "browser": None,
    "playwright": None,
    "context": None
}

@asynccontextmanager
async def lifespan(app: FastAPI):
    # --- STARTUP ---
    print("Initializing Playwright (Proactor Loop)...")
    state["playwright"] = await async_playwright().start()
    
    # Launching Headless (change to headless=False if you want to see the browser)
    # We use channel="chrome" to match the browser used for login
    try:
        state["browser"] = await state["playwright"].chromium.launch(
            channel="chrome",
            headless=False, # CHANGED TO FALSE FOR DEBUGGING & STABILITY
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox"
            ]
        )
    except Exception as e:
        print(f"Could not launch Chrome: {e}. Falling back to Chromium.")
        state["browser"] = await state["playwright"].chromium.launch(
            headless=False,
            args=["--disable-blink-features=AutomationControlled"]
        )
    
    if not os.path.exists("auth.json"):
        print("ERROR: auth.json not found! Run save_auth.py first.")
    else:
        print("Loading session and warming up ChatGPT...")
        state["context"] = await state["browser"].new_context(storage_state="auth.json")
        state["page"] = await state["context"].new_page()
        
        # Apply stealth
        stealth = Stealth()
        await stealth.apply_stealth_async(state["page"])

        print("Navigating to ChatGPT...")
        # Increased timeout to 60s and using 'domcontentloaded' to return faster
        await state["page"].goto("https://chatgpt.com/", timeout=60000, wait_until="domcontentloaded")
        
        try:
            # Wait for the chat box (increased timeout)
            await state["page"].wait_for_selector("#prompt-textarea", timeout=60000)
            print("--- SUCCESS: PAKI API IS READY AND WARM ---")
        except:
            print("WARNING: Chat box not found. You might be stuck on Cloudflare or a login screen.")

    yield  # Server runs here

    # --- SHUTDOWN ---
    print("Shutting down...")
    # On Windows, background processes often throw errors during shutdown. 
    # We use a try-except to ignore the 'Event loop is closed' message.
    try:
        if state["browser"]:
            await state["browser"].close()
        if state["playwright"]:
            await state["playwright"].stop()
    except:
        pass

app = FastAPI(lifespan=lifespan)

@app.get("/ask")
async def ask(prompt: str):
    if not state["page"]:
        return {"error": "Browser not initialized. Check if auth.json is valid."}
    
    page = state["page"]
    
    try:
        # 1. Fast cleanup (Non-blocking check)
        # This checks if the element exists immediately without waiting 500ms
        popup = page.locator("//a[contains(text(), 'Stay logged out')]")
        if await popup.is_visible():
            await popup.click()

        # 2. Type the prompt
        await page.fill("#prompt-textarea", prompt)
        await page.press("#prompt-textarea", "Enter")

        # 3. Wait for response
        stop_selector = 'button[data-testid="stop-button"]'
        
        # Wait for the AI to start (stop button appears)
        await page.wait_for_selector(stop_selector, timeout=10000)
        
        # Wait for the AI to finish (stop button disappears)
        # Timeout=0 means "wait forever/until done"
        await page.wait_for_selector(stop_selector, state="hidden", timeout=0)
        
        # Tiny wait to ensure DOM update (Reduced from 0.8s to 0.1s)
        await asyncio.sleep(0.1)

        # 4. Grab the last message
        replies = await page.query_selector_all('div[data-message-author-role="assistant"]')
        if replies:
            text = await replies[-1].inner_text()
            return {"response": text.strip()}
            
    except Exception as e:
        # In case of failure, refresh the page to reset for the next request
        await page.reload()
        return {"error": f"Task failed: {str(e)}. Page reloaded."}

    return {"error": "No response captured."}

@app.get("/chat_stream")
async def chat_stream(prompt: str):
    if not state["page"]:
        return StreamingResponse(iter(["Error: Browser not initialized.\n"]), media_type="text/plain")
    
    page = state["page"]
    
    async def response_generator():
        try:
            # 1. Clear popups
            popup = page.locator("//a[contains(text(), 'Stay logged out')]")
            if await popup.is_visible():
                await popup.click()

            # 2. Send prompt
            await page.fill("#prompt-textarea", prompt)
            await page.press("#prompt-textarea", "Enter")

            # 3. Wait for generation to start (Stop button appears)
            # We give it 30s to start generating, which is plenty
            stop_selector = 'button[data-testid="stop-button"]'
            try:
                await page.wait_for_selector(stop_selector, timeout=30000)
            except:
                yield "Error: Generation failed to start."
                return

            # 4. Stream the response loop    
            last_text = ""
            while True:
                # Check if generating
                # We do NOT use a timeout here because we just want to peek at the state
                is_generating = await page.locator(stop_selector).is_visible()
                
                # Get the latest text
                replies = await page.query_selector_all('div[data-message-author-role="assistant"]')
                if replies:
                    current_text = await replies[-1].inner_text()
                    # Calculate chunk
                    if len(current_text) > len(last_text):
                        chunk = current_text[len(last_text):]
                        last_text = current_text
                        yield chunk
                
                if not is_generating:
                    break
                
                # Tuning this poll rate balances CPU vs Latency
                await asyncio.sleep(0.05)
            
            # Final sweep to ensure we got everything (sometimes one last update happens)
            replies = await page.query_selector_all('div[data-message-author-role="assistant"]')
            if replies:
                current_text = await replies[-1].inner_text()
                if len(current_text) > len(last_text):
                    yield current_text[len(last_text):]

        except Exception as e:
            yield f"Error: {str(e)}"

    return StreamingResponse(response_generator(), media_type="text/plain")

if __name__ == "__main__":
    # DO NOT set WindowsSelectorEventLoopPolicy here!
    # Playwright needs the default loop.
    uvicorn.run(app, host="127.0.0.1", port=8000)