import os
import asyncio
from fastapi import FastAPI
from playwright.async_api import async_playwright
from playwright_stealth import stealth_async
import uvicorn

app = FastAPI()

# Global state to keep the browser alive
state = {
    "page": None,
    "browser": None,
    "playwright": None
}

async def init_browser():
    """Initializes the background browser once"""
    state["playwright"] = await async_playwright().start()
    state["browser"] = await state["playwright"].chromium.launch(
        headless=True, # Set to False if you want to watch it work
        args=["--disable-blink-features=AutomationControlled"]
    )
    # Load your saved login session
    state["context"] = await state["browser"].new_context(storage_state="auth.json")
    state["page"] = await state["context"].new_page()
    await stealth_async(state["page"])
    
    print("Connecting to ChatGPT...")
    await state["page"].goto("https://chatgpt.com/")
    
    # Wait for the chat box to ensure we are logged in
    try:
        await state["page"].wait_for_selector("#prompt-textarea", timeout=10000)
        print("API is READY and warm.")
    except:
        print("Error: Could not find chat box. Check auth.json or Cloudflare.")

@app.on_event("startup")
async def startup():
    asyncio.create_task(init_browser())

@app.get("/ask")
async def ask(prompt: str):
    page = state["page"]
    
    # 1. Clear any stuck modals (Stay logged out, etc.)
    try:
        await page.click("//a[contains(text(), 'Stay logged out')]", timeout=500)
    except:
        pass

    # 2. Type the prompt
    await page.fill("#prompt-textarea", prompt)
    await page.press("#prompt-textarea", "Enter")

    # 3. Wait for the response to finish
    # We look for the 'Stop' button and wait for it to disappear
    stop_selector = 'button[data-testid="stop-button"]'
    try:
        # Wait for generation to start
        await page.wait_for_selector(stop_selector, timeout=5000)
        # Wait for generation to end (button disappears)
        await page.wait_for_selector(stop_selector, state="hidden", timeout=90000)
    except:
        # If the answer was very short, the button might have appeared and vanished too fast
        await asyncio.sleep(2)

    # 4. Grab the latest message
    # ChatGPT uses articles/divs for messages. We want the last assistant one.
    replies = await page.query_selector_all('div[data-message-author-role="assistant"]')
    if replies:
        last_reply = replies[-1]
        text = await last_reply.inner_text()
        return {"response": text.strip()}
    
    return {"error": "Failed to grab response"}

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)