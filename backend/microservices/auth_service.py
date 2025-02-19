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

# @app.route('/api/auth/login', methods=['POST'])
# def login():
#     data = request.get_json()
#     username = data.get('username')
#     password = data.get('password')
    
#     if not username or not password:
#         return jsonify({'error': 'Username and password are required'}), 400
    
#     users = load_users()
#     user = next((u for u in users if u.get('username') == username and u.get('password') == password), None)
    
#     if not user:
#         return jsonify({'error': 'Invalid credentials'}), 401
    
#     token = jwt.encode({
#         'id': user['id'],
#         'username': user['username'],
#         'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=1)
#     }, app.config['SECRET_KEY'], algorithm='HS256')
    
#     user_data = {k: user[k] for k in user if k != 'password'}
#     return jsonify({'token': token, 'user': user_data})

# @app.route('/api/user/profile', methods=['GET'])
# def profile():
#     auth_header = request.headers.get('Authorization')
#     if not auth_header:
#         return jsonify({'error': 'Authorization header missing'}), 401

#     try:
#         token = auth_header.split()[1]
#         payload = jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256'])
#     except Exception as e:
#         return jsonify({'error': 'Invalid token', 'message': str(e)}), 401

#     users = load_users()
#     user = next((u for u in users if u.get('id') == payload.get('id')), None)
#     if not user:
#         return jsonify({'error': 'User not found'}), 404

#     user_data = {k: user[k] for k in user if k != 'password'}
#     return jsonify(user_data)

# @app.route('/health', methods=['GET'])
# def health():
#     return jsonify({'status': 'Authentication service is healthy'}), 200

# if __name__ == '__main__':
#     app.run(host='0.0.0.0', port=5003, debug=True)