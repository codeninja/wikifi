import httpx
import json

url = "http://localhost:11434/api/generate"
payload = {
    "model": "qwen3.6:27b",
    "prompt": "Say hello in JSON format: {\"message\": \"hello\"}",
    "stream": False,
    # "format": "json" # Removing this to see if it returns JSON in 'response'
}
response = httpx.post(url, json=payload, timeout=300.0)
print(response.json())
