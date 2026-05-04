def test_register_returns_token(client, random_credentials):
    response = client.post(
        "/auth/register",
        json={
            "email": random_credentials["email"],
            "password": random_credentials["password"],
            "password_confirmation": random_credentials["password"],
        },
    )
    assert response.status_code == 201
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["email"] == random_credentials["email"]
    assert body["access_token"]


def test_register_password_mismatch_rejected(client, random_credentials):
    response = client.post(
        "/auth/register",
        json={
            "email": random_credentials["email"],
            "password": random_credentials["password"],
            "password_confirmation": "different",
        },
    )
    assert response.status_code == 422


def test_register_duplicate_email_returns_409(client, random_credentials):
    payload = {
        "email": random_credentials["email"],
        "password": random_credentials["password"],
        "password_confirmation": random_credentials["password"],
    }
    assert client.post("/auth/register", json=payload).status_code == 201
    assert client.post("/auth/register", json=payload).status_code == 409


def test_login_success(client, random_credentials):
    client.post(
        "/auth/register",
        json={
            "email": random_credentials["email"],
            "password": random_credentials["password"],
            "password_confirmation": random_credentials["password"],
        },
    )
    response = client.post(
        "/auth/login",
        json={
            "email": random_credentials["email"],
            "password": random_credentials["password"],
        },
    )
    assert response.status_code == 200
    assert response.json()["access_token"]


def test_login_wrong_password_returns_401(client, random_credentials):
    client.post(
        "/auth/register",
        json={
            "email": random_credentials["email"],
            "password": random_credentials["password"],
            "password_confirmation": random_credentials["password"],
        },
    )
    response = client.post(
        "/auth/login",
        json={"email": random_credentials["email"], "password": "wrongpass"},
    )
    assert response.status_code == 401


def test_logout_requires_auth(client):
    assert client.post("/auth/logout").status_code == 401


def test_logout_with_valid_token_returns_204(client, random_credentials):
    register = client.post(
        "/auth/register",
        json={
            "email": random_credentials["email"],
            "password": random_credentials["password"],
            "password_confirmation": random_credentials["password"],
        },
    )
    token = register.json()["access_token"]
    response = client.post(
        "/auth/logout", headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 204
