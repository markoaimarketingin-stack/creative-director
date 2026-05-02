import os
import requests
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("HF_API_KEY")
# Testing with a more standard model first to verify API key
test_model = "runwayml/stable-diffusion-v1-5"
api_url = f"https://api-inference.huggingface.co/models/{test_model}"

headers = {"Authorization": f"Bearer {api_key}"}

def query(payload):
    response = requests.post(api_url, headers=headers, json=payload)
    return response

print(f"Testing Hugging Face Image Generation with model: {test_model}...")
try:
    response = query({
        "inputs": "A simple cat sitting on a chair",
    })
    
    if response.status_code == 200:
        print("SUCCESS: Hugging Face API key is VALID and working with Stable Diffusion!")
    else:
        print(f"FAILURE: Hugging Face API failed with status code: {response.status_code}")
        print("Response:", response.text)

    # Now let's try the FLUX model again with a slight variation in URL or just double check
    flux_model = os.getenv("HF_IMAGE_MODEL", "black-forest-labs/FLUX.1-schnell")
    flux_url = f"https://api-inference.huggingface.co/models/{flux_model}"
    print(f"\nTesting original model: {flux_model}...")
    flux_response = requests.post(flux_url, headers=headers, json={"inputs": "test"})
    
    if flux_response.status_code == 200:
        print("SUCCESS: FLUX model is working!")
    else:
        print(f"FAILURE: FLUX model failed with status code: {flux_response.status_code}")
        print("Response:", flux_response.text)

except Exception as e:
    print(f"ERROR: An error occurred: {e}")
