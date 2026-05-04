async def test_register_returns_token_pair(client, random_credentials):
    response = await client.post(
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
    assert body["refresh_token"]


async def test_register_password_mismatch_rejected(client, random_credentials):
    response = await client.post(
        "/auth/register",
        json={
            "email": random_credentials["email"],
            "password": random_credentials["password"],
            "password_confirmation": "different",
        },
    )
    assert response.status_code == 422


async def test_register_duplicate_email_returns_409(client, random_credentials):
    payload = {
        "email": random_credentials["email"],
        "password": random_credentials["password"],
        "password_confirmation": random_credentials["password"],
    }
    assert (await client.post("/auth/register", json=payload)).status_code == 201
    assert (await client.post("/auth/register", json=payload)).status_code == 409


async def test_login_success(client, random_credentials):
    await client.post(
        "/auth/register",
        json={
            "email": random_credentials["email"],
            "password": random_credentials["password"],
            "password_confirmation": random_credentials["password"],
        },
    )
    response = await client.post(
        "/auth/login",
        json={
            "email": random_credentials["email"],
            "password": random_credentials["password"],
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["access_token"]
    assert body["refresh_token"]


async def test_login_wrong_password_returns_401(client, random_credentials):
    await client.post(
        "/auth/register",
        json={
            "email": random_credentials["email"],
            "password": random_credentials["password"],
            "password_confirmation": random_credentials["password"],
        },
    )
    response = await client.post(
        "/auth/login",
        json={"email": random_credentials["email"], "password": "wrongpass"},
    )
    assert response.status_code == 401


async def test_refresh_rotates_token(client, random_credentials):
    register = await client.post(
        "/auth/register",
        json={
            "email": random_credentials["email"],
            "password": random_credentials["password"],
            "password_confirmation": random_credentials["password"],
        },
    )
    initial_refresh = register.json()["refresh_token"]

    response = await client.post(
        "/auth/refresh", json={"refresh_token": initial_refresh}
    )
    assert response.status_code == 200
    new_pair = response.json()
    assert new_pair["refresh_token"] != initial_refresh
    assert new_pair["access_token"]

    # Old token must no longer work — rotation revokes it.
    reuse = await client.post(
        "/auth/refresh", json={"refresh_token": initial_refresh}
    )
    assert reuse.status_code == 401


async def test_refresh_with_invalid_token_returns_401(client):
    response = await client.post(
        "/auth/refresh", json={"refresh_token": "garbage"}
    )
    assert response.status_code == 401


async def test_logout_revokes_refresh_token(client, random_credentials):
    register = await client.post(
        "/auth/register",
        json={
            "email": random_credentials["email"],
            "password": random_credentials["password"],
            "password_confirmation": random_credentials["password"],
        },
    )
    refresh = register.json()["refresh_token"]

    logout = await client.post("/auth/logout", json={"refresh_token": refresh})
    assert logout.status_code == 204

    after = await client.post("/auth/refresh", json={"refresh_token": refresh})
    assert after.status_code == 401
