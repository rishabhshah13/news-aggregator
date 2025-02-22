#!/usr/bin/env python3
"""
summarization_service.py - Microservice for Summarization
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

# Configure OpenAI
openai.api_key = Config.OPENAI_API_KEY
client = openai.OpenAI()
from supabase import create_client, Client  # Make sure you're using supabase-py or your preferred client

from dotenv import load_dotenv
load_dotenv('../../.env')

# Use your service key here for secure server-side operations.
SUPABASE_URL = os.getenv("VITE_SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.getenv("VITE_SUPABASE_ANON_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)


@log_exception(logger)
def fetch_article_content(url):
    try:
        # Check if URL is valid
        if not url or not url.startswith('http'):
            logger.error(f"Invalid URL format: {url}")
            return None

        # Set timeout and headers for request
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
    try:
        return "Summarized text here"
    
    #     model="gpt-3.5 turbo",
        response = client.chat.completions.create(
        model="gpt-4o-mini",
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
def get_keywords(text,num_keywords=1):
    kw_extractor = yake.KeywordExtractor(top=num_keywords, lan='en')
    keywords = kw_extractor.extract_keywords(text)
    return [kw[0] for kw in keywords]


@log_exception(logger)
def process_articles(session_id):
    try:
        # Query only articles that belong to the current session.
        # result = supabase.table("news_articles").select("*").eq("session_id", session_id).execute()
        # articles = result.data
        
        # First, query the user_search_history table for records with this session_id.
        history_result = supabase.table("user_search_history").select("news_id").eq("session_id", session_id).execute()
        article_ids = [record["news_id"] for record in history_result.data]

        # Now, query the news_articles table for those article IDs.
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

        # Optionally, save or return the summarized articles.
        # output_file = f'{session_id}_summarized_news.json'
        # output_path = Config.get_summarized_news_path() / output_file
        # with open(output_path, 'w') as file:
        #     json.dump(summarized_articles, file, indent=4)
        # logger.info(f"Summarized articles saved to {output_path}")

        return summarized_articles

    except Exception as e:
        logger.error(f"Error processing articles: {str(e)}")
        raise e
    

if __name__ == '__main__':
    process_articles()
