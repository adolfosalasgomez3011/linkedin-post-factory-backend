"""
Test Vertex AI Imagen 3 image generation (same as MCP server)
"""
import os
import requests
import base64
from PIL import Image
import io

def test_vertex_imagen():
    """Test Vertex AI image generation with API key"""
    
    # Vertex AI configuration (same as MCP server)
    PROJECT_ID = 'gen-lang-client-0439499588'
    LOCATION = 'us-central1'
    MODEL_NAME = 'imagen-3.0-generate-001'
    
    # Get API key from environment
    google_key = os.getenv('GOOGLE_API_KEY', 'AIzaSyBzBhvo3CCk3rcyGNhcuKvQNjxT4pbPZfA')
    
    if not google_key or google_key == 'your-gemini-key-here':
        print("❌ GOOGLE_API_KEY not found")
        return False
    
    print(f"✅ API Key: {google_key[:20]}...")
    
    try:
        # Build endpoint URL
        url = f"https://{LOCATION}-aiplatform.googleapis.com/v1/projects/{PROJECT_ID}/locations/{LOCATION}/publishers/google/models/{MODEL_NAME}:predict"
        
        print(f"📡 Endpoint: {url}")
        
        # Prepare request
        data = {
            "instances": [{"prompt": "A professional modern office with technology and innovation"}],
            "parameters": {
                "sampleCount": 1,
                "aspectRatio": "16:9"
            }
        }
        
        print("🎨 Generating image...")
        
        # Make request
        response = requests.post(
            url,
            headers={
                'Content-Type': 'application/json',
                'x-goog-api-key': google_key
            },
            json=data,
            timeout=30
        )
        
        print(f"📊 Status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            predictions = result.get('predictions', [])
            
            if predictions and len(predictions) > 0:
                base64_image = predictions[0].get('bytesBase64Encoded')
                if base64_image:
                    image_bytes = base64.b64decode(base64_image)
                    img = Image.open(io.BytesIO(image_bytes))
                    img.save("test_vertex_output.png")
                    print(f"✅ SUCCESS! Image saved: test_vertex_output.png ({img.size})")
                    print(f"📏 Size: {len(image_bytes)} bytes")
                    return True
        
        print(f"❌ Error: {response.status_code}")
        print(f"Response: {response.text[:500]}")
        return False
        
    except Exception as e:
        print(f"❌ Exception: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    test_vertex_imagen()

