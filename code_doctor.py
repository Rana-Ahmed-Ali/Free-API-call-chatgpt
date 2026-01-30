import httpx
import os
import sys

def main():
    print("==========================================")
    print("       🚑 CODE DOCTOR: AUTO-FIXER 🚑      ")
    print("==========================================")
    
    # 1. Get the file path
    file_path = input("Enter the path of the file to fix/improve: ").strip().strip('"')
    
    if not os.path.exists(file_path):
        print(f"Error: File '{file_path}' not found.")
        return

    # 2. Read the file
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
    except Exception as e:
        print(f"Error reading file: {e}")
        return

    # 3. Construct the prompt
    print(f"\nReading '{os.path.basename(file_path)}' ({len(content)} characters)...")
    prompt = (
        f"Act as a Senior Software Engineer. I am going to provide you with a code file. "
        f"Your goals are:\n"
        f"1. Fix any bugs.\n"
        f"2. Optimize performance.\n"
        f"3. Improve readability (add comments where necessary).\n"
        f"4. Provide the FULL fixed code inside a markdown code block.\n"
        f"5. Briefly explain the changes after the code.\n\n"
        f"Here is the code content:\n"
        f"```\n{content}\n```"
    )

    print("\n--- contacting ChatGPT (Streaming Response) ---\n")
    
    full_response = ""
    
    try:
        # 4. Stream the response from the local API
        with httpx.stream("GET", "http://127.0.0.1:8000/chat_stream", params={"prompt": prompt}, timeout=300) as r:
            if r.status_code != 200:
                print(f"Error: API returned status code {r.status_code}")
                # Try to print error message if available
                print(r.read().decode())
                return
                
            for chunk in r.iter_text():
                print(chunk, end="", flush=True)
                full_response += chunk
                
        print("\n\n------------------------------------------")
        print("          Analysis Complete")
        print("------------------------------------------")
        
        # 5. Extract Code Block logic
        import re
        code_blocks = re.findall(r'```(?:\w+)?\n(.*?)```', full_response, re.DOTALL)
        
        extracted_code = ""
        if code_blocks:
            # We assume the first or largest block is the main code
            # Let's join them just in case, or pick the largest
            extracted_code = max(code_blocks, key=len).strip()
        else:
            # Fallback for when GPT forgets the code blocks
            print("Warning: No markdown code blocks found in response.")
        
        # 6. Offer to save
        if extracted_code:
            save = input("\nDo you want to save the FIXED CODE to a file? (y/n): ").strip().lower()
            if save == 'y':
                # Create a suggested filename
                base, ext = os.path.splitext(file_path)
                new_filename = f"{base}_doctor_fixed{ext}" 
                
                with open(new_filename, "w", encoding="utf-8") as f:
                    f.write(extracted_code)
                print(f"✅ Success! Fixed code saved to: {new_filename}")
        else:
            print("No code to save found.")
            
    except httpx.ConnectError:
        print("\nError: Could not connect to Paki API.")
        print("Make sure 'python paki_api.py' is running in another terminal!")
    except Exception as e:
        print(f"\nAn error occurred: {e}")

if __name__ == "__main__":
    main()
