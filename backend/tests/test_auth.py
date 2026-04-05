from types import SimpleNamespace

import httpx
import pytest
from jose import jwt

from app.api import deps as deps_module
from app.api.v1 import auth as auth_module
from app.main import app


class _FakeAuthClient:
    def __init__(self) -> None:
        self.payloads: list[dict] = []

    def sign_in_with_otp(self, payload: dict):
        self.payloads.append(payload)
        return {"ok": True}


class _FakeSupabaseClient:
    def __init__(self) -> None:
        self.auth = _FakeAuthClient()


class _FakeResult:
    def __init__(self, data) -> None:
        self.data = data


class _FakeTableQuery:
    def __init__(self, tables: dict[str, dict[str, dict]], table_name: str) -> None:
        self.tables = tables
        self.table_name = table_name
        self._operation = None
        self._payload = None
        self._filters: dict[str, str] = {}

    def select(self, _columns: str):
        self._operation = "select"
        return self

    def eq(self, field: str, value: str):
        self._filters[field] = value
        return self

    def single(self):
        return self

    def maybe_single(self):
        return self

    def upsert(self, payload: dict, on_conflict: str | None = None):
        del on_conflict
        self._operation = "upsert"
        self._payload = dict(payload)
        return self

    def execute(self):
        table = self.tables.setdefault(self.table_name, {})
        if self._operation == "upsert":
            row = dict(self._payload)
            table[row["id"]] = row
            return _FakeResult([row])

        if self._operation == "select":
            row = table.get(self._filters.get("id"))
            return _FakeResult(dict(row) if row else None)

        raise AssertionError(f"Unexpected operation: {self._operation}")


class _FakeAdminClient:
    def __init__(self, initial_tables: dict[str, dict[str, dict]] | None = None) -> None:
        self.tables = initial_tables or {}

    def table(self, table_name: str):
        return _FakeTableQuery(self.tables, table_name)


def _make_bearer_token(secret: str, user_id: str = "user-123") -> str:
    return jwt.encode(
        {"sub": user_id, "aud": "authenticated"},
        secret,
        algorithm="HS256",
    )


@pytest.mark.asyncio
async def test_send_otp_for_signup_forwards_magic_link_redirect(monkeypatch) -> None:
    fake_client = _FakeSupabaseClient()
    monkeypatch.setattr(auth_module, "get_anon_client", lambda: fake_client)

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.post(
            "/v1/auth/send-otp",
            json={
                "email": "test@example.com",
                "email_redirect_to": "http://localhost:5000/pages/auth-callback.html",
            },
        )

    assert response.status_code == 200
    assert response.json() == {
        "success": True,
        "message": "Magic link sent successfully",
    }
    assert fake_client.auth.payloads == [
        {
            "email": "test@example.com",
            "options": {
                "should_create_user": True,
                "email_redirect_to": "http://localhost:5000/pages/auth-callback.html",
            },
        }
    ]


@pytest.mark.asyncio
async def test_send_otp_rejects_redirect_for_phone_destination() -> None:
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.post(
            "/v1/auth/send-otp",
            json={
                "phone": "+254712345678",
                "email_redirect_to": "http://localhost:5000/pages/auth-callback.html",
            },
        )

    assert response.status_code == 422
    assert "email_redirect_to" in response.text


@pytest.mark.asyncio
async def test_create_profile_allows_authenticated_new_user_without_existing_profile(monkeypatch) -> None:
    secret = "test-jwt-secret"
    fake_admin = _FakeAdminClient()
    monkeypatch.setattr(deps_module, "settings", SimpleNamespace(supabase_jwt_secret=secret))
    monkeypatch.setattr(auth_module, "get_admin_client", lambda: fake_admin)

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.post(
            "/v1/auth/profile",
            headers={"Authorization": f"Bearer {_make_bearer_token(secret)}"},
            json={
                "full_name": "Jane Wanjiku",
                "phone": "+254712345678",
                "email": "jane@example.com",
                "county": "Nairobi",
                "area": "Westlands",
                "role": "client",
                "mpesa_number": "+254712345678",
                "preferred_language": "en",
            },
        )

    assert response.status_code == 201
    assert response.json()["success"] is True
    assert fake_admin.tables["profiles"]["user-123"]["full_name"] == "Jane Wanjiku"
    assert fake_admin.tables["profiles"]["user-123"]["role"] == "client"


@pytest.mark.asyncio
async def test_bootstrap_allows_authenticated_new_user_without_existing_profile(monkeypatch) -> None:
    secret = "test-jwt-secret"
    fake_admin = _FakeAdminClient()
    monkeypatch.setattr(deps_module, "settings", SimpleNamespace(supabase_jwt_secret=secret))
    monkeypatch.setattr(auth_module, "get_admin_client", lambda: fake_admin)

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get(
            "/v1/auth/bootstrap",
            headers={"Authorization": f"Bearer {_make_bearer_token(secret)}"},
        )

    assert response.status_code == 200
    assert response.json() == {
        "is_new_user": True,
        "redirect_to": "complete-registration",
        "role": "client",
        "profile": None,
    }
