import httpx
import sys

# Test Streaming
print("--- Testing Streaming Response ---")
try:
    with httpx.stream("GET", "https://0c02b6a91d90.ngrok-free.app/chat_stream", params={"prompt": "Write a long poem about coding."}, timeout=120) as r:
        for chunk in r.iter_text():
            print(chunk, end="", flush=True)
    print("\n\n--- Done ---")
except Exception as e:
    print(f"\nError: {e}")