import os
import httpx
import asyncio
from dotenv import load_dotenv

load_dotenv()

async def check_gemini():
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("GEMINI_API_KEY not found in .env")
        return
    
    url = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url)
            if response.status_code == 200:
                print(f"Gemini API Key: Valid (Status 200)")
                # Just show the first few models to confirm
                models = [m['name'] for m in response.json().get("models", [])]
                print(f"Gemini Models available: {len(models)}")
                target_models = ["models/gemini-1.5-flash", "models/gemini-1.5-flash-8b", "models/gemini-pro"]
                for tm in target_models:
                    if tm in models:
                        print(f" - {tm}: FOUND")
                    else:
                        print(f" - {tm}: NOT FOUND")
                
                print("\nOther available models (sample):")
                for m in models[:15]:
                    print(f" - {m}")
            else:
                print(f"Gemini API Key: Error {response.status_code}")
                print(f"Response: {response.text}")
        except Exception as e:
            print(f"Gemini Check failed: {e}")

async def check_hf():
    api_key = os.getenv("HF_API_KEY")
    if not api_key:
        print("HF_API_KEY not found in .env")
        return
    
    # Try a simple model info request
    model = os.getenv("HF_IMAGE_MODEL", "black-forest-labs/FLUX.1-schnell")
    url = f"https://router.huggingface.co/hf-inference/models/{model}"
    headers = {"Authorization": f"Bearer {api_key}"}
    
    async with httpx.AsyncClient() as client:
        try:
            # We don't want to actually generate an image, just check if the key works
            # Maybe check model info instead
            info_url = f"https://huggingface.co/api/models/{model}"
            response = await client.get(info_url, headers=headers)
            if response.status_code == 200:
                print(f"HF API Key: Valid for model info (Status 200)")
            else:
                print(f"HF API Key: Error {response.status_code} for model info")
                print(f"Response: {response.text}")

            # Try a small dummy request to inference API to see if it's unauthorized or rate limited
            # Use an empty body or something that triggers a specific error but not "Unauthorized"
            inf_resp = await client.post(url, headers=headers, json={"inputs": "test"})
            if inf_resp.status_code == 400:
                 # 400 is expected if we send bad inputs, but if it's 401 or 403 or 429 then it's a problem
                 # Actually, let's see the error body
                 print(f"HF Inference Check Status: {inf_resp.status_code}")
                 print(f"HF Inference Check Body: {inf_resp.text}")
            elif inf_resp.status_code == 200:
                print(f"HF Inference Check: Success (Status 200)")
            else:
                print(f"HF Inference Check: Status {inf_resp.status_code}")
                print(f"HF Inference Check Body: {inf_resp.text}")
                
        except Exception as e:
            print(f"HF Check failed: {e}")

async def main():
    await check_gemini()
    print("-" * 20)
    await check_hf()

if __name__ == "__main__":
    asyncio.run(main())
