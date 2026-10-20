import os
from dotenv import load_dotenv
load_dotenv()

from openai import OpenAI
import traceback

# Create client instance
client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])

def generate_image(prompt: str, size: str = "1024x1024"):
    try:
        # Attempt to generate the image
        result = client.images.generate(
            model="dall-e-2",  # Try also "dall-e-3" if enabled on your account
            prompt=prompt,
            size=size
        )
        image_url = result.data[0].url
        return image_url

    except Exception as e:
        # Print full stack trace
        print("Exception occurred:")
        traceback.print_exc()
        return f"Error generating image: {e}"

if __name__ == "__main__":
    user_prompt = input("Enter your image prompt: ")
    url = generate_image(user_prompt)
    print(f"\nGenerated Image URL:\n{url}")
