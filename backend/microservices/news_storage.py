# backend/microservices/news_storage.py
"""
News Storage Service - Supabase Database Integration Module

This module provides functions for storing and retrieving news articles and user interactions
with the Supabase database. It handles article storage, user search history logging, and bookmark
management operations.

The module uses the Supabase client to interact with the following tables:
- news_articles: Stores article content and metadata
- user_search_history: Tracks user search interactions
- user_bookmarks: Manages user article bookmarks

Environment Variables Required:
- VITE_SUPABASE_URL: Supabase project URL
- VITE_SUPABASE_ANON_KEY: Supabase anonymous key for client operations
"""

import os
import datetime
from supabase import create_client, Client
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv('../../.env')

# Initialize Supabase client with environment variables
SUPABASE_URL = os.getenv("VITE_SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.getenv("VITE_SUPABASE_ANON_KEY")  # Using anon key for server-side operations
supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

def store_article_in_supabase(article):
    """
    Inserts a news article into the Supabase news_articles table if it doesn't already exist.
    
    This function first checks if an article with the same URL already exists in the database.
    If it does, the function returns the existing article's ID. Otherwise, it inserts the new
    article and returns the newly created ID. Uniqueness is enforced by the URL field (which 
    is UNIQUE in the table).
    
    Args:
        article (dict): A dictionary containing article data with the following keys:
            - title (str): The article title
            - summary (str, optional): A summary of the article
            - content (str, optional): The full article content
            - source (dict or str): The source of the article
            - publishedAt (str): Publication date in ISO format
            - url (str): The unique URL to the article
            - urlToImage (str, optional): URL to the article's image
    
    Returns:
        str: The ID of the article (either existing or newly created)
    """
    # Check if the article already exists using the URL as unique identifier
    existing = supabase.table("news_articles").select("*").eq("url", article["url"]).execute()
    if existing.data and len(existing.data) > 0:
        # Article already exists; return its id
        return existing.data[0]["id"]
    else:
        # Insert a new article with all available fields
        result = supabase.table("news_articles").insert({
            "title": article["title"],
            "summary": article.get("summary", ""),
            "content": article.get("content", ""),
            # Handle source field which can be a dict (from API) or a plain string
            "source": article["source"]["name"] if isinstance(article.get("source"), dict) else article["source"],
            "published_at": article["publishedAt"],
            "url": article["url"],
            "image": article.get("urlToImage", "")
        }).execute()
        return result.data[0]["id"]

def log_user_search(user_id, news_id, session_id):
    """
    Logs a search event by inserting a record into the user_search_history join table.
    
    This function creates a record of a user viewing or searching for a specific article,
    which can be used for analytics, personalization, and tracking user activity across sessions.
    
    Args:
        user_id (str): The ID of the user performing the search
        news_id (str): The ID of the news article that was viewed/searched
        session_id (str): The current session identifier for tracking user activity
    
    Returns:
        dict: The Supabase response object containing the result of the insert operation
    """
    # Create a timestamp for when the search occurred
    current_time = datetime.datetime.utcnow().isoformat()
    
    # Insert the search record with all required fields
    result = supabase.table("user_search_history").insert({
        "user_id": user_id,
        "news_id": news_id,
        "searched_at": current_time,
        "session_id": session_id,
    }).execute()
    return result

def add_bookmark(user_id, news_id):
    """
    Adds a bookmark by inserting a record into the user_bookmarks table.
    
    This function creates a bookmark relationship between a user and a news article,
    allowing users to save articles for later reading.
    
    Args:
        user_id (str): The ID of the user adding the bookmark
        news_id (str): The ID of the news article to bookmark
    
    Returns:
        dict or None: The created bookmark record if successful, None otherwise
    
    Raises:
        Exception: If there's an error during the database operation
    """
    try:
        # Insert a new bookmark record linking user to article
        result = supabase.table("user_bookmarks").insert({
            "user_id": user_id,
            "news_id": news_id,
        }).execute()
        
        # Return the first data item if available, otherwise None
        return result.data[0] if result.data else None
    except Exception as e:
        print(f"Error adding bookmark: {str(e)}")
        # Re-raise the exception for proper error handling upstream
        raise e

def get_user_bookmarks(user_id):
    """
    Retrieves all bookmarked articles for a user with full article details.
    
    This function performs a join between the user_bookmarks table and the news_articles table
    to retrieve complete article information for all articles bookmarked by the specified user.
    The results are transformed into a more user-friendly format where each article includes its
    bookmark_id for reference.
    
    Args:
        user_id (str): The ID of the user whose bookmarks should be retrieved
    
    Returns:
        list: A list of dictionaries, each containing the full details of a bookmarked article
              with an additional 'bookmark_id' field
    
    Raises:
        Exception: If there's an error during the database operation
    """
    try:
        # Query user_bookmarks and join with news_articles to get full article details
        # This uses Supabase's foreign key relationships to perform the join
        result = supabase.table("user_bookmarks") \
            .select(
                "id,"
                "news_articles(id,title,summary,content,source,published_at,url,image)"
            ) \
            .eq("user_id", user_id) \
            .execute()
        
        # Transform the nested result structure to a more friendly format
        # by flattening the news_articles data and adding the bookmark_id
        bookmarks = []
        for item in result.data:
            article = item["news_articles"]
            article["bookmark_id"] = item["id"]  # Add bookmark ID to article for reference
            bookmarks.append(article)
            
        return bookmarks
    except Exception as e:
        print(f"Error fetching bookmarks: {str(e)}")
        # Re-raise the exception for proper error handling upstream
        raise e

def delete_bookmark(user_id, bookmark_id):
    """
    Deletes a bookmark from the user_bookmarks table.
    
    This function removes a bookmark relationship between a user and an article.
    It ensures that users can only delete their own bookmarks by checking both the
    bookmark_id and user_id in the query.
    
    Args:
        user_id (str): The ID of the user who owns the bookmark
        bookmark_id (str): The ID of the bookmark to delete
    
    Returns:
        bool: True if the bookmark was successfully deleted, False if no bookmark was found
              or if the deletion was unsuccessful
    
    Raises:
        Exception: If there's an error during the database operation
    """
    try:
        # Delete the bookmark, ensuring it belongs to the specified user
        # This double condition prevents users from deleting other users' bookmarks
        result = supabase.table("user_bookmarks") \
            .delete() \
            .eq("id", bookmark_id) \
            .eq("user_id", user_id) \
            .execute()
        
        # Return True if at least one record was deleted, False otherwise
        return len(result.data) > 0
    except Exception as e:
        print(f"Error deleting bookmark: {str(e)}")
        # Re-raise the exception for proper error handling upstream
        raise e