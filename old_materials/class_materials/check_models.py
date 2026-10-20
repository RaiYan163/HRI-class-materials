import os
from dotenv import load_dotenv
load_dotenv()

import google.generativeai as genai

# 🔑 Set your Gemini API key
genai.configure(api_key=os.environ["GEMINI_API_KEY"])  # Replace with your real key

# List all available models
models = genai.list_models()

print("Available Gemini Models:")
for model in models:
    print(f"- {model.name}")
