#!/usr/bin/env python3
"""api_gateway.py - API Gateway for the News Aggregator Backend
This Flask application aggregates endpoints from various microservices.
"""

from flask import Flask, jsonify, request
from flask_cors import CORS
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
CORS(app, origins=Config.CORS_ORIGINS)

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({"status": "API Gateway is healthy"}), 200

@app.route('/summarize', methods=['POST'])
@log_exception(logger)
def summarize():
    data = request.get_json()
    article_text = data.get('article_text', '')
    summary = run_summarization(article_text)
    return jsonify({"summary": summary}), 200

@app.route('/api/news/fetch', methods=['GET'])
@log_exception(logger)
def get_news():
    try:
        # Get keyword from query parameters, default to empty string
        keyword = request.args.get('keyword', '')
        
        # Call the fetch_news function with the keyword
        articles = fetch_news(keyword)
        
        return jsonify({
            'status': 'success',
            'data': articles
        }), 200
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@app.route('/api/news/process', methods=['POST'])
@log_exception(logger)
def process_news():
    try:
        process_articles()
        return jsonify({
            'status': 'success',
            'message': 'Articles processed and summarized successfully'
        }), 200
    except Exception as e:
        logger.error(f"Error processing articles: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

if __name__ == '__main__':
    port = int(sys.argv[1]) if len(sys.argv) > 1 else Config.API_PORT
    app.run(host=Config.API_HOST, port=port, debug=True)
