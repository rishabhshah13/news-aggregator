#!/usr/bin/env python3
"""
scraper.py - Web scraper module for the news aggregator.
This script uses requests and BeautifulSoup to fetch and parse news articles.
"""

import requests
from bs4 import BeautifulSoup

def scrape(url):
    """
    Fetches the HTML content of a URL and extracts text.
    :param url: The URL of the news page to scrape.
    :return: The extracted text content.
    """
    try:
        response = requests.get(url)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        return soup.get_text()
    except requests.RequestException as e:
        print(f"Error scraping {url}: {e}")
        return None

if __name__ == '__main__':
    # Example usage: Scrape a sample URL.
    sample_url = "https://example.com/news"
    content = scrape(sample_url)
    if content:
        print("Scraped Content:")
        print(content)
    else:
        print("Scraping failed.")
