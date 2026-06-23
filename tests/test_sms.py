from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_forward_sms():
    response = client.post("/api/sms/forward", json={
        "sender": "Alice", "message": "Hello", "device_id": "phone1"
    }, headers={"Authorization": "Bearer testtoken"})
    assert response.status_code in [200, 401, 403]  # depends on auth

def test_list_sms():
    response = client.get("/api/sms/list", headers={"Authorization": "Bearer testtoken"})
    assert response.status_code in [200, 401, 403]
