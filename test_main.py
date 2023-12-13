from fastapi.testclient import TestClient
import secrets
import string

from .main import app

client = TestClient(app)


def test_index():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "Hi"}


def test_update_coins():
    response = client.get("/coins-update")
    assert response.status_code == 200
    assert response.json() == {"success": True,"message":"update coins successfull"}
    


def test_get_coins():
    response = client.get("/coins")
    assert response.status_code == 200
    assert isinstance(response.json()["data"], list)

# created random test payload
username = 'test_' + ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(8))
password = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(12))
jwt_token = ""

def test_register():    
    response = client.post(
        "/register",
      json={"username": username, "password": password}
    )
    assert response.status_code == 200
    assert "token" in response.json()
    # Update jwt_token for later use
    global jwt_token
    jwt_token = response.json()["token"]

def test_login():
    response = client.post(
        "/login",
        json={"username": username, "password": password}
    )
    assert response.status_code == 200
    assert "token" in response.json()
    # Update jwt_token for later use
    global jwt_token
    jwt_token = response.json()["token"]

# protected route test
def test_add_tracked_coin():
    response = client.post("/add-coin-track", json={"coin_id": 1}, headers={"Authorization": f"Bearer {jwt_token}"})
    assert response.status_code == 200
    assert "message" in response.json()

def test_get_tracked_coin():
    response = client.get("/coin-track", headers={"Authorization": f"Bearer {jwt_token}"})
    assert response.status_code == 200
    assert "data" in response.json()

def test_remove_tracked_coin():
    # Assuming jwt_token is a valid JWT token
    response = client.post("/remove-coin-track", json={"coin_id": 1}, headers={"Authorization": f"Bearer {jwt_token}"})

    assert response.status_code == 200
    assert "coin_id" in response.json()
    assert "message" in response.json()

    # Check if the message indicates successful removal
    assert response.json()["message"] == "Coin removed from tracker successfully"

def test_logout():
    response = client.post("/logout", headers={"Authorization": f"Bearer {jwt_token}"})
    assert response.status_code == 200
    assert response.json() == {"username": username, "message": "logout successfull", "token": ""}
    