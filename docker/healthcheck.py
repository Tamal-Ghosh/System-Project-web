"""A 200 unavailable response must not count as a healthy model."""
import json
import sys
import urllib.request
try:
    with urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=5) as response:
        ready=json.load(response).get('status') == 'ready'
except Exception:
    ready=False
sys.exit(0 if ready else 1)
