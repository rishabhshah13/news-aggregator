import os
import requests
from dotenv import load_dotenv
import json
from backend.core.config import Config


# Load environment variables from .env file
load_dotenv()

# Get the News API key from environment variables
NEWS_API_KEY = os.getenv('NEWS_API_KEY')

def fetch_news(keyword=''):
    # Define the News API endpoint and parameters
    url = "https://newsapi.org/v2/top-headlines"
    params = {
        'q': keyword,  # Use the keyword for search
        'apiKey': NEWS_API_KEY,
        'pageSize': 20
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
                write_to_file(articles)
                for article in articles:
                    print(f"Title: {article['title']}")
                    print(f"Description: {article['description']}")
                    print(f"URL: {article['url']}\n")
            
            return articles
        else:
            print("Failed to fetch news:", news_data.get('message'))

    except requests.exceptions.RequestException as e:
        print(f"Error fetching news: {e}")

def write_to_file(articles):
    # Define the file path
    # file_path = '/Users/akalpitdawkhar/prog_news/news-aggregator/backend/microservices/news_data.json'
    file_path = Config.NEWS_DATA_DIR / 'news_data.json'
    try:
        # Write articles to the file in JSON format
        with open(file_path, 'w') as file:
            json.dump(articles, file, indent=4)
        print(f"Articles saved to {file_path}")
    except IOError as e:
        print(f"Error writing to file: {e}")

if __name__ == '__main__':
    fetch_news()