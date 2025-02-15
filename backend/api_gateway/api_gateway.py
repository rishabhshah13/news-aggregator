#!/usr/bin/env python3
"""api_gateway.py - API Gateway for the News Aggregator Backend
This Flask application aggregates endpoints from various microservices.
"""

from flask import Flask, jsonify, request
from flask_cors import CORS
from flask_restx import Api, Resource, fields
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from backend.microservices.summarization_service import run_summarization, process_articles
from backend.microservices.news_fetcher import fetch_news
from backend.core.config import Config
from backend.core.utils import setup_logger, log_exception

# Initialize logger
logger = setup_logger(__name__)

# Initialize Flask app with CORS support
app = Flask(__name__)
CORS(app, origins=Config.CORS_ORIGINS, supports_credentials=True, allow_headers=['Content-Type', 'Authorization'])

# Initialize Flask-RestX
api = Api(app, version='1.0', title='News Aggregator API',
          description='A news aggregation and summarization API')

# Define namespaces
news_ns = api.namespace('api/news', description='News operations')
health_ns = api.namespace('health', description='Health check operations')
summarize_ns = api.namespace('summarize', description='Text summarization operations')

# Define models for documentation
article_model = api.model('Article', {
    'article_text': fields.String(required=True, description='The text to summarize')
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

# News fetch endpoint
@news_ns.route('/fetch')
class NewsFetch(Resource):
    @news_ns.param('keyword', 'Search keyword for news')
    def get(self):
        """Fetch news articles based on keyword"""
        try:
            keyword = request.args.get('keyword', '')
            articles = fetch_news(keyword)
            return {
                'status': 'success',
                'data': articles
            }, 200
        except Exception as e:
            return {
                'status': 'error',
                'message': str(e)
            }, 500

# News processing endpoint
@news_ns.route('/process')
class NewsProcess(Resource):
    def post(self):
        """Process and summarize articles"""
        try:
            summarized_articles = process_articles()
            return {
                'status': 'success',
                'message': 'Articles processed and summarized successfully',
                'data' : summarized_articles
            }, 200
        except Exception as e:
            logger.error(f"Error processing articles: {str(e)}")
            return {
                'status': 'error',
                'message': str(e)
            }, 500

if __name__ == '__main__':
    port = int(sys.argv[1]) if len(sys.argv) > 1 else Config.API_PORT
    app.run(host=Config.API_HOST, port=port, debug=True)
