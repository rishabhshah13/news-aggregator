#!/usr/bin/env python3
"""
Authentication Service Module

This microservice handles all authentication-related functionality including:
- User authentication and authorization
- JWT token generation and validation
- User profile management and storage
- Session handling

The service uses a file-based storage system for user data (users.txt)
and JWT tokens for maintaining user sessions. It provides RESTful endpoints
for user registration, login, and profile management.

Environment Variables:
    JWT_SECRET_KEY: Secret key for JWT token generation (required)

Typical usage example:
    POST /auth/login {'username': 'user', 'password': 'pass'}
    GET /auth/profile with JWT token in Authorization header
"""

from flask import Flask, request, jsonify
import json
import datetime
import jwt
import os
from pathlib import Path

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('JWT_SECRET_KEY', 'your-secret-key')  # Change this in production

# Get the path to the users file
USERS_FILE = Path(__file__).parent.parent / 'data' / 'users.txt'

# Ensure the data directory exists
USERS_FILE.parent.mkdir(parents=True, exist_ok=True)

# Create users.txt if it doesn't exist
if not USERS_FILE.exists():
    with open(USERS_FILE, 'w') as f:
        json.dump([
            {
                "id": 1,
                "username": "testuser",
                "password": "password123",
                "email": "test@example.com",
                "firstName": "Test",
                "lastName": "User"
            }
        ], f)

def load_users():
    """Load user data from the users.txt file.
    
    This function reads the JSON-formatted user data from the users.txt file
    and returns it as a Python list of dictionaries. Each dictionary contains
    user information including id, username, password, email, and name.
    
    Returns:
        list: A list of dictionaries containing user data.
              Each dictionary has the following structure:
              {
                  'id': int,
                  'username': str,
                  'password': str,
                  'email': str,
                  'firstName': str,
                  'lastName': str
              }
    
    Raises:
        Exception: If there's an error reading or parsing the users file.
    """
    try:
        with open(USERS_FILE, 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading users: {e}")
        return []
