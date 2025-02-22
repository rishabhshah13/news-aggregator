#!/usr/bin/env python3
"""
auth_service.py - Microservice for Authentication
Handles user authentication, JWT token generation, and user profile management.
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
    """Load users from the users.txt file"""
    try:
        with open(USERS_FILE, 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading users: {e}")
        return []
