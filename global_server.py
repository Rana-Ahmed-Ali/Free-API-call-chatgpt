import os
import sys
import subprocess
import time
import requests
from pyngrok import ngrok, conf

# --- CONFIG ---
PORT = 8000
AUTH_TOKEN = input("Enter your Ngrok Authtoken (from dashboard.ngrok.com): ").strip()

def main():
    print("==========================================")
    print("      🌍 GLOBAL 24/7 API SERVER 🌍      ")
    print("==========================================")
    
    # 1. Setup Ngrok Auth (Crucial for stability)
    if not AUTH_TOKEN:
        print("Error: Starting ngrok requires a free authtoken.")
        print("1. Go to https://dashboard.ngrok.com/get-started/your-authtoken")
        print("2. Copy the token")
        print("3. Run this script again and paste it.")
        return

    print("Configuring Ngrok...")
    conf.get_default().auth_token = AUTH_TOKEN
    
    # 2. Start the API locally (paki_api.py)
    print("Starting paki_api.py in background...")
    api_process = subprocess.Popen(
        [sys.executable, "paki_api.py"],
        cwd=os.getcwd(),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    
    # Wait for API to warm up
    print("Waiting for API to initialize (this takes ~15s)...")
    time.sleep(15)
    
    # Check if API is alive
    if api_process.poll() is not None:
        print("Error: paki_api.py crashed immediately.")
        print(api_process.stderr.read())
        return

    # 3. Create Tunnel
    try:
        public_url = ngrok.connect(PORT).public_url
        print("\n" + "="*60)
        print(f"🚀 YOUR GLOBAL API URL IS LIVE: {public_url}")
        print("="*60 + "\n")
        
        print(f"Example usage (Code Doctor):")
        print(f"API_URL = \"{public_url}/chat_stream\"")
        
        print("\nPress Ctrl+C to stop the server.")
        
        # Keep alive
        while True:
            if api_process.poll() is not None:
                print("\nError: paki_api.py crashed!")
                print("Last error:", api_process.stderr.read())
                break
            time.sleep(5)
            
    except KeyboardInterrupt:
        print("\nShutting down...")
    except Exception as e:
        print(f"\nTunnel error: {e}")
    finally:
        api_process.terminate()
        ngrok.kill()
        print("Server stopped.")

if __name__ == "__main__":
    main()
