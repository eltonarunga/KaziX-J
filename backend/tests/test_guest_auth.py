import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_guest_sign_in():
    response = client.post("/v1/auth/guest")
    assert response.status_code == 200
    data = response.json()
    assert data["access_token"] == "kazix-guest-session-token"
    assert data["redirect_to"] == "client-dashboard"

def test_guest_session():
    # Use the guest token to get session
    response = client.get(
        "/v1/auth/session",
        headers={"Authorization": "Bearer kazix-guest-session-token"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["user_id"] == "00000000-0000-0000-0000-000000000000"
    assert data["full_name"] == "Guest User"
    assert data["role"] == "admin"

def test_guest_bootstrap():
    response = client.get(
        "/v1/auth/bootstrap",
        headers={"Authorization": "Bearer kazix-guest-session-token"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["role"] == "admin"
    assert data["profile"]["full_name"] == "Guest User"

def test_guest_profile_me():
    response = client.get(
        "/v1/profiles/me",
        headers={"Authorization": "Bearer kazix-guest-session-token"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["profile"]["full_name"] == "Guest User"
    assert data["profile"]["role"] == "admin"
