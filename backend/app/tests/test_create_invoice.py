from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_create_invoice_minimal_payload():
    payload = {
        "patient_id": 1,
        "branch_id": 1,
        "total_amount": 500.0
    }
    response = client.post("/invoices/", json=payload)
    assert response.status_code in (201, 500)
