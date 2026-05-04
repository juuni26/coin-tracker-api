import pytest


@pytest.fixture()
def auth_headers(client, random_credentials):
    response = client.post(
        "/auth/register",
        json={
            "email": random_credentials["email"],
            "password": random_credentials["password"],
            "password_confirmation": random_credentials["password"],
        },
    )
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_portfolio_requires_auth(client):
    assert client.get("/portfolio").status_code == 401
    assert client.post("/portfolio", json={"coin_id": 1}).status_code == 401
    assert client.delete("/portfolio/1").status_code == 401


def test_add_unknown_coin_returns_404(client, auth_headers):
    response = client.post("/portfolio", json={"coin_id": 9999}, headers=auth_headers)
    assert response.status_code == 404


def test_add_then_list_portfolio(client, auth_headers, seed_coin):
    coin_id = seed_coin()
    add = client.post("/portfolio", json={"coin_id": coin_id}, headers=auth_headers)
    assert add.status_code == 201
    body = add.json()
    assert body["coin"]["id"] == coin_id
    assert body["coin"]["external_id"] == "bitcoin"
    assert body["added_at"]

    listing = client.get("/portfolio", headers=auth_headers)
    assert listing.status_code == 200
    assert len(listing.json()) == 1
    assert listing.json()[0]["coin"]["id"] == coin_id


def test_add_duplicate_returns_409(client, auth_headers, seed_coin):
    coin_id = seed_coin()
    client.post("/portfolio", json={"coin_id": coin_id}, headers=auth_headers)
    response = client.post("/portfolio", json={"coin_id": coin_id}, headers=auth_headers)
    assert response.status_code == 409


def test_remove_from_portfolio(client, auth_headers, seed_coin):
    coin_id = seed_coin()
    client.post("/portfolio", json={"coin_id": coin_id}, headers=auth_headers)

    response = client.delete(f"/portfolio/{coin_id}", headers=auth_headers)
    assert response.status_code == 204

    listing = client.get("/portfolio", headers=auth_headers)
    assert listing.json() == []


def test_remove_nonexistent_returns_404(client, auth_headers):
    response = client.delete("/portfolio/12345", headers=auth_headers)
    assert response.status_code == 404


def test_invalid_coin_id_validation(client, auth_headers):
    response = client.post("/portfolio", json={"coin_id": 0}, headers=auth_headers)
    assert response.status_code == 422
