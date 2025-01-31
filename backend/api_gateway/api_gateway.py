#!/usr/bin/env python3
"""
api_gateway.py - API Gateway for the News Aggregator Backend
This Flask application aggregates endpoints from various microservices.
"""

from flask import Flask, jsonify, request
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from backend.microservices.summarization_service import run_summarization

# Add project root to Python path

app = Flask(__name__)

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({"status": "API Gateway is healthy"}), 200

# Example endpoint for summarization service
@app.route('/summarize', methods=['POST'])
def summarize():
    try:
        data = request.get_json()
        article_text = data.get('article_text', '')
        # Updated import path to match project structure
        summary = run_summarization(article_text)
        return jsonify({"summary": summary}), 200
    except Exception as e:
        print(f"Errorftgyhujk: {str(e)}")
        return jsonify({"error": "Summarization failed"}), 500

if __name__ == '__main__':
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 5000
    app.run(host='0.0.0.0', port=port)
