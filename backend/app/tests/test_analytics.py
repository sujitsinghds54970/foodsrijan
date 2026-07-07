from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_admin_summary_requires_auth():
    response = client.get("/admin/summary")
    assert response.status_code in (401, 403)

def test_branch_summary_requires_auth():
    response = client.get("/admin/branch-summary")
    assert response.status_code in (401, 403)
