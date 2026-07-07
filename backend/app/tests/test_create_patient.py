from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_create_patient_requires_auth():
    payload = {
        "first_name": "John",
        "last_name": "Doe",
        "date_of_birth": "1994-01-01T00:00:00",
        "gender": "Male",
        "phone": "9999999999",
        "address": "Address",
        "city": "City",
        "state": "State",
        "pincode": "123456",
        "emergency_contact": "8888888888",
        "emergency_contact_name": "Jane Doe",
        "branch_id": 1,
    }
    response = client.post("/api/patients/", json=payload)
    assert response.status_code in (401, 403)
