import os
import json
from google.oauth2 import service_account
from google.auth.transport.requests import Request
import requests

KEY_FILE = r"c:\Users\USER\OneDrive\LinkedIn_PersonalBrand\Post_Factory_App\GoogleCloudKeys\gen-lang-client-0439499588-5da0ae8ca0f6.json"

def check_api_status():
    try:
        creds = service_account.Credentials.from_service_account_file(
            KEY_FILE,
            scopes=['https://www.googleapis.com/auth/cloud-platform']
        )
        request = Request()
        creds.refresh(request)
        token = creds.token
        project_id = creds.project_id
        
        # Check Service Usage API
        url = f"https://serviceusage.googleapis.com/v1/projects/{project_id}/services/aiplatform.googleapis.com"
        
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        
        print(f"Checking API status: {url}")
        response = requests.get(url, headers=headers)
        
        if response.status_code == 200:
            print("Response:", json.dumps(response.json(), indent=2))
        else:
            print(f"Error {response.status_code}: {response.text}")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_api_status()
