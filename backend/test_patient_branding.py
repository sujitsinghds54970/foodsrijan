import requests
import json

# Test the patient portal branding endpoint
# First, get a patient token by creating a test session

# For now, let's just check if the endpoint exists
response = requests.post(
    "http://localhost:8000/api/patient/login",
    json={
        "mode": "otp",
        "mobile": "9876543210",
        "otp": "123456"
    }
)

print("Login response status:", response.status_code)
if response.status_code == 200:
    token = response.json().get("access_token")
    print("Got token:", token[:20] + "...")
    
    # Now test the dashboard endpoint
    dash_response = requests.get(
        "http://localhost:8000/api/patient/dashboard",
        headers={"Authorization": f"Bearer {token}"}
    )
    
    print("Dashboard status:", dash_response.status_code)
    if dash_response.status_code == 200:
        data = dash_response.json()
        branding = data.get("branding", {})
        print("\n=== BRANDING DATA ===")
        print(json.dumps(branding, indent=2))
        print(f"\nBranch Name: {branding.get('branch_name')}")
        print(f"Branch Address: {branding.get('branch_address')}")
        print(f"Branch Logo URL: {branding.get('logo_url')}")
    else:
        print("Error:", dash_response.text[:200])
else:
    print("Error:", response.text[:200])
