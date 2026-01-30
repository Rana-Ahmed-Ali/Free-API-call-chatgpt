import time
import os
from playwright.sync_api import sync_playwright
from playwright_stealth import Stealth

def run():
    if os.path.exists("auth.json"):
        print("Note: auth.json already exists. This will overwrite it.")

    # We need to use the Stealth context manager or manually apply it
    # The cleanest way with this library version is using the context manager approach
    # or manual application. Let's do manual application for simplicity with existing code structure.
    
    # Approach 2: Persistent Context (Better for Google Login evasion)
    # We point to a local user folder so Chrome treats it as a "real" profile session
    user_data_dir = os.path.join(os.getcwd(), "chrome_profile")
    
    # Approach 3: Connect to an EXISTING Chrome instance (CDP)
    # This is the gold standard for bypassing "Browser not secure" errors.
    # We ask the user to launch Chrome manually with a debugging port.
    
    print("="*80)
    print("GOOGLE LOGIN FIX: MANUAL CHROME LAUNCH REQUIRED")
    print("To bypass the 'Browser not secure' error, we must connect to your real Chrome.")
    print("Please follow these steps exactly:")
    print("="*80)
    print("1. Close ALL existing Chrome windows (Taskbar > Right Click > Close all windows).")
    print("2. Open your terminal (PowerShell or Command Prompt).")
    print("3. Run this command to start Chrome with debugging enabled:")
    print('   & "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe" --remote-debugging-port=9222 --user-data-dir="C:\\ChromeProfile_Dev"')
    print("   (Note: If Chrome is installed elsewhere, adjust the path)")
    print("="*80)
    
    input("4. Once Chrome is open, press ENTER here to connect...")

    with sync_playwright() as p:
        try:
            print("\nConnecting to Chrome on port 9222...")
            browser = p.chromium.connect_over_cdp("http://localhost:9222")
            context = browser.contexts[0]
            page = context.pages[0]
            print("Successfully connected to your Chrome!")
        except Exception as e:
            print(f"\nFATAL ERROR: Could not connect to Chrome. ({e})")
            print("Did you close all other Chrome windows first?")
            print("Did you run the command exactly as shown?")
            return

        print("Navigating to ChatGPT...")
        page.goto("https://chatgpt.com/?model=auto")
        
        print("\n" + "="*60)
        print("INSTRUCTIONS:")
        print("1. Log in manually in the Chrome window that just opened.")
        print("   (You should have NO issues with Google Login now!)")
        print("2. Wait until you see the 'Ask anything' chat box.")
        print("="*60 + "\n")
        
        input("Press ENTER here ONLY AFTER you have fully logged in and see the chat input box...")
        
        # Verify
        try:
            page.wait_for_selector("#prompt-textarea", timeout=3000)
            print("Session successfully detected!")
        except:
            print("Warning: Could not confirm chat box, saving anyway.")

        # Save the session to auth.json
        # Note: We save to the current directory
        context.storage_state(path="auth.json")
        
        print("\nSUCCESS: 'auth.json' has been created.")
        print("You can now close Chrome and run paki_api.py.")
        
        browser.close()

if __name__ == "__main__":
    run()
