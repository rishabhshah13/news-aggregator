#!/usr/bin/env python3
"""
story_tracking_service.py - Microservice for Story Tracking

This service provides functionality for tracking news stories by keyword and finding related articles.
It integrates with Supabase for data persistence and manages user story tracking preferences.

Key Features:
- Story tracking by keywords
- Related article discovery
- User story management
- Automatic story updates

The service uses clustering algorithms to group similar articles and maintains
relationships between tracked stories and their associated articles.

Database Tables Used:
- tracked_stories: Stores user story tracking preferences
- tracked_story_articles: Links stories to their related articles
- news_articles: Stores article content and metadata

Environment Variables Required:
- VITE_SUPABASE_URL: Supabase project URL
- SUPABASE_SERVICE_ROLE_KEY: Service role key for admin access
"""

#TODO: Implement proper background processing: Use a task queue like Celery to handle article fetching in the background

import os
import datetime
from supabase import create_client, Client
from dotenv import load_dotenv
# from summarization.story_tracking.story_tracking import cluster_articles
from backend.microservices.news_fetcher import fetch_news

# Service initialization logging
print("[DEBUG] [story_tracking_service] [main] Story tracking service starting...")

# Load environment variables from .env file
load_dotenv()
print("[DEBUG] [story_tracking_service] [main] Environment variables loaded")

# Initialize Supabase client with service role key for admin access to bypass RLS
# RLS (Row Level Security) policies are bypassed when using the service role key
SUPABASE_URL = os.getenv("VITE_SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

print(f"[DEBUG] [story_tracking_service] [main] Supabase URL: {SUPABASE_URL}")
print(f"[DEBUG] [story_tracking_service] [main] Supabase Key: {SUPABASE_SERVICE_KEY[:5]}..." if SUPABASE_SERVICE_KEY else "[DEBUG] [story_tracking_service] [main] Supabase Key: None")

# Create Supabase client for database operations
supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

print("[DEBUG] [story_tracking_service] [main] Supabase client initialized")

def run_story_tracking(article_embeddings):
    """
    Runs the story tracking algorithm on a set of article embeddings to identify story clusters.
    
    This function uses clustering algorithms to group similar articles together based on their
    vector embeddings, helping to identify distinct news stories or topics.
    
    Args:
        article_embeddings: List of vector embeddings for articles. Each embedding should be
                          a numerical vector representing the article's content.
                          
    Returns:
        list: A list of cluster labels indicating which story cluster each article belongs to.
              Empty list is returned if article_embeddings is None or empty.
    """
    print(f"[DEBUG] [story_tracking_service] [run_story_tracking] Running story tracking with {len(article_embeddings) if article_embeddings else 0} embeddings")
    labels = cluster_articles(article_embeddings)
    print(f"[DEBUG] [story_tracking_service] [run_story_tracking] Clustering complete, found {len(labels) if labels else 0} labels")
    return labels

def create_tracked_story(user_id, keyword, source_article_id=None):
    """
    Creates a new tracked story for a user based on a keyword.
    
    Args:
        user_id: The ID of the user tracking the story
        keyword: The keyword/topic to track
        source_article_id: Optional ID of the source article that initiated tracking
        
    Returns:
        The created tracked story record
    """
    
    print(f"[DEBUG] [story_tracking_service] [create_tracked_story] Creating tracked story for user {user_id}, keyword: '{keyword}', source_article: {source_article_id}")
    try:
        # Check if the user is already tracking this keyword
        print(f"[DEBUG] [story_tracking_service] [create_tracked_story] Checking if user already tracks keyword '{keyword}'")
        existing = supabase.table("tracked_stories") \
            .select("*") \
            .eq("user_id", user_id) \
            .eq("keyword", keyword) \
            .execute()
            
        if existing.data and len(existing.data) > 0:
            # User is already tracking this keyword
            print(f"[DEBUG] [story_tracking_service] [create_tracked_story] User already tracking this keyword, found {len(existing.data)} existing entries")
            return existing.data[0]
        
        # Create a new tracked story
        print(f"[DEBUG] [story_tracking_service] [create_tracked_story] Creating new tracked story record")
        current_time = datetime.datetime.utcnow().isoformat()
        result = supabase.table("tracked_stories").insert({
            "user_id": user_id,
            "keyword": keyword,
            "created_at": current_time,
            "last_updated": current_time
        }).execute()
        
        if not result.data:
            print(f"[DEBUG] [story_tracking_service] [create_tracked_story] Failed to create tracked story: {result}")
            return None
            
        tracked_story = result.data[0] if result.data else None
        print(f"[DEBUG] [story_tracking_service] [create_tracked_story] Tracked story created with ID: {tracked_story['id'] if tracked_story else None}")
        
        # If a source article was provided, link it to the tracked story
        if tracked_story and source_article_id:
            print(f"[DEBUG] [story_tracking_service] [create_tracked_story] Linking source article {source_article_id} to tracked story")
            supabase.table("tracked_story_articles").insert({
                "tracked_story_id": tracked_story["id"],
                "news_id": source_article_id,
                "added_at": datetime.datetime.utcnow().isoformat()
            }).execute()
        
        # Log that we're skipping synchronous article fetching
        print(f"[DEBUG] [story_tracking_service] [create_tracked_story] Skipping synchronous article fetching to avoid resource contention")
        find_related_articles(tracked_story["id"], keyword)
        
        return tracked_story
    
    except Exception as e:
        print(f"[DEBUG] [story_tracking_service] [create_tracked_story] Error creating tracked story: {str(e)}")
        raise e

def get_tracked_stories(user_id):
    """
    Gets all tracked stories for a user.
    
    Args:
        user_id: The ID of the user
        
    Returns:
        List of tracked stories with their related articles
    """
    print(f"[DEBUG] [story_tracking_service] [get_tracked_stories] Getting tracked stories for user {user_id}")
    try:
        # Get all tracked stories for the user
        result = supabase.table("tracked_stories") \
            .select("*") \
            .eq("user_id", user_id) \
            .order("created_at", desc=True) \
            .execute()
        
        tracked_stories = result.data if result.data else []
        print(f"[DEBUG] [story_tracking_service] [get_tracked_stories] Found {len(tracked_stories)} tracked stories")
        
        # For each tracked story, get its related articles
        for story in tracked_stories:
            print(f"[DEBUG] [story_tracking_service] [get_tracked_stories] Getting articles for story {story['id']}")
            story["articles"] = get_story_articles(story["id"])
            print(f"[DEBUG] [story_tracking_service] [get_tracked_stories] Found {len(story['articles'])} articles for story {story['id']}")
        
        return tracked_stories
    
    except Exception as e:
        print(f"[DEBUG] [story_tracking_service] [get_tracked_stories] Error getting tracked stories: {str(e)}")
        raise e

def get_story_details(story_id):
    """
    Gets details for a specific tracked story including related articles.
    
    Args:
        story_id: The ID of the tracked story
        
    Returns:
        The tracked story with its related articles
    """
    print(f"[DEBUG] [story_tracking_service] [get_story_details] Getting story details for story ID {story_id}")
    try:
        # Get the tracked story
        result = supabase.table("tracked_stories") \
            .select("*") \
            .eq("id", story_id) \
            .execute()
        
        if not result.data or len(result.data) == 0:
            print(f"[DEBUG] [story_tracking_service] [get_story_details] No story found with ID {story_id}")
            return None
        
        story = result.data[0]
        print(f"[DEBUG] [story_tracking_service] [get_story_details] Found story: {story['keyword']}")
        
        # Get related articles
        print(f"[DEBUG] [story_tracking_service] [get_story_details] Getting related articles")
        story["articles"] = get_story_articles(story_id)
        print(f"[DEBUG] [story_tracking_service] [get_story_details] Found {len(story['articles'])} related articles")
        
        return story
    
    except Exception as e:
        print(f"[DEBUG] [story_tracking_service] [get_story_details] Error getting story details: {str(e)}")
        raise e

def delete_tracked_story(user_id, story_id):
    """
    Deletes a tracked story for a user.
    
    Args:
        user_id: The ID of the user
        story_id: The ID of the tracked story to delete
        
    Returns:
        True if successful, False otherwise
    """
    print(f"[DEBUG] [story_tracking_service] [delete_tracked_story] Deleting tracked story {story_id} for user {user_id}")
    try:
        # Delete the tracked story (related articles will be deleted via CASCADE)
        result = supabase.table("tracked_stories") \
            .delete() \
            .eq("id", story_id) \
            .eq("user_id", user_id) \
            .execute()
        
        success = len(result.data) > 0
        print(f"[DEBUG] [story_tracking_service] [delete_tracked_story] Delete operation {'successful' if success else 'failed'}")
        return success
    
    except Exception as e:
        print(f"[DEBUG] [story_tracking_service] [delete_tracked_story] Error deleting tracked story: {str(e)}")
        raise e

def get_story_articles(story_id):
    """
    Gets all articles related to a tracked story.
    
    Args:
        story_id: The ID of the tracked story
        
    Returns:
        List of articles related to the tracked story
    """
    print(f"[DEBUG] [story_tracking_service] [get_story_articles] Getting articles for story {story_id}")
    try:
        # Get all article IDs related to the tracked story
        result = supabase.table("tracked_story_articles") \
            .select("news_id, added_at") \
            .eq("tracked_story_id", story_id) \
            .order("added_at", desc=True) \
            .execute()
        
        article_refs = result.data if result.data else []
        print(f"[DEBUG] [story_tracking_service] [get_story_articles] Found {len(article_refs)} article references")
        
        if not article_refs:
            return []
        
        # Get the full article details for each article ID
        articles = []
        for ref in article_refs:
            print(f"[DEBUG] [story_tracking_service] [get_story_articles] Getting details for article {ref['news_id']}")
            article_result = supabase.table("news_articles") \
                .select("*") \
                .eq("id", ref["news_id"]) \
                .execute()
            
            if article_result.data and len(article_result.data) > 0:
                article = article_result.data[0]
                # Add the added_at timestamp from the join table
                article["added_at"] = ref["added_at"]
                articles.append(article)
                print(f"[DEBUG] [story_tracking_service] [get_story_articles] Added article: {article.get('title', 'No title')}")
            else:
                print(f"[DEBUG] [story_tracking_service] [get_story_articles] No data found for article {ref['news_id']}")
        
        return articles
    
    except Exception as e:
        print(f"[DEBUG] [story_tracking_service] [get_story_articles] Error getting story articles: {str(e)}")
        raise e

def find_related_articles(story_id, keyword):
    """
    Finds and adds articles related to a tracked story based on its keyword.
    
    Args:
        story_id: The ID of the tracked story
        keyword: The keyword to search for
        
    Returns:
        Number of new articles added
    """
    print(f"[DEBUG] [story_tracking_service] [find_related_articles] Finding related articles for story {story_id}, keyword: '{keyword}'")
    try:
        # Get the tracked story to check when it was last updated
        story_result = supabase.table("tracked_stories") \
            .select("*") \
            .eq("id", story_id) \
            .execute()
        
        if not story_result.data or len(story_result.data) == 0:
            print(f"[DEBUG] [story_tracking_service] [find_related_articles] No story found with ID {story_id}")
            return 0
        
        story = story_result.data[0]
        print(f"[DEBUG] [story_tracking_service] [find_related_articles] Found story: {story['keyword']}")
        
        # Fetch articles related to the keyword
        print(f"[DEBUG] [story_tracking_service] [find_related_articles] Fetching articles for keyword '{keyword}'")
        articles = fetch_news(keyword)
        
        if not articles:
            print(f"[DEBUG] [story_tracking_service] [find_related_articles] No articles found for keyword '{keyword}'")
            return 0
        
        print(f"[DEBUG] [story_tracking_service] [find_related_articles] Found {len(articles)} articles for keyword '{keyword}'")
        
        # Get existing article IDs for this story to avoid duplicates
        print(f"[DEBUG] [story_tracking_service] [find_related_articles] Getting existing article IDs for story {story_id}")
        existing_result = supabase.table("tracked_story_articles") \
            .select("news_id") \
            .eq("tracked_story_id", story_id) \
            .execute()
        
        existing_ids = [item["news_id"] for item in existing_result.data] if existing_result.data else []
        print(f"[DEBUG] [story_tracking_service] [find_related_articles] Found {len(existing_ids)} existing article IDs")
        
        # Process and add new articles
        new_articles_count = 0
        for article in articles:
            # First, store the article in the news_articles table
            print(f"[DEBUG] [story_tracking_service] [find_related_articles] Storing article: {article.get('title', 'No title')}")
            from backend.microservices.news_storage import store_article_in_supabase
            article_id = store_article_in_supabase(article)
            print(f"[DEBUG] [story_tracking_service] [find_related_articles] Article stored with ID: {article_id}")
            
            # If this article is not already linked to the story, add it
            if article_id not in existing_ids:
                print(f"[DEBUG] [story_tracking_service] [find_related_articles] Linking new article {article_id} to story {story_id}")
                supabase.table("tracked_story_articles").insert({
                    "tracked_story_id": story_id,
                    "news_id": article_id,
                    "added_at": datetime.datetime.utcnow().isoformat()
                }).execute()
                new_articles_count += 1
            else:
                print(f"[DEBUG] [story_tracking_service] [find_related_articles] Article {article_id} already linked to story")
        
        print(f"[DEBUG] [story_tracking_service] [find_related_articles] Added {new_articles_count} new articles to story {story_id}")
        
        # Update the last_updated timestamp of the tracked story
        if new_articles_count > 0:
            print(f"[DEBUG] [story_tracking_service] [find_related_articles] Updating last_updated timestamp for story {story_id}")
            supabase.table("tracked_stories") \
                .update({"last_updated": datetime.datetime.utcnow().isoformat()}) \
                .eq("id", story_id) \
                .execute()
        
        return new_articles_count
    
    except Exception as e:
        print(f"[DEBUG] [story_tracking_service] [find_related_articles] Error finding related articles: {str(e)}")
        raise e

def update_all_tracked_stories():
    """
    Background job to update all tracked stories with new related articles.
    
    This function is designed to be run as a scheduled task to keep all tracked stories
    up-to-date with the latest news articles. It iterates through all tracked stories in the
    database and calls find_related_articles() for each one to fetch and link new articles.
    
    Returns:
        dict: A dictionary containing statistics about the update operation:
              - stories_updated: Number of stories that received new articles
              - new_articles: Total number of new articles added across all stories
    """
    print(f"[DEBUG] [story_tracking_service] [update_all_tracked_stories] Starting update of all tracked stories")
    try:
        # Get all tracked stories
        result = supabase.table("tracked_stories") \
            .select("id, keyword") \
            .execute()
        
        tracked_stories = result.data if result.data else []
        print(f"[DEBUG] [story_tracking_service] [update_all_tracked_stories] Found {len(tracked_stories)} tracked stories to update")
        
        if not tracked_stories:
            return {"stories_updated": 0, "new_articles": 0}
        
        # Update each tracked story
        stories_updated = 0
        total_new_articles = 0
        
        for story in tracked_stories:
            print(f"[DEBUG] [story_tracking_service] [update_all_tracked_stories] Updating story {story['id']}, keyword: '{story['keyword']}'")
            new_articles = find_related_articles(story["id"], story["keyword"])
            if new_articles > 0:
                stories_updated += 1
                total_new_articles += new_articles
                print(f"[DEBUG] [story_tracking_service] [update_all_tracked_stories] Added {new_articles} new articles to story {story['id']}")
            else:
                print(f"[DEBUG] [story_tracking_service] [update_all_tracked_stories] No new articles found for story {story['id']}")
        
        print(f"[DEBUG] [story_tracking_service] [update_all_tracked_stories] Update complete. Updated {stories_updated} stories with {total_new_articles} new articles")
        return {
            "stories_updated": stories_updated,
            "new_articles": total_new_articles
        }
    
    except Exception as e:
        print(f"[DEBUG] [story_tracking_service] [update_all_tracked_stories] Error updating tracked stories: {str(e)}")
        raise e

if __name__ == '__main__':
    # Example usage - this code runs when the script is executed directly
    print("[DEBUG] [story_tracking_service] [main] Running story_tracking_service.py as main")
    result = update_all_tracked_stories()
    print(f"[DEBUG] [story_tracking_service] [main] Updated {result['stories_updated']} stories with {result['new_articles']} new articles")
    print("[DEBUG] [story_tracking_service] [main] Execution completed")
