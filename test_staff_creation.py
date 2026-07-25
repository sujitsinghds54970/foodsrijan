import requests
import json
from requests.auth import HTTPBasicAuth

# Backend URL
BASE_URL = "http://localhost:8000/api"

# Get a valid token first - login with a known user
# Let's try to create a new test user first

print("Testing Staff Creation Endpoint...")
print("=" * 60)

# First, let's check what users exist and their roles
login_response = requests.post(
    f"{BASE_URL}/auth/login",
    json={
        "username": "sujitep",
        "password": "password123"
    }
)

print(f"Login response status: {login_response.status_code}")
if login_response.status_code != 200:
    print(f"Login failed: {login_response.json()}")
    print("\nTrying alternative credentials...")
    
    # Try with director account
    login_response = requests.post(
        f"{BASE_URL}/auth/login",
        json={
            "username": "director_vvma005_c158",
            "password": "password123"
        }
    )
    print(f"Alternative login status: {login_response.status_code}")
    if login_response.status_code != 200:
        print(f"Alternative login also failed: {login_response.json()}")
    else:
        print("Alternative login successful!")
else:
    print("Primary login successful!")

# Print response
print(f"\nResponse: {login_response.json()}")
