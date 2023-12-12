import os
from typing import Union
from dotenv import load_dotenv
import json
import sqlite3
import requests

from datetime import datetime, timedelta

from fastapi import Depends, FastAPI, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.responses import JSONResponse
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel


load_dotenv()
COIN_PATH = "coins.json"


# openssl rand -hex 32
SECRET_KEY = os.getenv("JWT_SECRET_KEY") or "seweey"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


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


app = FastAPI()

# helpers function


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


def db_reset():
    # Load the data from the file and initialize the database
    con = sqlite3.connect('tracker_coin.db')
    cur = con.cursor()

    # Drop existing tables
    cur.execute('DROP TABLE IF EXISTS users;')
    cur.execute('DROP TABLE IF EXISTS coins;')
    cur.execute('DROP TABLE IF EXISTS user_coins;')

    con.commit()
    con.close()


class UserAccess(BaseModel):
    username: str
    password: str

    # Crypto Price Tracker
    # a. Signup (email, password, password confirmation)
    # b. Signin (email and password). API user will get a JWT Token to identify user.
    # c. Authenticated user can signout.
    # d. Authenticated user can show user list of tracked coins (name of coin and price in rupiah)
    # e. Authenticated user can add coin to tracker.
    # f. Authenticated user can remove coin from tracker.


# db_reset()
db_init()


class Token(BaseModel):
    access_token: str
    token_type: str


@app.get("/coins-update")
def initCoins():
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

            # Prepare the data for insertion
            data_to_insert = [(obj["name"], obj["shortName"], obj["rank"], round(
                float(obj["priceUsd"]), 2), obj["priceIdr"]) for obj in coin_data]
            # Insert the entire array into the database
            cur.executemany('''
                INSERT INTO coins (name,shortName,rank,priceUsd,priceIdr) VALUES (?, ?,?,?,?)
            ''', data_to_insert)
            con.commit()
            con.close()
            return {"success": True, "data": coin_data}
    except Exception as e:
        con.close()
        data = {"status": "failed", "message": str(e)}
        return JSONResponse(content=data, status_code=500)


@app.get("/coins")
def getCoins():
    con = sqlite3.connect("tracker_coin.db")
    cur = con.cursor()

    # Get the column names from the table
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
        # Verify the JWT token
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
        request.state.username = username
    except Exception as e:
        raise credentials_exception


@app.post("/login")
def login(user: UserAccess):
    try:
        username = user.username
        password = user.password

        con = sqlite3.connect("tracker_coin.db")
        cur = con.cursor()
        cur.execute('''
            SELECT password FROM users
            WHERE username = ?
            ;
        ''', (username,))

        # Fetch the result
        result = cur.fetchone()
        if not result:
            return {"status_code": 400, "message": "username/password invalid"}
        if not verify_password(password, result[0]):
            return {"status_code": 400, "message": "username/password invalid"}

        con.commit()
        con.close()
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": username}, expires_delta=access_token_expires
        )
        return {"message": "login successfull", "username": username, "token": access_token}

    except Exception as e:
        con.close()
        return {"status_code": 500, "message": str(e)}


@app.post("/register")
def register(user: UserAccess):
    try:
        username = user.username
        password = user.password

        con = sqlite3.connect("tracker_coin.db")
        cur = con.cursor()
        insert_query = "INSERT INTO users (username, password) VALUES (?, ?)"
        values = (username, hash_password(password))
        cur.execute(insert_query, values)
        con.commit()
        con.close()

        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": username}, expires_delta=access_token_expires
        )
        return {"message": "Created User Successfully", "username": username, "token": access_token}

    except Exception as e:
        con.close()
        return {"status_code": 500, "message": str(e)}


# protected routes routes
@app.post("/logout", dependencies=[Depends(auth_middleware)])
def logout(req: Request):
    # because we stateless in behind, logout mechanism applied in frontend
    return {"username": req.state.username, "message": "logout successfull", "token": ""}


@app.post("/coin-track", dependencies=[Depends(auth_middleware)])
def addCoin(req: Request):
    con = sqlite3.connect("tracker_coin.db")
    cur = con.cursor()

    coin_id = req.id
    short_name = req.short_name
    username = req.state.username

    con.commit()
    con.close()

    cur.execute('''
        SELECT password FROM users
        WHERE username = ?
        ;
    ''', (username,))
    # Fetch the result
    result = cur.fetchone()
    if not result:
        return "error"
    user_id = result[0]

    return {"username": req.state.username, "message": "coin added", "token": ""}


@app.get("/")
def read_root():
    return {"Hello": "World"}
