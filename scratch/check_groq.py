import os
import httpx
import asyncio
from dotenv import load_dotenv

load_dotenv()

async def check_groq():
    api_key = os.getenv("GROQ_API_KEY")
    model = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
    fallback = os.getenv("GROQ_FALLBACK_MODELS", "")

    if not api_key:
        print("GROQ_API_KEY not found in .env")
        return

    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": "Say 'Groq is working!' in exactly 4 words."}],
        "temperature": 0.1,
        "max_tokens": 20,
    }

    async with httpx.AsyncClient(timeout=30) as client:
        try:
            response = await client.post(url, headers=headers, json=payload)
            if response.status_code == 200:
                content = response.json()["choices"][0]["message"]["content"]
                print(f"Groq API Key: VALID")
                print(f"Primary Model: {model}")
                print(f"Fallback Model: {fallback}")
                print(f"Test Response: {content.strip()}")
            else:
                print(f"Groq API Key: ERROR {response.status_code}")
                print(f"Detail: {response.text[:300]}")
        except Exception as e:
            print(f"Groq check failed: {e}")

asyncio.run(check_groq())
