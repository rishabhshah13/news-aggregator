#!/usr/bin/env python3
"""api_gateway.py - API Gateway for the News Aggregator Backend
This Flask application aggregates endpoints from various microservices.
"""

from flask import Flask, jsonify, request, make_response
from flask_cors import CORS
from flask_restx import Api, Resource, fields
import sys
import os
import jwt
import json
import uuid
import datetime
from functools import wraps
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

# load env
from dotenv import load_dotenv
load_dotenv()



from backend.microservices.summarization_service import run_summarization, process_articles
from backend.microservices.news_fetcher import fetch_news
from backend.core.config import Config
from backend.core.utils import setup_logger, log_exception
from backend.microservices.auth_service import load_users
from backend.microservices.news_storage import store_article_in_supabase, log_user_search
# Initialize logger
logger = setup_logger(__name__)

# Initialize Flask app with CORS support
app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('JWT_SECRET_KEY', 'your-secret-key')  # Change this in production
CORS(app, origins=Config.CORS_ORIGINS, supports_credentials=True, allow_headers=['Content-Type', 'Authorization'])

# Initialize Flask-RestX
api = Api(app, version='1.0', title='News Aggregator API',
          description='A news aggregation and summarization API')

# Define namespaces
news_ns = api.namespace('api/news', description='News operations')
health_ns = api.namespace('health', description='Health check operations')
summarize_ns = api.namespace('summarize', description='Text summarization operations')
user_ns = api.namespace('api/user', description='User operations')
auth_ns = api.namespace('api/auth', description='Authentication operations')
bookmark_ns = api.namespace('api/bookmarks', description='Bookmark operations')

def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get('Authorization')
        if not auth_header:
            return {'error': 'Authorization header missing'}, 401
        try:
            token = auth_header.split()[1]
            payload = jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256'])
            return f(*args, **kwargs)
        except Exception as e:
            return {'error': 'Invalid token', 'message': str(e)}, 401
    return decorated

# Define models for documentation
article_model = api.model('Article', {
    'article_text': fields.String(required=True, description='The text to summarize')
})

user_profile_model = api.model('UserProfile', {
    'id': fields.String(description='User ID'),
    'username': fields.String(description='Username'),
    'email': fields.String(description='Email address'),
    'firstName': fields.String(description='First name'),
    'lastName': fields.String(description='Last name'),
    'avatarUrl': fields.String(description='URL to user avatar')
})

# Model for user signup
signup_model = api.model('Signup', {
    'username': fields.String(required=True, description='Username'),
    'password': fields.String(required=True, description='Password'),
    'email': fields.String(required=True, description='Email address'),
    'firstName': fields.String(required=False, description='First name'),
    'lastName': fields.String(required=False, description='Last name')
})

# Health check endpoint
@health_ns.route('/')
class HealthCheck(Resource):
    def get(self):
        """Check if API Gateway is healthy"""
        return {"status": "API Gateway is healthy"}, 200

# Summarization endpoint
@summarize_ns.route('/')
class Summarize(Resource):
    @summarize_ns.expect(article_model)
    def post(self):
        """Summarize the given article text"""
        data = request.get_json()
        article_text = data.get('article_text', '')
        summary = run_summarization(article_text)
        return {"summary": summary}, 200

@news_ns.route('/fetch')
class NewsFetch(Resource):
    @news_ns.param('keyword', 'Search keyword for news')
    @news_ns.param('user_id', 'User ID for logging search history')
    @news_ns.param('session_id', 'Session ID for tracking requests')
    def get(self):
        """
        Fetch news articles, store them in Supabase, and log user search history if a user ID is provided.
        """
        try:
            keyword = request.args.get('keyword', '')
            user_id = request.args.get('user_id')  # optional
            session_id = request.args.get('session_id')

            # Fetch articles from your existing news_fetcher module.
            articles = fetch_news(keyword)  # This returns a list of articles.
            stored_article_ids = []

            for article in articles:
                # Store each article in the database; get its unique id.
                article_id = store_article_in_supabase(article)
                stored_article_ids.append(article_id)

                # If the request included a user_id, log the search for this article.
                if user_id:
                    log_user_search(user_id, article_id, session_id)

            return make_response(jsonify({
                'status': 'success',
                'data': stored_article_ids
            }), 200)

        except Exception as e:
            return make_response(jsonify({
                'status': 'error',
                'message': str(e)
            }), 500)

            


# News processing endpoint
@news_ns.route('/process')
class NewsProcess(Resource):
    @news_ns.param('session_id', 'Session ID for tracking requests')
    def post(self):
        """Process and summarize articles"""
        try:
            session_id = request.args.get('session_id')
            summarized_articles = process_articles(session_id)
            return {
                'status': 'success',
                'message': 'Articles processed and summarized successfully',
                'data' : summarized_articles,
                'session_id': session_id
            }, 200
        except Exception as e:
            logger.error(f"Error processing articles: {str(e)}")
            return {
                'status': 'error',
                'message': str(e)
            }, 500

# User authentication endpoints
@auth_ns.route('/signup')
class Signup(Resource):
    @auth_ns.expect(signup_model)
    def post(self):
        print('signup')
        """Register a new user"""
        data = request.get_json()
        username = data.get('username')
        password = data.get('password')
        email = data.get('email')
        firstName = data.get('firstName', '')
        lastName = data.get('lastName', '')

        if not username or not password or not email:
            return {'error': 'Username, password, and email are required'}, 400

        users = load_users()

        # Check if username already exists
        if any(u.get('username') == username for u in users):
            return {'error': 'Username already exists'}, 400

        # Create new user with unique ID
        new_user = {
            'id': str(uuid.uuid4()),
            'username': username,
            'password': password,
            'email': email,
            'firstName': firstName,
            'lastName': lastName
        }

        print(new_user)
        
        users.append(new_user)

        try:
            # Save updated users list
            with open(os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'users.txt'), 'w') as f:
                json.dump(users, f, indent=4)
        except Exception as e:
            return {'error': 'Failed to save user data', 'message': str(e)}, 500

        # Generate JWT token
        token = jwt.encode({
            'id': new_user['id'],
            'username': new_user['username'],
            'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=1)
        }, app.config['SECRET_KEY'], algorithm='HS256')

        # Exclude password from response
        user_data = {k: new_user[k] for k in new_user if k != 'password'}
        return {'message': 'User registered successfully', 'user': user_data, 'token': token}, 201

@auth_ns.route('/login')
class Login(Resource):
    def post(self):
        """Login and get authentication token"""
        print('login in')
        data = request.get_json()
        username = data.get('username')
        password = data.get('password')
        
        if not username or not password:
            return {'error': 'Username and password are required'}, 400
        
        users = load_users()
        user = next((u for u in users if u.get('username') == username and u.get('password') == password), None)
        
        if not user:
            return {'error': 'Invalid credentials'}, 401
        
        token = jwt.encode({
            'id': user['id'],
            'username': user['username'],
            'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=1)
        }, app.config['SECRET_KEY'], algorithm='HS256')
        
        user_data = {k: user[k] for k in user if k != 'password'}
        return {'token': token, 'user': user_data}

@user_ns.route('/profile')
class UserProfile(Resource):
    @token_required
    @user_ns.marshal_with(user_profile_model)
    def get(self):
        """Get user profile information"""
        auth_header = request.headers.get('Authorization')
        token = auth_header.split()[1]
        payload = jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256'])
        
        users = load_users()
        user = next((u for u in users if u.get('id') == payload.get('id')), None)
        if not user:
            return {'error': 'User not found'}, 404
            
        return {k: user[k] for k in user if k != 'password'}, 200

@bookmark_ns.route('/')
class Bookmark(Resource):
    @token_required
    def post(self):
        """Add a bookmark for a news article"""
        try:
            # Get the user ID from the token
            auth_header = request.headers.get('Authorization')
            token = auth_header.split()[1]
            payload = jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256'])
            user_id = payload.get('id')

            # Get the news article ID from the request body
            data = request.get_json()
            news_id = data.get('news_id')

            if not news_id:
                return {'error': 'News article ID is required'}, 400

            # Add the bookmark using the news_storage service
            bookmark = add_bookmark(user_id, news_id)
            
            return {
                'status': 'success',
                'message': 'Bookmark added successfully',
                'data': bookmark
            }, 201

        except Exception as e:
            logger.error(f"Error adding bookmark: {str(e)}")
            return {
                'status': 'error',
                'message': str(e)
            }, 500

@bookmark_ns.route('/<string:bookmark_id>')
class BookmarkDelete(Resource):
    @token_required
    def delete(self, bookmark_id):
        """Remove a bookmark for a news article"""
        try:
            # Get the user ID from the token
            auth_header = request.headers.get('Authorization')
            token = auth_header.split()[1]
            payload = jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256'])
            user_id = payload.get('id')

            # Delete the bookmark using the news_storage service
            result = delete_bookmark(user_id, bookmark_id)
            
            return {
                'status': 'success',
                'message': 'Bookmark removed successfully'
            }, 200

        except Exception as e:
            logger.error(f"Error removing bookmark: {str(e)}")
            return {
                'status': 'error',
                'message': str(e)
            }, 500

if __name__ == '__main__':
    port = int(sys.argv[1]) if len(sys.argv) > 1 else Config.API_PORT
    app.run(host=Config.API_HOST, port=port, debug=True)
