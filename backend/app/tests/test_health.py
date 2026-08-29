def test_health_check(client):
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "online"
    assert data["airgap_mode"] is True
    assert "service" in data


def test_auth_login_valid(client):
    response = client.post(
        "/api/v1/auth/login",
        data={
            "username": "examiner@nciipc.gov.in",
            "password": "SupervisorPass123!"
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["role"] == "examiner"


def test_auth_login_invalid(client):
    response = client.post(
        "/api/v1/auth/login",
        data={
            "username": "examiner@nciipc.gov.in",
            "password": "WrongPassword!"
        }
    )
    assert response.status_code == 401
