async def test_health(client):
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


async def test_list_coins_empty(client):
    response = await client.get("/coins")
    assert response.status_code == 200
    assert response.json() == []


async def test_list_coins_returns_seeded(client, seed_coin):
    await seed_coin()
    response = await client.get("/coins")
    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["external_id"] == "bitcoin"
    assert body[0]["symbol"] == "BTC"
    assert body[0]["price_usd"] == 50000.0
