#!/usr/bin/env python3
"""
Test script to debug JWT token flow end-to-end.
"""

import requests
import json
import sys

def test_token_flow():
    """Test the complete token creation and validation flow."""
    
    base_url = "http://localhost:5050"  # Based on your Docker setup
    token_url = f"{base_url}/endorser/token"
    protected_url = f"{base_url}/endorser/v1/admin/config"
    
    print("=== JWT Token Flow Test ===")
    print(f"Token URL: {token_url}")
    print(f"Protected URL: {protected_url}")
    
    # Step 1: Get a token
    print("\n=== Step 1: Getting Token ===")
    token_data = {
        "username": "endorser-api-admin",  # Default from docker-compose
        "password": "endorser-api-admin-key"  # Default from docker-compose
    }
    
    try:
        response = requests.post(token_url, data=token_data)
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.text}")
        
        if response.status_code != 200:
            print("❌ Failed to get token")
            return
            
        token_response = response.json()
        token = token_response["access_token"]
        print(f"✅ Got token: {token[:50]}...")
        
    except Exception as e:
        print(f"❌ Error getting token: {e}")
        return
    
    # Step 2: Use token to access protected endpoint
    print("\n=== Step 2: Using Token ===")
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    try:
        response = requests.get(protected_url, headers=headers)
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.text}")
        
        if response.status_code == 200:
            print("✅ Token validation successful!")
        else:
            print("❌ Token validation failed")
            
    except Exception as e:
        print(f"❌ Error using token: {e}")
    
    # Step 3: Test with invalid token
    print("\n=== Step 3: Testing Invalid Token ===")
    invalid_headers = {
        "Authorization": "Bearer invalid_token_here",
        "Content-Type": "application/json"
    }
    
    try:
        response = requests.get(protected_url, headers=invalid_headers)
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.text}")
        
    except Exception as e:
        print(f"❌ Error testing invalid token: {e}")

if __name__ == "__main__":
    test_token_flow()
