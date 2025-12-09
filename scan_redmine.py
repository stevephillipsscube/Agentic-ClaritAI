import os
import requests
from dotenv import load_dotenv

load_dotenv()

base_url = os.getenv("RM_URL", "").rstrip("/")
api_key = os.getenv("RM_SECURITY_TOKEN")
headers = {"Content-Type": "application/json", "X-Redmine-API-Key": api_key}

print(f"Scanning for writeable endpoints on: {base_url}\n")

# Common Redmine paths
paths = [
    "",
    "/redmine",
    "/pm",
    "/projects"
]

payload = {
    "issue": {
        "project_id": 49,
        "tracker_id": 1,
        "status_id": 1,
        "subject": "Test - Path Scan",
        "description": "Testing path"
    }
}

for path in paths:
    url = f"{base_url}{path}/issues.json"
    print(f"Testing POST to: {url}")
    
    try:
        # Check OPTIONS first to see allowed methods
        opt_resp = requests.options(url, headers=headers, timeout=5)
        print(f"  OPTIONS Status: {opt_resp.status_code}")
        if 'Allow' in opt_resp.headers:
            print(f"  Allowed Methods: {opt_resp.headers['Allow']}")
        
        # Try POST
        resp = requests.post(url, json=payload, headers=headers, timeout=5)
        print(f"  POST Status: {resp.status_code}")
        
        if resp.status_code == 201:
            print("  ✅ SUCCESS! Found correct path.")
            print(f"  Update RM_URL to: {base_url}{path}")
            break
        elif resp.status_code != 404:
            print(f"  ⚠️ Interesting response: {resp.status_code}")
            print(f"  Response: {resp.text[:200]}")
            
    except Exception as e:
        print(f"  Error: {e}")
    print("-" * 40)
