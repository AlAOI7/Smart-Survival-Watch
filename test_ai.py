import os
from dotenv import load_dotenv
import google.generativeai as genai

load_dotenv()
key = os.getenv("GEMINI_API_KEY")
print(f"Key loaded: {bool(key)}")
genai.configure(api_key=key)
try:
    model = genai.GenerativeModel('gemini-1.5-flash')
    r = model.generate_content("hello")
    print(r.text)
except Exception as e:
    import traceback
    traceback.print_exc()
