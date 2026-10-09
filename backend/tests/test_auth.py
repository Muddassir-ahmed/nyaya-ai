from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_login_requires_credentials():
    response = client.post(
        "/auth/login",
        json={
            "email": "does-not-exist@example.com",
            "password": "wrong-password",
        },
    )

    assert response.status_code == 401


def test_protected_route_requires_token():
    response = client.get("/users/me")

    assert response.status_code in (401, 403)