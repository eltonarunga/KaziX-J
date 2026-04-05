from fastapi.testclient import TestClient

from app.main import app


def test_root_redirects_to_frontend_index() -> None:
    with TestClient(app) as client:
        response = client.get("/", follow_redirects=False)

    assert response.status_code == 307
    assert response.headers["location"] == "/pages/index.html"


def test_frontend_page_is_served_from_fastapi() -> None:
    with TestClient(app) as client:
        response = client.get("/pages/login.html")

    assert response.status_code == 200
    assert "Sign In" in response.text


def test_frontend_assets_are_served_from_fastapi() -> None:
    with TestClient(app) as client:
        response = client.get("/assets/css/styles.css")

    assert response.status_code == 200
    assert ":root" in response.text


def test_frontend_env_js_is_served_from_fastapi() -> None:
    with TestClient(app) as client:
        response = client.get("/env.js")

    assert response.status_code == 200
    assert "window.KAZIX_CONFIG" in response.text
