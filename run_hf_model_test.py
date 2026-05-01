import os
from pathlib import Path
import requests
import sys

# load .env from project root
env_path = Path(__file__).parent / '.env'
if env_path.exists():
    for line in env_path.read_text().splitlines():
        if '=' in line and not line.strip().startswith('#'):
            k,v = line.split('=',1)
            os.environ.setdefault(k.strip(), v.strip())

key = os.environ.get('HF_API_KEY')
model = os.environ.get('HF_IMAGE_MODEL') or 'black-forest-labs/FLUX.1-schnell'
if not key:
    print('NO_KEY')
    sys.exit(2)

url = f'https://router.huggingface.co/hf-inference/models/{model}'
headers = {'Authorization': f'Bearer {key}'}
payload = {"inputs": "Test prompt for quota check: generate a small image placeholder."}

print('POST', url)
try:
    r = requests.post(url, headers=headers, json=payload, timeout=30)
except Exception as e:
    print('REQUEST ERROR', e)
    sys.exit(3)

print('STATUS', r.status_code)
for k in r.headers:
    kl = k.lower()
    if 'rate' in kl or 'limit' in kl or 'x-ratelimit' in kl or 'retry' in kl:
        print(k+':', r.headers[k])

text = r.text
if len(text)>1000:
    text = text[:1000] + '...'
print('BODY', text)
