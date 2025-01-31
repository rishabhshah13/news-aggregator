#!/usr/bin/env python3
"""
api_connector.py - Module to interface with external news APIs.
This script demonstrates how to fetch data from a news API.
"""

import requests

def fetch_news(api_url, params):
    """
    Fetches news articles from the given API endpoint.
    :param api_url: The API endpoint URL.
    :param params: Dictionary of query parameters (including API keys).
    :return: JSON response as a Python dict if successful, else empty dict.
    """
    try:
        response = requests.get(api_url, params=params)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        print(f"API request error: {e}")
        return {}

if __name__ == '__main__':
    # Example usage: Replace YOUR_API_KEY with a valid key.
    sample_api_url = "https://newsapi.org/v2/top-headlines"
    sample_params = {"country": "us", "apiKey": "YOUR_API_KEY"}
    data = fetch_news(sample_api_url, sample_params)
    print("API Response:")
    print(data)
