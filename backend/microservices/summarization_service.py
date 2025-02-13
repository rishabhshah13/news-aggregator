#!/usr/bin/env python3
"""
summarization_service.py - Microservice for Summarization
"""

import os
import openai
import json
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv

load_dotenv()

# Configure OpenAI
openai.api_key = os.getenv('OPENAI_API_KEY')

def fetch_article_content(url):
    try:
        # Check if URL is valid
        if not url or not url.startswith('http'):
            print(f"Invalid URL format: {url}")
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
            print(f"No content found at URL: {url}")
            return None
            
        content = ' '.join([p.get_text() for p in paragraphs])
        return content
        
    except requests.exceptions.Timeout:
        print(f"Request timed out for URL: {url}")
        return None
    except requests.exceptions.SSLError:
        print(f"SSL verification failed for URL: {url}")
        return None
    except requests.exceptions.ConnectionError:
        print(f"Failed to connect to URL: {url}")
        return None
    except requests.exceptions.RequestException as e:
        print(f"Error fetching article content from {url}: {str(e)}")
        return None
    except Exception as e:
        print(f"Unexpected error processing {url}: {str(e)}")
        return None

def run_summarization(text):
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a helpful assistant that summarizes text in approximately 150 words."},
                {"role": "user", "content": f"Please summarize the following text:\n\n{text}"}
            ],
            max_tokens=200,
            temperature=0.5
        )
        return response.choices[0].message['content'].strip()
    except Exception as e:
        print(f"Error in summarization: {str(e)}")
        return "Error generating summary"

def process_articles():
    try:
        # Read the news data
        with open('/Users/akalpitdawkhar/prog_news/news-aggregator/backend/microservices/news_data.json', 'r') as file:
            articles = json.load(file)

        summarized_articles = []
        for article in articles:
            print(f"Processing article: {article['title']}")
            
            # Fetch full article content from URL
            content = fetch_article_content(article['url'])
            if content:
                summary = run_summarization(content)
            else:
                summary = run_summarization(article.get('content', ''))

            summarized_articles.append({
                'title': article['title'],
                'author': article.get('author', 'Unknown Author'),
                'source': article['source']['name'],
                'publishedAt': article['publishedAt'],
                'url': article['url'],
                'urlToImage': article.get('urlToImage'),
                'content': article.get('content', ''),
                'summary': summary
            })

        # Save summarized articles
        output_path = '/Users/akalpitdawkhar/prog_news/news-aggregator-frontend/public/summarized_news.json'
        with open(output_path, 'w') as file:
            json.dump(summarized_articles, file, indent=4)
        print(f"Summarized articles saved to {output_path}")

    except Exception as e:
        print(f"Error processing articles: {str(e)}")

if __name__ == '__main__':
    process_articles()
