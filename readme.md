# Tracker Coin FastAPI Documentation

# Table of Contents

- [Introduction](#introduction)
- [Installation](#installation)
- [JWT Token Configuration](#jwt-token-configuration)
- [Testing Application](#testing)
- [How Authentication Works](#how-auth-work)
- [Database Initialization](#database-initialization)
- [General Routes](#general-routes)
  - [Update Coins](#update-coins)
  - [Get Coins](#get-coins)
- [User Routes](#user-routes)
  - [Login](#login)
  - [Register](#register)
  - [Logout](#logout)
- [Protected Routes](#protected-routes)
  - [Add Tracked Coin](#add-tracked-coin)
  - [Get Tracked Coins](#get-tracked-coins)
- [Try it Live](#try-it-live)

## Introduction

This FastAPI application, crafted in Python 3.11.5, offers a straightforward API for efficiently managing and tracking cryptocurrency coins. Its features include easy data updates, user authentication, and personalized coin tracking.

## Installation

1. Clone the repository:

   ```bash
   git clone <repository_url>

2.  Install required system dependencies and packages:
    
    ```bash
    sudo apt update
    sudo apt install -y python3.11 python3.11-venv

3. Create a virtual environment:

    ```bash
    python -m venv venv

4. Activate the virtual environment:

    - Windows:

        ```bash
        .\venv\Scripts\activate
    
    - Linux/macOS:
        ```bash
        source venv/bin/activate
        
5. Install the required packages:

    ```bash
    pip install -r requirements.txt

6. Create a .env file and set your environment variables:

    ```env
    JWT_SECRET_KEY=your_secret_key
    
7. Run the FastAPI application:

    ```bash
    uvicorn main:app --reload


## JWT Token Configuration
- **SECRET_KEY**: The secret key used for JWT token encoding and decoding.
- **ALGORITHM**: The algorithm used for JWT token encoding.
- **ACCESS_TOKEN_EXPIRE_MINUTES**: The expiration time for access tokens in minutes.

## **Testing Application**

Run ```pytest```

test case provided in the root folder `test_main.py`

Prioritize running this test before engaging in any transactions, as it specifically involves updating data in the database. It should be executed first before proceeding with any other operations. 


## How Authentication Works 

1. **Login Endpoint (/login):**

   To authenticate, users need to provide their credentials (username and password) through the `/login` endpoint.

   ```bash
   POST /login
   

    Request Body
    
    {
      "username": "your_username",
      "password": "your_password"
    }
    Response
    {
      "message": "login successfull",
      "username": "your_username",
      "token": "your_generated_jwt_token"
    }
    
2. **Protected Routes**

    Once authenticated, users include the JWT token in the Authorization header using the Bearer schema for every request to protected routes.

    ```bash 
    Authorization: Bearer your_generated_jwt_token

3. **Logout Endpoint (/logout):**


    Logging out is handled on the client side. The **/logout** endpoint does not require any authentication since the application is stateless in the backend. Users can clear the JWT token from their client, effectively logging them out.

    ```
    POST /logout
    Response:
    {
      "username": "your_username",
      "message": "logout successfull",
      "token": ""
    }

## Database Initialization
The application initializes a SQLite database named `tracker_coin.db` with three tables: `users`, `coins`, and `user_coins`. These tables store user information, coin data, and the relationships between users and tracked coins.

## General Routes

### **Update Coins**
- **Route**: /coins-update
- **Method**: GET
- **Description**: Updates the `coins` table with the latest data from the CoinCap API.

### **Get Coins**
- **Route**: /coins
- **Method**: GET
- **Description**: Retrieves all coins from the `coins` table.

## **User Routes**

### **Login**
- **Route**: /login
- **Method**: POST
- **Description**: Logs in a user and returns an access token.

### **Register**
- **Route**: /register
- **Method**: POST
- **Description**: Registers a new user and returns an access token.

### **Logout**
- **Route**: /logout
- **Method**: POST
- **Description**: Logs out a user.

## Protected Routes (Authenticated User Only)
### **Add Tracked Coin**
- **Route**: /coin-track
- **Method**: POST
- **Description**: Adds a tracked coin to a user's list.

### Get Tracked Coins
- **Route**: /coin-track
- **Method**: GET
- **Description**: Retrieves all tracked coins for a user.

## **Try It Live**

you can try out it's live : http://167.172.65.57:8000
    
example: 
    
    http get http://167.172.65.57:8000/coins
