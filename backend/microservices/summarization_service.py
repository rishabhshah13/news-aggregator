#!/usr/bin/env python3
"""
Summarization Service Module

This module provides functionality for fetching, processing, and summarizing news articles.
It includes capabilities for content extraction, text summarization, and keyword extraction.

Key Features:
- Article content fetching from URLs
- Text summarization using OpenAI's GPT models
- Keyword extraction using YAKE
- Integration with Supabase for data persistence
"""

import json
import requests
from bs4 import BeautifulSoup
import openai
from backend.core.config import Config
from backend.core.utils import setup_logger, log_exception
import yake
import os

# Initialize logger
logger = setup_logger(__name__)

# Configure OpenAI with your API key from environment variables
openai.api_key = Config.OPENAI_API_KEY

# No need to instantiate a client object; we'll use openai.ChatCompletion.create directly.

from supabase import create_client, Client  # Make sure you're using supabase-py or your preferred client

from dotenv import load_dotenv
load_dotenv('../../.env')  # Optional: Only use this for local development.

# Use your service key here for secure server-side operations.
SUPABASE_URL = os.getenv("VITE_SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.getenv("VITE_SUPABASE_ANON_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)


@log_exception(logger)
def fetch_article_content(url):
    """
    Fetches and extracts the main content from a given URL.

    Args:
        url (str): The URL of the article to fetch content from.

    Returns:
        str or None: The extracted article content as plain text.
                    Returns None if the fetch fails or content is invalid.
    """
    try:
        if not url or not url.startswith('http'):
            logger.error(f"Invalid URL format: {url}")
            return None

        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        paragraphs = soup.find_all('p')
        
        if not paragraphs:
            logger.warning(f"No content found at URL: {url}")
            return None
            
        content = ' '.join([p.get_text() for p in paragraphs])
        return content
        
    except requests.exceptions.Timeout:
        logger.error(f"Request timed out for URL: {url}")
        return None
    except requests.exceptions.SSLError:
        logger.error(f"SSL verification failed for URL: {url}")
        return None
    except requests.exceptions.ConnectionError:
        logger.error(f"Failed to connect to URL: {url}")
        return None
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching article content from {url}: {str(e)}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error processing {url}: {str(e)}")
        return None


@log_exception(logger)
def run_summarization(text):
    """
    Generates a concise summary of the provided text using OpenAI's GPT model.

    Args:
        text (str): The input text to be summarized.

    Returns:
        str: A summarized version of the input text (approximately 150 words).
             Returns an error message if summarization fails.

    Note:
        Uses OpenAI's GPT-4 (or your specified model) with specific parameters:
        - Temperature: 0.5
        - Max tokens: 200
    """
    try:
        response = openai.ChatCompletion.create(
            model="gpt-4o-mini",  # Change to your desired model (e.g., "gpt-3.5-turbo")
            messages=[
                {"role": "system", "content": "You are a helpful assistant that summarizes text in approximately 150 words."},
                {"role": "user", "content": f"Please summarize the following text:\n\n{text}"}
            ],
            max_tokens=200,
            temperature=0.5
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        logger.error(f"Error in summarization: {str(e)}")
        return "Error generating summary"


@log_exception(logger)
def get_keywords(text, num_keywords=1):
    """
    Extracts key phrases from the input text using YAKE keyword extraction.

    Args:
        text (str): The input text to extract keywords from.
        num_keywords (int, optional): Number of keywords to extract. Defaults to 1.

    Returns:
        list: A list of extracted keywords/key phrases.
    """
    kw_extractor = yake.KeywordExtractor(top=num_keywords, lan='en')
    keywords = kw_extractor.extract_keywords(text)
    return [kw[0] for kw in keywords]


@log_exception(logger)
def process_articles(session_id):
    """
    Processes a batch of articles associated with a specific session ID.
    
    This function performs the following operations:
    1. Retrieves articles from Supabase based on the session ID.
    2. Fetches missing content for articles if needed.
    3. Generates summaries for each article.
    4. Extracts keywords for filtering.
    
    Args:
        session_id (str): The unique identifier for the user session.

    Returns:
        list: A list of dictionaries containing processed article data.
    """
    try:
        history_result = supabase.table("user_search_history").select("news_id").eq("session_id", session_id).execute()
        article_ids = [record["news_id"] for record in history_result.data]

        articles = []
        if article_ids:
            result = supabase.table("news_articles").select("*").in_("id", article_ids).execute()
            articles = result.data

        summarized_articles = []
        for article in articles:
            logger.info(f"Processing article: {article['title']}")
            
            content = article.get('content')
            if not content:
                content = fetch_article_content(article['url'])
            
            if content:
                summary = run_summarization(content)
            else:
                summary = run_summarization(article.get('content', ''))
            
            summarized_articles.append({
                'id': article['id'],
                'title': article['title'],
                'author': article.get('author', 'Unknown Author'),
                'source': article.get('source'),
                'publishedAt': article.get('published_at'),
                'url': article['url'],
                'urlToImage': article.get('image'),
                'content': article.get('content', ''),
                'summary': summary,
                'filter_keywords': get_keywords(article.get('content', ''))
            })

        return summarized_articles

    except Exception as e:
        logger.error(f"Error processing articles: {str(e)}")
        raise e


if __name__ == '__main__':
    process_articles()