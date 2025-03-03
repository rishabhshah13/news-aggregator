"""News Fetcher Service

This module is responsible for fetching news articles from the News API based on
keywords and managing the storage of fetched articles. It provides functionality
to search for news articles and optionally save them to files with session-based
organization.

The module uses the News API (https://newsapi.org/) as its primary data source
and supports session-based article management for multi-user scenarios.

Typical usage:
    articles = fetch_news('technology')
    write_to_file(articles, 'user_session_123')

Environment Variables Required:
    NEWS_API_KEY: API key for accessing the News API service
"""

import os
import requests
from dotenv import load_dotenv
import json
from pathlib import Path
from backend.core.config import Config

# Load environment variables from .env file for configuration
load_dotenv()

# Initialize the News API key from environment variables
NEWS_API_KEY = os.getenv('NEWS_API_KEY')

def fetch_news(keyword='', session_id=None):
    """Fetch news articles from News API based on a keyword search.

    This function queries the News API to retrieve articles matching the provided
    keyword. It supports session-based tracking of requests and can handle empty
    keyword searches.

    Args:
        keyword (str, optional): The search term to find relevant articles.
            Defaults to empty string which returns top headlines.
        session_id (str, optional): Unique identifier for the current user session.
            Used for organizing saved articles. Defaults to None.

    Returns:
        list: A list of dictionaries containing article data with fields like
            'title', 'description', 'url', etc. Returns None on error.

    Raises:
        requests.exceptions.RequestException: If there's an error communicating
            with the News API.
    """
    # Configure the News API endpoint and request parameters
    url = "https://newsapi.org/v2/everything"
    params = {
        'q': keyword,  # Search query parameter
        'apiKey': NEWS_API_KEY,
        'pageSize': 1  # Limit results to 10 articles per request
    }

    try:
        # Make a GET request to the News API
        response = requests.get(url, params=params)
        response.raise_for_status()

        # Process the response data
        news_data = response.json()
        if news_data.get('status') == 'ok':
            articles = news_data.get('articles', [])
            if not articles:
                print("No articles found for the given keyword.")
            else:
                pass
                # Use session_id in the filename if provided
                # if session_id:
                #     write_to_file(articles, session_id)
                # else:
                #     write_to_file(articles)
                # for article in articles:
                #     print(f"Title: {article['title']}")
                #     print(f"Description: {article['description']}")
                #     print(f"URL: {article['url']}\n")
            
            return articles
        else:
            print("Failed to fetch news:", news_data.get('message'))

    except requests.exceptions.RequestException as e:
        print(f"Error fetching news: {e}")

def write_to_file(articles, session_id=None):
    """Save fetched news articles to a JSON file.

    This function stores the provided articles in a JSON file, organizing them
    by session ID. It creates the necessary directories if they don't exist.

    Args:
        articles (list): List of article dictionaries to save.
        session_id (str, optional): Unique identifier for the current session.
            Used to create a unique filename. Defaults to 'default' if None.

    Returns:
        None

    Raises:
        IOError: If there's an error writing to the file system.
    """
    # Use default session ID if none provided
    if not session_id:
        session_id = 'default'
    
    # Generate a unique filename using the session ID
    file_name = f'{session_id}_news_data.json'
    
    # Construct the full file path using the configured data directory
    file_path = Config.NEWS_DATA_DIR / file_name
    try:
        # Save the articles as formatted JSON for better readability
        with open(file_path, 'w') as file:
            json.dump(articles, file, indent=4)
        print(f"Articles successfully saved to {file_path}")
    except IOError as e:
        print(f"Error writing to file: {e}")

if __name__ == '__main__':
    fetch_news()





