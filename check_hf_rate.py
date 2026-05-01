import os, sys, requests
from pathlib import Path

# load .env if present
env_path = Path(__file__).parent / '.env'
if env_path.exists():
    for line in env_path.read_text().splitlines():
        if '=' in line and not line.strip().startswith('#'):
            k,v = line.split('=',1)
            os.environ.setdefault(k.strip(), v.strip())

key = os.environ.get('HF_API_KEY')
if not key:
    print('NO_KEY')
    sys.exit(2)

headers = {'Authorization': f'Bearer {key}'}
# Call whoami to validate token and inspect headers
try:
    r = requests.get('https://huggingface.co/api/whoami-v2', headers=headers, timeout=15)
except Exception as e:
    print('ERROR', e)
    sys.exit(3)

print('STATUS', r.status_code)
for h in ['x-ratelimit-limit','x-ratelimit-remaining','x-ratelimit-reset','X-RateLimit-Limit','X-RateLimit-Remaining','X-RateLimit-Reset']:
    if h in r.headers:
        print(h, r.headers[h])

try:
    body = r.json()
    print('USER', body.get('id') or body.get('name') or str(body)[:200])
except Exception:
    text = r.text
    if len(text)>800:
        text = text[:800]+'...'
    print('BODY', text)

# Also query the inference model metadata endpoint for headers
try:
    r2 = requests.get('https://api-inference.huggingface.co/models/gpt2', headers=headers, timeout=15)
    print('\nINFERENCE STATUS', r2.status_code)
    for k,v in r2.headers.items():
        if k.lower().startswith('x-ratelimit'):
            print(k, v)
    tb = r2.text
    if len(tb)>400:
        tb = tb[:400]+'...'
    print('INFERENCE BODY', tb)
except Exception as e:
    print('INFERENCE ERROR', e)
