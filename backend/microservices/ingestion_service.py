#!/usr/bin/env python3
"""
ingestion_service.py - Microservice for Data Ingestion
Handles incoming data from scrapers, APIs, and RSS feeds,
and passes them to the processing layer.
"""

from flask import Flask, jsonify, request

app = Flask(__name__)

# Simple in-memory storage for demo
articles = {}
current_id = 1

@app.route('/api/news', methods=['GET', 'POST'])
def news():
    global current_id
    if request.method == 'POST':
        data = request.get_json()
        articles[current_id] = data
        response = {'id': current_id, 'message': 'Article created'}
        current_id += 1
        return jsonify(response), 201
    else:
        return jsonify(list(articles.values())), 200

@app.route('/api/news/<int:article_id>', methods=['GET'])
def news_by_id(article_id):
    article = articles.get(article_id)
    if article:
        return jsonify(article), 200
    return jsonify({'error': 'Article not found'}), 404

@app.route('/api/news/search', methods=['GET'])
def search():
    query = request.args.get('q', '').lower()
    results = [
        article for article in articles.values()
        if query in article.get('title', '').lower() or query in article.get('content', '').lower()
    ]
    return jsonify(results), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5002)
