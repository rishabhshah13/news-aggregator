
#!/usr/bin/env python3
"""API Gateway for the News Aggregator Backend

This module serves as the central API Gateway for the News Aggregator application.
It provides a unified interface for clients to interact with various microservices
including news fetching, summarization, authentication, and story tracking.

Key Features:
- RESTful API endpoints using Flask-RestX
- JWT-based authentication
- CORS support for cross-origin requests
- Swagger documentation
- Error handling and logging
- Integration with multiple microservices

Endpoints:
- /api/news: News fetching and processing
- /health: System health check
- /summarize: Article summarization
- /api/user: User profile management
- /api/auth: Authentication operations
- /api/bookmarks: Bookmark management
- /api/story_tracking: Story tracking functionality
"""

# Standard library imports
from flask import Blueprint, Flask, jsonify, request, make_response
from flask_cors import CORS
from flask_restx import Api, Resource, fields, Namespace
import sys
import os
import jwt
import json
import uuid
import datetime
from datetime import datetime, timedelta
from functools import wraps

# Add project root to Python path for relative imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

print("[DEBUG] [api_gateway] [startup] API Gateway starting up...")

# Load environment variables from .env file
from dotenv import load_dotenv
load_dotenv()
print("[DEBUG] [api_gateway] [startup] Environment variables loaded")

# Import microservices and utilities
from backend.microservices.summarization_service import run_summarization, process_articles
from backend.microservices.news_fetcher import fetch_news
from backend.core.config import Config
from backend.core.utils import setup_logger, log_exception
from backend.microservices.auth_service import load_users
from backend.microservices.news_storage import store_article_in_supabase, log_user_search, add_bookmark, get_user_bookmarks, delete_bookmark
from backend.microservices.story_tracking_service import get_tracked_stories, create_tracked_story, get_story_details, delete_tracked_story


# Initialize logger for the API Gateway
logger = setup_logger(__name__)
print("[DEBUG] [api_gateway] [startup] Logger initialized")

# Initialize Flask application with security configurations
app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('JWT_SECRET_KEY', 'your-secret-key')  # JWT secret key for token signing
print("[DEBUG] [api_gateway] [startup] Flask app initialized with secret key")

# Configure CORS to allow specific origins and methods
CORS(app, 
     origins=["http://localhost:5173", "http://localhost:5001"], 
     supports_credentials=True, 
     allow_headers=["Content-Type", "Authorization"], 
     methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"])
print("[DEBUG] [api_gateway] [startup] CORS configured")

# Initialize Flask-RestX for API documentation
api = Api(app, version='1.0', title='News Aggregator API',
          description='A news aggregation and summarization API')
print("[DEBUG] [api_gateway] [startup] Flask-RestX API initialized")

# Define API namespaces for logical grouping of endpoints
news_ns = api.namespace('api/news', description='News operations')
health_ns = api.namespace('health', description='Health check operations')
summarize_ns = api.namespace('summarize', description='Text summarization operations')
user_ns = api.namespace('api/user', description='User operations')
auth_ns = api.namespace('api/auth', description='Authentication operations')
bookmark_ns = api.namespace('api/bookmarks', description='Bookmark operations')
story_tracking_ns = api.namespace('api/story_tracking', description='Story tracking operations')
print("[DEBUG] [api_gateway] [startup] API namespaces defined")

def token_required(f):
    """Decorator to protect routes that require authentication.
    
    This decorator validates the JWT token in the Authorization header.
    It ensures that only authenticated users can access protected endpoints.
    
    Args:
        f: The function to be decorated.
        
    Returns:
        decorated: The decorated function that includes token validation.
        
    Raises:
        401: If the token is missing or invalid.
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        print("[DEBUG] [api_gateway] [token_required] Checking token in request")
        auth_header = request.headers.get('Authorization')
        if not auth_header:
            print("[DEBUG] [api_gateway] [token_required] Authorization header missing")
            return {'error': 'Authorization header missing'}, 401
        try:
            token = auth_header.split()[1]  # Extract token from 'Bearer <token>'
            print(f"[DEBUG] [api_gateway] [token_required] Decoding token: {token[:10]}...")
            payload = jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256'],audience='authenticated')
            print(f"[DEBUG] [api_gateway] [token_required] Token decoded successfully, user: {payload.get('sub', 'unknown')}")

            return f(*args, **kwargs)
        except Exception as e:
            print(f"[DEBUG] [api_gateway] [token_required] Token validation error: {str(e)}")
            return {'error': 'Invalid token', 'message': str(e)}, 401
    return decorated

# Define API models for request/response documentation
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

# Model for user registration
signup_model = api.model('Signup', {
    'username': fields.String(required=True, description='Username'),
    'password': fields.String(required=True, description='Password'),
    'email': fields.String(required=True, description='Email address'),
    'firstName': fields.String(required=False, description='First name'),
    'lastName': fields.String(required=False, description='Last name')
})

print("[DEBUG] [api_gateway] [startup] API models defined")

# Health check endpoint for system monitoring
@health_ns.route('/')
class HealthCheck(Resource):
    def get(self):
        """Check the health status of the API Gateway.
        
        Returns:
            dict: A dictionary containing the health status.
            int: HTTP 200 status code indicating success.
        """
        print("[DEBUG] [api_gateway] [health_check] Called")
        return {"status": "API Gateway is healthy"}, 200

# Endpoint for article summarization
@summarize_ns.route('/')
class Summarize(Resource):
    @summarize_ns.expect(article_model)
    def post(self):
        """Summarize the provided article text.
        
        Expects a JSON payload with 'article_text' field.
        Uses the summarization service to generate a concise summary.
        
        Returns:
            dict: Contains the generated summary.
            int: HTTP 200 status code on success.
        """
        print("[DEBUG] [api_gateway] [summarize] Called")
        data = request.get_json()
        article_text = data.get('article_text', '')
        print(f"[DEBUG] [api_gateway] [summarize] Summarizing text of length: {len(article_text)}")
        summary = run_summarization(article_text)
        print(f"[DEBUG] [api_gateway] [summarize] Summarization complete, summary length: {len(summary)}")
        return {"summary": summary}, 200

@news_ns.route('/fetch')
class NewsFetch(Resource):
    @news_ns.param('keyword', 'Search keyword for news')
    @news_ns.param('user_id', 'User ID for logging search history')
    @news_ns.param('session_id', 'Session ID for tracking requests')
    def get(self):
        """Fetch news articles based on a keyword and store them in Supabase.
        
        This endpoint fetches news articles matching the provided keyword,
        stores them in Supabase, and logs the search history if a user ID is provided.
        
        Args:
            keyword (str): The search term for fetching news articles.
            user_id (str, optional): User ID for logging search history.
            session_id (str): Session ID for tracking the request.
            
        Returns:
            dict: Contains the stored article IDs and success status.
            int: HTTP 200 on success, 500 on error.
        """
        try:
            keyword = request.args.get('keyword', '')
            user_id = request.args.get('user_id')  # optional
            session_id = request.args.get('session_id')
            print(f"[DEBUG] [api_gateway] [news_fetch] Called with keyword: '{keyword}', user_id: {user_id}, session_id: {session_id}")

            print(f"[DEBUG] [api_gateway] [news_fetch] Fetching news articles for keyword: '{keyword}'")
            articles = fetch_news(keyword)  # This returns a list of articles.
            print(f"[DEBUG] [api_gateway] [news_fetch] Found {len(articles) if articles else 0} articles")
            stored_article_ids = []

            for article in articles:
                print(f"[DEBUG] [api_gateway] [news_fetch] Storing article: {article.get('title', 'No title')}")
                article_id = store_article_in_supabase(article)
                stored_article_ids.append(article_id)
                print(f"[DEBUG] [api_gateway] [news_fetch] Stored article with ID: {article_id}")

                if user_id:
                    print(f"[DEBUG] [api_gateway] [news_fetch] Logging search for user {user_id}, article {article_id}")
                    log_user_search(user_id, article_id, session_id)

            print(f"[DEBUG] [api_gateway] [news_fetch] Returning {len(stored_article_ids)} article IDs")
            return make_response(jsonify({
                'status': 'success',
                'data': stored_article_ids
            }), 200)

        except Exception as e:
            print(f"[DEBUG] [api_gateway] [news_fetch] Error: {str(e)}")
            return make_response(jsonify({
                'status': 'error',
                'message': str(e)
            }), 500)


@news_ns.route('/process')
class NewsProcess(Resource):
    @news_ns.param('session_id', 'Session ID for tracking requests')
    def post(self):
        """Process and summarize a batch of articles.
        
        This endpoint processes articles associated with the provided session ID,
        generating summaries and performing any necessary data transformations.
        
        Args:
            session_id (str): Session ID for tracking the request and identifying articles.
            
        Returns:
            dict: Contains processed articles data and success status.
            int: HTTP 200 on success, 500 on error.
        """
        try:
            session_id = request.args.get('session_id')
            print(f"[DEBUG] [api_gateway] [news_process] Called with session_id: {session_id}")
            print("[DEBUG] [api_gateway] [news_process] Processing articles...")
            summarized_articles = process_articles(session_id)
            print(f"[DEBUG] [api_gateway] [news_process] Processed {len(summarized_articles) if summarized_articles else 0} articles")
            return {
                'status': 'success',
                'message': 'Articles processed and summarized successfully',
                'data' : summarized_articles,
                'session_id': session_id
            }, 200
        except Exception as e:
            print(f"[DEBUG] [api_gateway] [news_process] Error: {str(e)}")
            logger.error(f"Error processing articles: {str(e)}")
            return {
                'status': 'error',
                'message': str(e)
            }, 500

@auth_ns.route('/signup')
class Signup(Resource):
    @auth_ns.expect(signup_model)
    def post(self):
        """Register a new user in the system.
        
        Creates a new user account with the provided information and generates
        a JWT token for immediate authentication.
        
        Expected JSON payload:
        {
            'username': str (required),
            'password': str (required),
            'email': str (required),
            'firstName': str (optional),
            'lastName': str (optional)
        }
        
        Returns:
            dict: Contains user data (excluding password) and JWT token.
            int: HTTP 201 on success, 400 on validation error, 500 on server error.
        """
        print("[DEBUG] [api_gateway] [signup] User signup endpoint called")
        data = request.get_json()
        username = data.get('username')
        password = data.get('password')
        email = data.get('email')
        firstName = data.get('firstName', '')
        lastName = data.get('lastName', '')
        print(f"[DEBUG] [api_gateway] [signup] Request for username: {username}, email: {email}")

        if not username or not password or not email:
            print("[DEBUG] [api_gateway] [signup] Validation failed: missing required fields")
            return {'error': 'Username, password, and email are required'}, 400

        users = load_users()
        print(f"[DEBUG] [api_gateway] [signup] Loaded {len(users)} existing users")

        # Check if username already exists
        if any(u.get('username') == username for u in users):
            print(f"[DEBUG] [api_gateway] [signup] Username {username} already exists")
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
        print(f"[DEBUG] [api_gateway] [signup] Created new user with ID: {new_user['id']}")
        
        users.append(new_user)

        try:
            # Save updated users list
            print("[DEBUG] [api_gateway] [signup] Saving updated users list")
            with open(os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'users.txt'), 'w') as f:
                json.dump(users, f, indent=4)
            print("[DEBUG] [api_gateway] [signup] Users list saved successfully")
        except Exception as e:
            print(f"[DEBUG] [api_gateway] [signup] Error saving user data: {str(e)}")
            return {'error': 'Failed to save user data', 'message': str(e)}, 500

        # Generate JWT token
        print("[DEBUG] [api_gateway] [signup] Generating JWT token")
        token = jwt.encode({
            'id': new_user['id'],
            'username': new_user['username'],
            'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=1)
        }, app.config['SECRET_KEY'], algorithm='HS256')
        print(f"[DEBUG] [api_gateway] [signup] Token generated: {token[:10]}...")

        # Exclude password from response
        user_data = {k: new_user[k] for k in new_user if k != 'password'}
        print("[DEBUG] [api_gateway] [signup] Signup successful")
        return {'message': 'User registered successfully', 'user': user_data, 'token': token}, 201

@auth_ns.route('/login')
class Login(Resource):
    def post(self):
        """Authenticate user and generate JWT token.
        
        Validates user credentials and generates a JWT token for authenticated access.
        
        Expected JSON payload:
        {
            'username': str (required),
            'password': str (required)
        }
        
        Returns:
            dict: Contains user data (excluding password) and JWT token.
            int: HTTP 200 on success, 400 on validation error, 401 on invalid credentials.
        """
        print("[DEBUG] [api_gateway] [login] Login endpoint called")
        data = request.get_json()
        username = data.get('username')
        password = data.get('password')
        print(f"[DEBUG] [api_gateway] [login] Login attempt for username: {username}")
        
        if not username or not password:
            print("[DEBUG] [api_gateway] [login] Validation failed: missing username or password")
            return {'error': 'Username and password are required'}, 400
        
        users = load_users()
        print(f"[DEBUG] [api_gateway] [login] Loaded {len(users)} users")
        user = next((u for u in users if u.get('username') == username and u.get('password') == password), None)
        
        if not user:
            print(f"[DEBUG] [api_gateway] [login] Invalid credentials for username: {username}")
            return {'error': 'Invalid credentials'}, 401
        
        print(f"[DEBUG] [api_gateway] [login] Valid credentials for user: {user.get('id')}")
        print("[DEBUG] [api_gateway] [login] Generating JWT token")
        token = jwt.encode({
            'id': user['id'],
            'username': user['username'],
            'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=1)
        }, app.config['SECRET_KEY'], algorithm='HS256')
        print(f"[DEBUG] [api_gateway] [login] Token generated: {token[:10]}...")
        
        user_data = {k: user[k] for k in user if k != 'password'}
        print("[DEBUG] [api_gateway] [login] Login successful")
        return {'token': token, 'user': user_data}

@user_ns.route('/profile')
class UserProfile(Resource):
    @token_required
    @user_ns.marshal_with(user_profile_model)
    def get(self):
        """Retrieve authenticated user's profile information.
        
        Requires a valid JWT token in the Authorization header.
        Returns the user's profile data excluding sensitive information.
        
        Returns:
            dict: User profile data including id, username, email, and names.
            int: HTTP 200 on success, 404 if user not found.
        """
        print("[DEBUG] [api_gateway] [user_profile] Called")
        auth_header = request.headers.get('Authorization')
        token = auth_header.split()[1]
        print(f"[DEBUG] [api_gateway] [user_profile] Decoding token: {token[:10]}...")
        payload = jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256'])
        print(f"[DEBUG] [api_gateway] [user_profile] Looking up user with ID: {payload.get('id')}")
        
        users = load_users()
        user = next((u for u in users if u.get('id') == payload.get('id')), None)
        if not user:
            print(f"[DEBUG] [api_gateway] [user_profile] User not found with ID: {payload.get('id')}")
            return {'error': 'User not found'}, 404
            
        print(f"[DEBUG] [api_gateway] [user_profile] Found user: {user.get('username')}")
        return {k: user[k] for k in user if k != 'password'}, 200

@bookmark_ns.route('/')
class Bookmark(Resource):
    @token_required
    def get(self):
        """Retrieve all bookmarks for the authenticated user.
        
        Requires a valid JWT token in the Authorization header.
        Returns a list of bookmarked articles for the current user.
        
        Returns:
            dict: Contains list of bookmarked articles and success status.
            int: HTTP 200 on success, 500 on error.
        """
        try:
            print("[DEBUG] [api_gateway] [get_bookmarks] Called")
            auth_header = request.headers.get('Authorization')
            token = auth_header.split()[1]
            print(f"[DEBUG] [api_gateway] [get_bookmarks] Decoding token: {token[:10]}...")
            payload = jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256'],audience='authenticated')
            user_id = payload.get('sub')
            print(f"[DEBUG] [api_gateway] [get_bookmarks] Getting bookmarks for user: {user_id}")

            bookmarks = get_user_bookmarks(user_id)
            print(f"[DEBUG] [api_gateway] [get_bookmarks] Found {len(bookmarks)} bookmarks")

            return {
                'status': 'success',
                'data': bookmarks
            }, 200

        except Exception as e:
            print(f"[DEBUG] [api_gateway] [get_bookmarks] Error: {str(e)}")
            logger.error(f"Error fetching bookmarks: {str(e)}")
            return {
                'status': 'error',
                'message': str(e)
            }, 500

    @token_required
    def post(self):
        """Add a new bookmark for the authenticated user.
        
        Requires a valid JWT token in the Authorization header.
        Creates a bookmark linking the user to a specific news article.
        
        Expected JSON payload:
        {
            'news_id': str (required)
        }
        
        Returns:
            dict: Contains bookmark ID and success status.
            int: HTTP 201 on success, 400 on validation error, 500 on server error.
        """
        try:
            print("[DEBUG] [api_gateway] [add_bookmark] Called")
            auth_header = request.headers.get('Authorization')
            token = auth_header.split()[1]
            print(f"[DEBUG] [api_gateway] [add_bookmark] Decoding token: {token[:10]}...")
            payload = jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256'],audience='authenticated')
            user_id = payload.get('sub')
            print(f"[DEBUG] [api_gateway] [add_bookmark] Adding bookmark for user: {user_id}")

            data = request.get_json()
            news_id = data.get('news_id')
            print(f"[DEBUG] [api_gateway] [add_bookmark] News article ID: {news_id}")

            if not news_id:
                print("[DEBUG] [api_gateway] [add_bookmark] News article ID missing in request")
                return {'error': 'News article ID is required'}, 400

            print(f"[DEBUG] [api_gateway] [add_bookmark] Adding bookmark for user {user_id}, article {news_id}")
            bookmark = add_bookmark(user_id, news_id)
            print(f"[DEBUG] [api_gateway] [add_bookmark] Bookmark added with ID: {bookmark['id'] if isinstance(bookmark, dict) else bookmark}")
            
            return {
                'status': 'success',
                'message': 'Bookmark added successfully',
                'data': {
                    'bookmark_id': bookmark['id'] if isinstance(bookmark, dict) else bookmark
                }
            }, 201

        except Exception as e:
            print(f"[DEBUG] [api_gateway] [add_bookmark] Error: {str(e)}")
            logger.error(f"Error adding bookmark: {str(e)}")
            return {
                'status': 'error',
                'message': str(e)
            }, 500

@bookmark_ns.route('/<string:bookmark_id>')
class BookmarkDelete(Resource):
    @token_required
    def delete(self, bookmark_id):
        """Remove a bookmark for a news article.

        Requires a valid JWT token in the Authorization header.
        Deletes the specified bookmark for the authenticated user.

        Args:
            bookmark_id (str): The ID of the bookmark to be deleted.

        Returns:
            dict: Contains success message.
            int: HTTP 200 on success, 500 on error.
        """
        try:
            print(f"[DEBUG] [api_gateway] [delete_bookmark] Called for bookmark: {bookmark_id}")
            auth_header = request.headers.get('Authorization')
            token = auth_header.split()[1]
            print(f"[DEBUG] [api_gateway] [delete_bookmark] Decoding token: {token[:10]}...")
            payload = jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256'],audience='authenticated')
            user_id = payload.get('sub')
            print(f"[DEBUG] [api_gateway] [delete_bookmark] Deleting bookmark {bookmark_id} for user {user_id}")

            result = delete_bookmark(user_id, bookmark_id)
            print(f"[DEBUG] [api_gateway] [delete_bookmark] Deletion result: {result}")
            
            return {
                'status': 'success',
                'message': 'Bookmark removed successfully'
            }, 200

        except Exception as e:
            print(f"[DEBUG] [api_gateway] [delete_bookmark] Error: {str(e)}")
            logger.error(f"Error removing bookmark: {str(e)}")
            return {
                'status': 'error',
                'message': str(e)
            }, 500

@story_tracking_ns.route('/')
class StoryTracking(Resource):
    @story_tracking_ns.param('keyword', 'Keyword to track for news updates')
    def get(self):
        """Fetch latest news for a tracked keyword.

        Retrieves and processes the latest news articles for a given keyword.

        Args:
            keyword (str): The keyword to search for news articles.

        Returns:
            dict: Contains list of processed articles and success status.
            int: HTTP 200 on success, 400 if keyword is missing, 500 on error.
        """
        try:
            print("[DEBUG] [api_gateway] [story_tracking] Story tracking get endpoint called")
            keyword = request.args.get('keyword')
            print(f"[DEBUG] [api_gateway] [story_tracking] Requested keyword: '{keyword}'")
            if not keyword:
                print("[DEBUG] [api_gateway] [story_tracking] Keyword parameter missing")
                return make_response(jsonify({
                    'status': 'error',
                    'message': 'Keyword parameter is required'
                }), 400)

            print(f"[DEBUG] [api_gateway] [story_tracking] Fetching news for keyword: '{keyword}'")
            articles = fetch_news(keyword)
            print(f"[DEBUG] [api_gateway] [story_tracking] Found {len(articles) if articles else 0} articles")
            
            processed_articles = []
            for article in articles:
                print(f"[DEBUG] [api_gateway] [story_tracking] Processing article: {article.get('title', 'No title')}")
                article_id = store_article_in_supabase(article)
                print(f"[DEBUG] [api_gateway] [story_tracking] Stored article with ID: {article_id}")
                processed_articles.append({
                    'id': article_id,
                    'title': article.get('title'),
                    'url': article.get('url'),
                    'source': article.get('source', {}).get('name') if isinstance(article.get('source'), dict) else article.get('source'),
                    'publishedAt': article.get('publishedAt', datetime.now().isoformat())
                })

            print(f"[DEBUG] [api_gateway] [story_tracking] Returning {len(processed_articles)} processed articles")
            return make_response(jsonify({
                'status': 'success',
                'articles': processed_articles
            }), 200)

        except Exception as e:
            print(f"[DEBUG] [api_gateway] [story_tracking] Error: {str(e)}")
            logger.error(f"Error in story tracking: {str(e)}")
            return make_response(jsonify({
                'status': 'error',
                'message': str(e)
            }), 500)
    
    @token_required
    def post(self):
        """Create a new tracked story.

        Requires a valid JWT token in the Authorization header.
        Creates a new tracked story for the authenticated user based on a keyword and source article.

        Expected JSON payload:
        {
            'keyword': str (required),
            'sourceArticleId': str (optional)
        }

        Returns:
            dict: Contains created story details and success status.
            int: HTTP 201 on success, 400 on validation error, 500 on server error.
        """
        try:
            print("[DEBUG] [api_gateway] [story_tracking] Called")
            auth_header = request.headers.get('Authorization')
            token = auth_header.split()[1]
            print(f"[DEBUG] [api_gateway] [story_tracking] Decoding token: {token[:10]}...")
            payload = jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256'], audience='authenticated')
            user_id = payload.get('sub')
            print(f"[DEBUG] [api_gateway] [story_tracking] Creating tracked story for user: {user_id}")
            
            data = request.get_json()
            keyword = data.get('keyword')
            source_article_id = data.get('sourceArticleId')
            print(f"[DEBUG] [api_gateway] [story_tracking] Story details - Keyword: '{keyword}', Source article: {source_article_id}")
            
            if not keyword:
                print("[DEBUG] [api_gateway] [story_tracking] Keyword parameter missing in request")
                return make_response(jsonify({
                    'status': 'error',
                    'message': 'Keyword is required'
                }), 400)
            
            print(f"[DEBUG] [api_gateway] [story_tracking] Calling create_tracked_story with user_id: {user_id}, keyword: '{keyword}'")
            tracked_story = create_tracked_story(user_id, keyword, source_article_id)
            print(f"[DEBUG] [api_gateway] [story_tracking] Tracked story created with ID: {tracked_story['id'] if tracked_story else 'unknown'}")
            
            print(f"[DEBUG] [api_gateway] [story_tracking] Getting full story details for story: {tracked_story['id']}")
            story_with_articles = get_story_details(tracked_story['id'])
            print(f"[DEBUG] [api_gateway] [story_tracking] Found {len(story_with_articles.get('articles', [])) if story_with_articles else 0} related articles")
            
            return make_response(jsonify({
                'status': 'success',
                'data': story_with_articles
            }), 201)
            
        except Exception as e:
            print(f"[DEBUG] [api_gateway] [story_tracking] Error: {str(e)}")
            logger.error(f"Error creating tracked story: {str(e)}")
            return make_response(jsonify({
                'status': 'error',
                'message': str(e)
            }), 500)

@story_tracking_ns.route('/user')
class UserStoryTracking(Resource):
    @token_required
    def get(self):
        """Get all tracked stories for the authenticated user.

        Requires a valid JWT token in the Authorization header.
        Retrieves all tracked stories associated with the authenticated user.

        Returns:
            dict: Contains list of tracked stories and success status.
            int: HTTP 200 on success, 500 on error.
        """
        try:
            print("[DEBUG] [api_gateway] [user_story_tracking] Called")
            auth_header = request.headers.get('Authorization')
            token = auth_header.split()[1]
            print(f"[DEBUG] [api_gateway] [user_story_tracking] Decoding token: {token[:10]}...")
            payload = jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256'], audience='authenticated')
            user_id = payload.get('sub')
            print(f"[DEBUG] [api_gateway] [user_story_tracking] Getting tracked stories for user: {user_id}")
            
            print(f"[DEBUG] [api_gateway] [user_story_tracking] Calling get_tracked_stories")
            tracked_stories = get_tracked_stories(user_id)
            print(f"[DEBUG] [api_gateway] [user_story_tracking] Found {len(tracked_stories)} tracked stories")
            
            return make_response(jsonify({
                'status': 'success',
                'data': tracked_stories
            }), 200)
            
        except Exception as e:
            print(f"[DEBUG] [api_gateway] [user_story_tracking] Error: {str(e)}")
            logger.error(f"Error getting tracked stories: {str(e)}")
            return make_response(jsonify({
                'status': 'error',
                'message': str(e)
            }), 500)

@story_tracking_ns.route('/<string:story_id>')
class StoryTrackingDetail(Resource):
    @token_required
    def get(self, story_id):
        """Get details for a specific tracked story.

        Requires a valid JWT token in the Authorization header.
        Retrieves detailed information about a specific tracked story.

        Args:
            story_id (str): The ID of the tracked story to retrieve.

        Returns:
            dict: Contains story details and success status.
            int: HTTP 200 on success, 404 if story not found, 500 on error.
        """
        try:
            print(f"[DEBUG] [api_gateway] [story_tracking_detail] Called for story: {story_id}")
            print(f"[DEBUG] [api_gateway] [story_tracking_detail] Calling get_story_details for story: {story_id}")
            story = get_story_details(story_id)
            
            if not story:
                print(f"[DEBUG] [api_gateway] [story_tracking_detail] No story found with ID: {story_id}")
                return make_response(jsonify({
                    'status': 'error',
                    'message': 'Tracked story not found'
                }), 404)
            
            print(f"[DEBUG] [api_gateway] [story_tracking_detail] Found story: {story['keyword']}")
            print(f"[DEBUG] [api_gateway] [story_tracking_detail] Story has {len(story.get('articles', []))} articles")
            return make_response(jsonify({
                'status': 'success',
                'data': story
            }), 200)
            
        except Exception as e:
            print(f"[DEBUG] [api_gateway] [story_tracking_detail] Error: {str(e)}")
            logger.error(f"Error getting story details: {str(e)}")
            return make_response(jsonify({
                'status': 'error',
                'message': str(e)
            }), 500)
    
    @token_required
    def delete(self, story_id):
        """Stop tracking a story.

        Requires a valid JWT token in the Authorization header.
        Deletes a tracked story for the authenticated user.

        Args:
            story_id (str): The ID of the tracked story to delete.

        Returns:
            dict: Contains success message.
            int: HTTP 200 on success, 404 if story not found, 500 on error.
        """
        try:
            print(f"[DEBUG] [api_gateway] [delete_story_tracking] Called for story: {story_id}")
            auth_header = request.headers.get('Authorization')
            token = auth_header.split()[1]
            print(f"[DEBUG] [api_gateway] [delete_story_tracking] Decoding token: {token[:10]}...")
            payload = jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256'], audience='authenticated')
            user_id = payload.get('sub')
            print(f"[DEBUG] [api_gateway] [delete_story_tracking] Deleting tracked story {story_id} for user {user_id}")
            
            print(f"[DEBUG] [api_gateway] [delete_story_tracking] Calling delete_tracked_story")
            success = delete_tracked_story(user_id, story_id)
            print(f"[DEBUG] [api_gateway] [delete_story_tracking] Delete result: {success}")
            
            if not success:
                print(f"[DEBUG] [api_gateway] [delete_story_tracking] Failed to delete story or story not found")
                return make_response(jsonify({
                    'status': 'error',
                    'message': 'Failed to delete tracked story or story not found'
                }), 404)
            
            print(f"[DEBUG] [api_gateway] [delete_story_tracking] Story deleted successfully")
            return make_response(jsonify({
                'status': 'success',
                'message': 'Tracked story deleted successfully'
            }), 200)
            
        except Exception as e:
            print(f"[DEBUG] [api_gateway] [delete_story_tracking] Error: {str(e)}")
            logger.error(f"Error deleting tracked story: {str(e)}")
            return make_response(jsonify({
                'status': 'error',
                'message': str(e)
            }), 500)

@app.route('/api/story_tracking', methods=['OPTIONS'])
def story_tracking_options():
    """Handle OPTIONS requests for the story tracking endpoint.

    This function sets the necessary CORS headers for preflight requests
    to the story tracking endpoint.

    Returns:
        Response: A Flask response object with appropriate CORS headers.
    """
    print("[DEBUG] [api_gateway] [story_tracking_options] Called")
    response = make_response()
    response.headers.add("Access-Control-Allow-Origin", "*")
    response.headers.add("Access-Control-Allow-Headers", "Content-Type,Authorization")
    response.headers.add("Access-Control-Allow-Methods", "GET,POST,PUT,DELETE,OPTIONS")
    print("[DEBUG] [api_gateway] [story_tracking_options] Responding with CORS headers")
    return response

if __name__ == '__main__':
    # Read the port from the environment (Cloud Run sets the PORT variable)
    port = int(os.environ.get("PORT", Config.API_PORT))
    # Listen on 0.0.0.0 so the service is reachable externally
    print(f"[DEBUG] [api_gateway] [main] Starting on {Config.API_HOST}:{port} with debug={True}")
    app.run(host="0.0.0.0", port=port, debug=True)
