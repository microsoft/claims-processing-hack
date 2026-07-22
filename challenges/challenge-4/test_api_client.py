#!/usr/bin/env python3
"""
Test client for Claims Processing API
"""
import os
import sys
import json
import httpx
import asyncio
from pathlib import Path


async def test_api_upload(api_url: str, image_path: str):
    """Test the API using file upload"""
    print(f"🧪 Testing API with file upload: {image_path}")
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        # Read image file
        with open(image_path, "rb") as f:
            files = {"file": (Path(image_path).name, f, "image/jpeg")}
            
            # Make request
            response = await client.post(
                f"{api_url}/process-claim/upload",
                files=files
            )
        
        print(f"Status: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        
        return response.json()


async def test_health(api_url: str):
    """Test health endpoint"""
    print(f"🏥 Testing health endpoint")
    
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.get(f"{api_url}/health")
        print(f"Status: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")


async def main():
    """Main test function"""
    # Get API URL from environment or argument
    if len(sys.argv) > 1:
        api_url = sys.argv[1]
    else:
        api_url = os.environ.get("API_URL", "http://localhost:8080")
    
    # Remove trailing slash
    api_url = api_url.rstrip("/")
    
    print(f"🎯 Testing Claims Processing API: {api_url}")
    print("=" * 60)
    
    # Test health endpoint
    await test_health(api_url)
    
    print("\n" + "=" * 60)
    
    # Get test image path
    test_image = "/workspaces/claims-processing-hack/challenge-1/data/statements/crash1_front.jpeg"
    
    if not os.path.exists(test_image):
        print(f"❌ Test image not found: {test_image}")
        print("Please specify an image path as the second argument.")
        sys.exit(1)
    
    # Test file upload method
    print("\n📤 Test: File Upload Method")
    print("=" * 60)
    await test_api_upload(api_url, test_image)
    
    print("\n" + "=" * 60)
    print("✅ All tests completed!")


if __name__ == "__main__":
    asyncio.run(main())
