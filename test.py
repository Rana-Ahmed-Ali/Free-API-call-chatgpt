import httpx
import sys

# Test Streaming
print("--- Testing Streaming Response ---")
try:
    with httpx.stream("GET", "http://127.0.0.1:8000/chat_stream", params={"prompt": "Write a long poem about coding."}, timeout=120) as r:
        for chunk in r.iter_text():
            print(chunk, end="", flush=True)
    print("\n\n--- Done ---")
except Exception as e:
    print(f"\nError: {e}")