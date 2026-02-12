import os
import json
import base64
import requests
from typing import Optional, Dict, Any
from google.oauth2 import service_account
from google.oauth2 import credentials as authorized_user_credentials
from google.auth.transport.requests import Request as AuthRequest

class VertexWrapper:
    """
    Direct wrapper for Vertex AI Gemini API using Service Account credentials.
    Bypasses the 'User location not supported' error by using Enterprise Vertex AI endpoints.
    """
    def __init__(self, project_id: Optional[str] = None, location: str = "us-central1"):
        self.project_id = project_id
        self.location = location
        self.credentials = None
        self.model_name = "gemini-1.5-flash-001" # Vertex specific version name
        
        self._init_credentials()

    def _init_credentials(self):
        """Initialize credentials from Base64 env var or file"""
        # Try Base64 Env Var (For Render)
        b64_creds = os.getenv("GCP_CREDENTIALS_JSON_B64")
        if b64_creds:
            try:
                creds_json = base64.b64decode(b64_creds).decode('utf-8')
                creds_dict = json.loads(creds_json)
                
                # Check credential type
                cred_type = creds_dict.get('type')
                
                if cred_type == 'service_account':
                    self.credentials = service_account.Credentials.from_service_account_info(
                        creds_dict,
                        scopes=['https://www.googleapis.com/auth/cloud-platform']
                    )
                    if not self.project_id:
                        self.project_id = creds_dict.get('project_id')
                
                elif cred_type == 'authorized_user':
                    self.credentials = authorized_user_credentials.Credentials.from_authorized_user_info(
                        creds_dict,
                        scopes=['https://www.googleapis.com/auth/cloud-platform']
                    )
                    if not self.project_id:
                        # Authorized user credentials use quota_project_id
                        self.project_id = creds_dict.get('quota_project_id')
                
                return
            except Exception as e:
                print(f"Failed to load credentials from Base64: {e}")

        # Try local file
        local_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'gcp-credentials.json')
        if os.path.exists(local_path):
            try:
                with open(local_path, 'r') as f:
                    creds_dict = json.load(f)

                # Check credential type
                cred_type = creds_dict.get('type')
                
                if cred_type == 'service_account':
                    self.credentials = service_account.Credentials.from_service_account_file(
                        local_path,
                        scopes=['https://www.googleapis.com/auth/cloud-platform']
                    )
                    if not self.project_id:
                        self.project_id = creds_dict.get('project_id')
                
                elif cred_type == 'authorized_user':
                    # For file based authorized user, we need to load differently or reuse the dict logic
                    self.credentials = authorized_user_credentials.Credentials.from_authorized_user_info(
                        creds_dict,
                        scopes=['https://www.googleapis.com/auth/cloud-platform']
                    )
                    if not self.project_id:
                        self.project_id = creds_dict.get('quota_project_id')
                
                return
            except Exception as e:
                print(f"Failed to load credentials from file: {e}")

    def generate_content(self, prompt: str) -> Optional[str]:
        """Generate content using Vertex AI REST API"""
        if not self.credentials or not self.project_id:
            print("Vertex AI Not Configured: No credentials found")
            return None

        # Refresh token if needed
        if not self.credentials.valid:
            request = AuthRequest()
            self.credentials.refresh(request)

        token = self.credentials.token
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }

        url = f"https://{self.location}-aiplatform.googleapis.com/v1/projects/{self.project_id}/locations/{self.location}/publishers/google/models/{self.model_name}:generateContent"

        payload = {
            "contents": [{
                "role": "user",
                "parts": [{"text": prompt}]
            }],
            "generationConfig": {
                "temperature": 0.7,
                # "maxOutputTokens": 2048,
            }
        }

        try:
            response = requests.post(url, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()
            
            # Extract text from response
            # Response format: candidates[0].content.parts[0].text
            if 'candidates' in data and len(data['candidates']) > 0:
                parts = data['candidates'][0].get('content', {}).get('parts', [])
                if parts:
                    return parts[0].get('text', '')
            
            return None

        except Exception as e:
            print(f"Vertex AI Generation Error: {e}")
            if 'response' in locals() and hasattr(response, 'text'):
                print(f"API Response: {response.text}")
            return None
