import pytest_asyncio


@pytest_asyncio.fixture()
async def auth_headers(client, random_credentials):
    response = await client.post(
        "/auth/register",
        json={
            "email": random_credentials["email"],
            "password": random_credentials["password"],
            "password_confirmation": random_credentials["password"],
        },
    )
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


async def test_portfolio_requires_auth(client):
    assert (await client.get("/portfolio")).status_code == 401
    assert (await client.post("/portfolio", json={"coin_id": 1})).status_code == 401
    assert (await client.delete("/portfolio/1")).status_code == 401


async def test_add_unknown_coin_returns_404(client, auth_headers):
    response = await client.post(
        "/portfolio", json={"coin_id": 9999}, headers=auth_headers
    )
    assert response.status_code == 404


async def test_add_then_list_portfolio(client, auth_headers, seed_coin):
    coin_id = await seed_coin()
    add = await client.post(
        "/portfolio", json={"coin_id": coin_id}, headers=auth_headers
    )
    assert add.status_code == 201
    body = add.json()
    assert body["coin"]["id"] == coin_id
    assert body["coin"]["external_id"] == "bitcoin"
    assert body["added_at"]

    listing = await client.get("/portfolio", headers=auth_headers)
    assert listing.status_code == 200
    assert len(listing.json()) == 1
    assert listing.json()[0]["coin"]["id"] == coin_id


async def test_add_duplicate_returns_409(client, auth_headers, seed_coin):
    coin_id = await seed_coin()
    await client.post("/portfolio", json={"coin_id": coin_id}, headers=auth_headers)
    response = await client.post(
        "/portfolio", json={"coin_id": coin_id}, headers=auth_headers
    )
    assert response.status_code == 409


async def test_remove_from_portfolio(client, auth_headers, seed_coin):
    coin_id = await seed_coin()
    await client.post("/portfolio", json={"coin_id": coin_id}, headers=auth_headers)

    response = await client.delete(f"/portfolio/{coin_id}", headers=auth_headers)
    assert response.status_code == 204

    listing = await client.get("/portfolio", headers=auth_headers)
    assert listing.json() == []


async def test_remove_nonexistent_returns_404(client, auth_headers):
    response = await client.delete("/portfolio/12345", headers=auth_headers)
    assert response.status_code == 404


async def test_invalid_coin_id_validation(client, auth_headers):
    response = await client.post(
        "/portfolio", json={"coin_id": 0}, headers=auth_headers
    )
    assert response.status_code == 422
