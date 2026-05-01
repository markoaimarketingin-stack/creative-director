import os
import httpx
import asyncio
import json
from dotenv import load_dotenv

load_dotenv()

async def check_groq():
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        print("GROQ_API_KEY not found in .env")
        return
    
    print("\n--- GROQ CHECK ---")
    url = "https://api.groq.com/openai/v1/models"
    headers = {"Authorization": f"Bearer {api_key}"}
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, headers=headers)
            if response.status_code == 200:
                print(f"Groq API Key: Valid (Status 200)")
                # Groq doesn't show limits in the models list, but let's try a dummy chat completion to see headers
                chat_url = "https://api.groq.com/openai/v1/chat/completions"
                payload = {
                    "model": "llama-3.1-8b-instant",
                    "messages": [{"role": "user", "content": "hi"}],
                    "max_tokens": 1
                }
                chat_resp = await client.post(chat_url, headers=headers, json=payload)
                if chat_resp.status_code == 200:
                    print("Groq Chat Check: Success")
                    # Extract rate limit headers if present
                    headers_of_interest = [
                        "x-ratelimit-limit-requests", 
                        "x-ratelimit-remaining-requests", 
                        "x-ratelimit-reset-requests",
                        "x-ratelimit-limit-tokens",
                        "x-ratelimit-remaining-tokens",
                        "x-ratelimit-reset-tokens"
                    ]
                    for h in headers_of_interest:
                        val = chat_resp.headers.get(h)
                        if val:
                            print(f" - {h}: {val}")
                else:
                    print(f"Groq Chat Check Error: {chat_resp.status_code}")
                    print(f"Response: {chat_resp.text}")
            else:
                print(f"Groq API Key Error: {response.status_code}")
                print(f"Response: {response.text}")
        except Exception as e:
            print(f"Groq Check failed: {e}")

async def check_gemini():
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("GEMINI_API_KEY not found in .env")
        return
    
    print("\n--- GEMINI CHECK ---")
    url = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url)
            if response.status_code == 200:
                data = response.json()
                models = [m['name'] for m in data.get("models", [])]
                print(f"Gemini API Key: Valid (Status 200)")
                print(f"Gemini Models available: {len(models)}")
                
                # Try to use the first available model that supports generateContent
                test_model = None
                for m in data.get("models", []):
                    if "generateContent" in m.get("supportedGenerationMethods", []):
                        test_model = m["name"]
                        break
                
                if test_model:
                    print(f"Testing with model: {test_model}")
                    gen_url = f"https://generativelanguage.googleapis.com/v1beta/{test_model}:generateContent?key={api_key}"
                    gen_resp = await client.post(gen_url, json={"contents": [{"parts": [{"text": "hi"}]}]})
                    if gen_resp.status_code == 200:
                        print("Gemini Content Generation: Success")
                    else:
                        print(f"Gemini Content Generation Error: {gen_resp.status_code}")
                        print(f"Response: {gen_resp.text}")
                else:
                    print("No model supporting generateContent found.")
            else:
                print(f"Gemini API Key Error: {response.status_code}")
                print(f"Response: {response.text}")
        except Exception as e:
            print(f"Gemini Check failed: {e}")

async def check_hf():
    api_key = os.getenv("HF_API_KEY")
    if not api_key:
        print("HF_API_KEY not found in .env")
        return
    
    print("\n--- HUGGING FACE CHECK ---")
    model = os.getenv("HF_IMAGE_MODEL", "black-forest-labs/FLUX.1-schnell")
    headers = {"Authorization": f"Bearer {api_key}"}
    
    async with httpx.AsyncClient() as client:
        try:
            whoami_url = "https://huggingface.co/api/whoami-v2"
            whoami_resp = await client.get(whoami_url, headers=headers)
            if whoami_resp.status_code == 200:
                user_data = whoami_resp.json()
                print(f"HF API Key: Valid (Status 200)")
                print(f" - User: {user_data.get('name')}")
            else:
                print(f"HF whoami Error: {whoami_resp.status_code}")

            # Try a very common model to verify inference capacity
            test_model = "gpt2" # Very lightweight and always available
            inf_url = f"https://api-inference.huggingface.co/models/{test_model}"
            inf_resp = await client.post(inf_url, headers=headers, json={"inputs": "The weather is"})
            
            print(f"HF Inference (GPT2) Status: {inf_resp.status_code}")
            if inf_resp.status_code == 200:
                print(" - Inference Success! (Key is working)")
                # Report rate limit headers if present
                for h in ["x-ratelimit-limit", "x-ratelimit-remaining", "x-ratelimit-reset"]:
                    val = inf_resp.headers.get(h)
                    if val:
                        print(f" - {h}: {val}")
            else:
                print(f" - Inference Status: {inf_resp.status_code}")
                print(f" - Response: {inf_resp.text[:100]}")
                
        except Exception as e:
            print(f"HF Check failed: {e}")


async def main():
    await check_groq()
    await check_gemini()
    await check_hf()

if __name__ == "__main__":
    asyncio.run(main())

