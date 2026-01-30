import streamlit as st
import requests
import os

# --- CONIFG ---
API_URL = "http://127.0.0.1:8000/chat_stream"
st.set_page_config(page_title="Code Doctor 🚑", layout="wide")

# --- CSS STYLES ---
st.markdown("""
<style>
    .stTextArea textarea {
        font-family: 'Fira Code', monospace;
    }
    .success-box {
        padding: 1rem;
        border-radius: 0.5rem;
        background-color: #d4edda;
        color: #155724;
        border: 1px solid #c3e6cb;
    }
</style>
""", unsafe_allow_html=True)

# --- HEADER ---
st.title("🚑 Code Doctor: AI Auto-Fixer")
st.markdown("Upload your code files, describe the issue, and let the AI fix it for you.")

# --- SIDEBAR ---
with st.sidebar:
    st.header("Settings")
    api_status = st.empty()
    try:
        # Check if API is alive (simple ping check)
        requests.get("http://127.0.0.1:8000/ask?prompt=ping", timeout=3)
        api_status.success("🟢 API Connected")
    except:
        api_status.error("🔴 API Offline")
        st.warning("Make sure 'python paki_api.py' is running!")

    st.markdown("---")
    st.info("💡 **Tip:** Use specific instructions like 'Optimize loop' or 'Add comments'.")

# --- MAIN INPUT ---
uploaded_files = st.file_uploader("📂 Select Python files", accept_multiple_files=True, type=['py', 'js', 'html', 'css', 'json', 'md'])
instruction = st.text_area("📝 What should I fix/improve?", placeholder="e.g. Fix bugs, add type hints, and optimize performance.", height=100)

if st.button("🚀 Analyze & Fix Code", type="primary", disabled=not uploaded_files):
    
    for uploaded_file in uploaded_files:
        filename = uploaded_file.name
        content = uploaded_file.read().decode("utf-8")
        
        st.divider()
        st.subheader(f"📄 Processing: `{filename}`")
        
        # Display simplified preview
        with st.expander("View Original Code"):
            st.code(content, language='python')
        
        # Construct Prompt
        prompt = (
            f"Act as a Senior Software Engineer. Fix and improve the following code.\n"
            f"Filename: {filename}\n"
            f"User Instructions: {instruction}\n\n"
            f"Goals:\n1. Fix bugs.\n2. Optimize.\n3. Return FULL fixed code in a markdown block.\n\n"
            f"Code:\n```\n{content}\n```"
        )
        
        # Stream Response
        st.write("---")
        full_response = ""
        response_box = st.empty()

        try:
            # We use a simple loop with requests.get(stream=True)
            with requests.get("http://127.0.0.1:8000/chat_stream", params={"prompt": instruction + "\n\nOriginal Code:\n" + content}, stream=True, timeout=120) as r:
                for chunk in r.iter_content(chunk_size=1024):
                    if chunk:
                        text = chunk.decode("utf-8")
                        full_response += text
                        response_box.markdown(full_response + "▌")
            
            # Final render without cursor
            response_box.markdown(full_response)
            
            # Extract Code Logic
            import re
            code_blocks = re.findall(r'```(?:\w+)?\n(.*?)```', full_response, re.DOTALL)
            fixed_code = max(code_blocks, key=len).strip() if code_blocks else None
            
            if fixed_code:
                st.markdown('<div class="success-box">✅ Fix Generated Successfully!</div>', unsafe_allow_html=True)
                
                # Download Button
                st.download_button(
                    label=f"💾 Download Fixed `{filename}`",
                    data=fixed_code,
                    file_name=f"fixed_{filename}",
                    mime="text/plain"
                )
            else:
                st.warning("⚠️ No code block found in response.")

        except Exception as e:
            st.error(f"An error occurred: {str(e)}")

if not uploaded_files:
    st.info("👆 Upload a file to get started.")
