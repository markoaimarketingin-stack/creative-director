import os
import requests
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("GROQ_API_KEY")
model = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
base_url = "https://api.groq.com/openai/v1/chat/completions"

headers = {
    "Authorization": f"Bearer {api_key}",
    "Content-Type": "application/json"
}

data = {
    "model": model,
    "messages": [{"role": "user", "content": "Hello, are you working?"}],
    "max_tokens": 10
}

print(f"Testing Groq API with model: {model}...")
try:
    response = requests.post(base_url, headers=headers, json=data)
    if response.status_code == 200:
        print("SUCCESS: Groq API is working!")
        print("Response:", response.json()['choices'][0]['message']['content'])
    else:
        print(f"FAILURE: Groq API failed with status code: {response.status_code}")
        print("Response:", response.text)
except Exception as e:
    print(f"ERROR: An error occurred: {e}")
