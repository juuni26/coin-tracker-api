import os
from datetime import datetime, timedelta
from typing import Union
from dotenv import load_dotenv
import json
import sqlite3
import requests
from fastapi import Depends, FastAPI, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.responses import JSONResponse
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel

load_dotenv()
COIN_PATH = "coins.json"
# jwt
SECRET_KEY = os.getenv("JWT_SECRET_KEY") or "seweey"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")
app = FastAPI()

# helpers function


def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)


def hash_password(password):
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: timedelta | None = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def to_idr(usd):
    exchange_rate = 15608.90
    idr = exchange_rate * usd
    rounded_idr = round(idr, 2)
    return rounded_idr

# helpers db


def db_init():
    con = sqlite3.connect("tracker_coin.db")
    cur = con.cursor()
    # Create users table
    cur.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
    ''')
    # Create coins table
    cur.execute('''
        CREATE TABLE IF NOT EXISTS coins (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            shortName TEXT UNIQUE NOT NULL,
            rank TEXT,
            priceUsd REAL,
            priceIdr REAL    
        )
    ''')
    # Create user_trackers table
    cur.execute('''
        CREATE TABLE IF NOT EXISTS user_coins (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            coin_id INTEGER,
            FOREIGN KEY (user_id) REFERENCES users (id),
            FOREIGN KEY (coin_id) REFERENCES coins (id),
            UNIQUE (user_id, coin_id)
        )
    ''')
    con.commit()
    con.close()


def db_truncate_tables():
    con = sqlite3.connect('tracker_coin.db')
    cur = con.cursor()

    cur.execute('DROP TABLE IF EXISTS users;')
    cur.execute('DROP TABLE IF EXISTS coins;')
    cur.execute('DROP TABLE IF EXISTS user_coins;')

    cur.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
    ''')
    # Create coins table
    cur.execute('''
        CREATE TABLE IF NOT EXISTS coins (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            shortName TEXT UNIQUE NOT NULL,
            rank TEXT,
            priceUsd REAL,
            priceIdr REAL    
        )
    ''')
    # Create user_trackers table
    cur.execute('''
        CREATE TABLE IF NOT EXISTS user_coins (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            coin_id INTEGER,
            FOREIGN KEY (user_id) REFERENCES users (id),
            FOREIGN KEY (coin_id) REFERENCES coins (id),
            UNIQUE (user_id, coin_id)
        )
    ''')
    con.commit()
    con.close()


db_init()

# general route


@app.get("/")
def index():
    return {"message": "Hi"}

@app.get("/reset-data")
def resetData():
    db_truncate_tables()
    return {"message": "data successfully resetted"}


@app.get("/coins-update")
def updateCoins():
    db_truncate_tables()
    con = sqlite3.connect("tracker_coin.db")
    cur = con.cursor()
    try:
        api_url = 'https://api.coincap.io/v2/assets'
        response = requests.get(api_url)
        if response.status_code == 200:
            coin_data = response.json()
            coin_data = [
                {
                    "shortName": coin["id"],
                    "rank": coin["rank"],
                    "name": coin["name"],
                    "priceUsd": coin["priceUsd"],
                    "priceIdr": to_idr(float(coin["priceUsd"])),
                }
                for coin in coin_data.get("data", [])
            ]
            data_to_insert = [(obj["name"], obj["shortName"], obj["rank"], round(
                float(obj["priceUsd"]), 2), obj["priceIdr"]) for obj in coin_data]
            cur.executemany('''
                INSERT INTO coins (name,shortName,rank,priceUsd,priceIdr) VALUES (?, ?,?,?,?)
            ''', data_to_insert)
            con.commit()
            con.close()
            return {"success": True, "message": "update coins successfull"}
        data = {"status": "failed", "message": "Fetching Data Failed"}
        return JSONResponse(content=data, status_code=500)
    except Exception as e:
        con.close()
        data = {"status": "failed", "message": str(e)}
        return JSONResponse(content=data, status_code=500)


@app.get("/coins")
def getCoins():
    con = sqlite3.connect("tracker_coin.db")
    cur = con.cursor()
    cur.execute(f"PRAGMA table_info(coins)")
    columns = cur.fetchall()
    column_names = [column[1] for column in columns]
    cur.execute(f"SELECT * FROM coins")
    rows = cur.fetchall()
    coin_data = [dict(zip(column_names, row)) for row in rows]
    con.close()
    return {"data": coin_data}


def auth_middleware(request: Request, token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
        user_id = payload.get("user_id")

        request.state.username = username
        request.state.user_id = user_id

    except Exception as e:
        raise credentials_exception


class UserAccess(BaseModel):
    username: str
    password: str


@app.post("/login")
def login(user: UserAccess):
    try:
        username = user.username
        password = user.password

        con = sqlite3.connect("tracker_coin.db")
        cur = con.cursor()
        cur.execute('''
            SELECT id,password FROM users
            WHERE username = ?
            ;
        ''', (username,))

        # Fetch the result
        result = cur.fetchone()
        if not result:
            return {"status_code": 400, "message": "username/password invalid"}
        if not verify_password(password, result[1]):
            return {"status_code": 400, "message": "username/password invalid"}

        con.commit()
        con.close()
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": username, "user_id": result[0]}, expires_delta=access_token_expires
        )
        return {"message": "login successfull", "username": username, "token": access_token}

    except Exception as e:
        con.close()
        data = {"status": "failed", "message": str(e)}
        return JSONResponse(content=data, status_code=500)


@app.post("/register")
def register(user: UserAccess):
    con = sqlite3.connect("tracker_coin.db")
    cur = con.cursor()
    try:
        username = user.username
        password = user.password
        insert_query = "INSERT INTO users (username, password) VALUES (?, ?)"
        values = (username, hash_password(password))
        cur.execute(insert_query, values)
        user_id = cur.lastrowid
        con.commit()
        con.close()
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": username, "user_id": user_id}, expires_delta=access_token_expires
        )
        return {"message": "Created User Successfully", "username": username, "token": access_token}
    except Exception as e:
        con.close()
        data = {"status": "failed", "message": str(e)}
        return JSONResponse(content=data, status_code=500)


# protected routes
@app.post("/logout", dependencies=[Depends(auth_middleware)])
def logout(req: Request):
    # because we stateless in behind, logout mechanism applied in frontend
    return {"username": req.state.username, "message": "logout successfull", "token": ""}


class CoinTrack(BaseModel):
    coin_id: int


@app.post("/add-coin-track", dependencies=[Depends(auth_middleware)])
def addTrackedCoin(req: Request, coin: CoinTrack):
    con = sqlite3.connect("tracker_coin.db")
    cur = con.cursor()
    try:
        state_error = False
        # payload jwt
        user_id = req.state.user_id
        #  payload input
        coin_id = coin.coin_id
        if coin_id:
            cur.execute('''
            SELECT id FROM coins
            WHERE id = ?
            ;
            ''', (coin_id,))
            result = cur.fetchone()
            if not result:
                state_error = True
        else:
            state_error = True

        if state_error:
            con.close()
            data = {"status": "failed",
                    "message": "coin not found, please input coin_id correctly"}
            return JSONResponse(content=data, status_code=400)

        insert_query = "INSERT INTO user_coins (user_id, coin_id) VALUES (?, ?)"
        values = (user_id, coin_id)
        cur.execute(insert_query, values)
        con.commit()
        con.close()
        return {"username": req.state.username, "message": "coin added to tracker successfully"}
    except Exception as e:
        con.close()
        data = {"status": "failed", "message": str(e)}
        return JSONResponse(content=data, status_code=500)

@app.post("/remove-coin-track", dependencies=[Depends(auth_middleware)])
def removeTrackedCoin(req: Request, coin: CoinTrack):
    con = sqlite3.connect("tracker_coin.db")
    cur = con.cursor()
    try:
        user_id = req.state.user_id
        coin_id = coin.coin_id

        # Check if the user is tracking the specified coin
        cur.execute('''
            SELECT id FROM user_coins
            WHERE user_id = ? AND coin_id = ?
        ''', (user_id, coin_id))
        result = cur.fetchone()

        if not result:
            con.close()
            data = {"status": "failed", "message": "Coin not found in user's tracker"}
            return JSONResponse(content=data, status_code=400)

        # Remove the tracked coin
        cur.execute('''
            DELETE FROM user_coins
            WHERE user_id = ? AND coin_id = ?
        ''', (user_id, coin_id))

        con.commit()
        con.close()
        return {"coin_id":coin_id,"message": "Coin removed from tracker successfully"}
    except Exception as e:
        con.close()
        data = {"status": "failed", "message": str(e)}
        return JSONResponse(content=data, status_code=500)


@app.get("/coin-track", dependencies=[Depends(auth_middleware)])
def getTrackedCoin(req: Request):
    con = sqlite3.connect("tracker_coin.db")
    cur = con.cursor()
    user_id = req.state.user_id
    try:
        query = """
        SELECT coins.name, coins.shortName,coins.priceUsd ,coins.priceIdr,coins.rank,coins.id as coin_id
        FROM coins
        JOIN user_coins ON user_coins.coin_id = coins.id
        JOIN users ON users.id = user_coins.user_id
        WHERE users.id = ?    
        """
        cur.execute(query, (user_id,))
        rows = cur.fetchall()       
        result = [
            {"coin_id": row[5], "coin_name": row[0], "coin_shortName": row[1],
                "coin_priceUsd": row[2], "coin_priceIdr": row[3], "coin_rank": row[4]}
            for row in rows
        ]
        print(result, "this one is tracked coin from users")
        con.close()
        return {"data": result, "success": True}
    except Exception as e:
        con.close()
        data = {"status": "failed", "message": str(e)}
        return JSONResponse(content=data, status_code=500)
