import os
import requests
from dotenv import load_dotenv
import json

load_dotenv()

url = os.getenv("RM_URL", "").rstrip("/")
api_key = os.getenv("RM_SECURITY_TOKEN")

print(f"Listing projects from {url}/projects.json")

headers = {
    "Content-Type": "application/json",
    "X-Redmine-API-Key": api_key
}

try:
    resp = requests.get(
        f"{url}/projects.json?limit=100", 
        headers=headers,
        timeout=10
    )
    print(f"Status: {resp.status_code}")
    
    if resp.status_code == 200:
        data = resp.json()
        print(f"Found {data['total_count']} projects.")
        for p in data['projects']:
            if p['id'] == 49:
                print(f"FOUND TARGET: ID: {p['id']} - Name: {p['name']} - Identifier: {p['identifier']}")
                break
    else:
        print(f"Response: {resp.text}")
except Exception as e:
    print(f"❌ Error: {e}")
