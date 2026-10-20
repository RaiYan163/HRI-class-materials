from openai import OpenAI

client = OpenAI(api_key="your_openai_api_key")

def list_image_models():
    print("Available Image Generation Models:\n")
    try:
        models = client.models.list()
        for model in models.data:
            if "image" in model.id or "dall" in model.id.lower():
                print(f"- {model.id}")
    except Exception as e:
        print(f"Error listing models: {e}")

if __name__ == "__main__":
    list_image_models()
