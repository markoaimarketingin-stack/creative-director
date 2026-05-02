import os
from huggingface_hub import InferenceClient
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("HF_API_KEY")
model = os.getenv("HF_IMAGE_MODEL", "black-forest-labs/FLUX.1-schnell")

print(f"Testing Hugging Face InferenceClient with model: {model}...")

try:
    client = InferenceClient(model=model, token=api_key)
    
    # Simple image generation request
    image = client.text_to_image("A futuristic car")
    
    # If it doesn't raise an exception, it's working
    print("SUCCESS: Hugging Face API key is VALID and working!")
    
    output_path = "scratch/hf_client_test.jpg"
    image.save(output_path)
    print(f"Sample image saved to: {output_path}")

except Exception as e:
    print(f"FAILURE: Hugging Face API check failed.")
    print(f"Error details: {e}")
    
    # Try a simple identity check
    print("\nAttempting to check user identity...")
    import requests
    headers = {"Authorization": f"Bearer {api_key}"}
    whoami_resp = requests.get("https://huggingface.co/api/whoami-v2", headers=headers)
    if whoami_resp.status_code == 200:
        print("SUCCESS: API Key is valid for account:", whoami_resp.json().get("name"))
    else:
        print(f"FAILURE: API Key identity check failed with status {whoami_resp.status_code}")
        print("Response:", whoami_resp.text)
