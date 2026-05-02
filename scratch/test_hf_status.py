import os
import requests
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("HF_API_KEY")
model = os.getenv("HF_IMAGE_MODEL", "black-forest-labs/FLUX.1-schnell")
api_url = f"https://api-inference.huggingface.co/models/{model}"

headers = {"Authorization": f"Bearer {api_key}"}

def query(payload):
    response = requests.post(api_url, headers=headers, json=payload)
    return response

print(f"Testing Hugging Face Image Generation with model: {model}...")
try:
    response = query({
        "inputs": "A futuristic city at sunset, neon lights, high detail",
    })
    
    if response.status_code == 200:
        print("SUCCESS: Hugging Face Image Generation is working!")
        # Save the image to check if it's actually valid
        output_path = "scratch/hf_test_image.jpg"
        os.makedirs("scratch", exist_ok=True)
        with open(output_path, "wb") as f:
            f.write(response.content)
        print(f"Sample image saved to: {output_path}")
    elif response.status_code == 503:
        print("WARNING: Hugging Face model is loading (503). Try again in a few seconds.")
    else:
        print(f"FAILURE: Hugging Face API failed with status code: {response.status_code}")
        print("Response:", response.text)
except Exception as e:
    print(f"ERROR: An error occurred: {e}")
