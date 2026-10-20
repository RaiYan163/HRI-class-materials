import google.generativeai as genai

# 🔑 Set your Gemini API key
genai.configure(api_key="your_gemini_api_key")  # Replace with your real key

# List all available models
models = genai.list_models()

print("Available Gemini Models:")
for model in models:
    print(f"- {model.name}")
