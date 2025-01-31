#!/usr/bin/env python3
"""
summary_cache.py - Caching for Summaries
This module caches generated summaries to avoid redundant processing.
It can be integrated with the caching layer (e.g., Redis) if needed.
"""

# For simplicity, using a dictionary as an in-memory cache.
cache = {}

def cache_summary(article_id, summary):
    """
    Stores the summary in the cache.
    :param article_id: Unique identifier for the article.
    :param summary: Generated summary text.
    """
    cache[article_id] = summary

def get_cached_summary(article_id):
    """
    Retrieves a cached summary if it exists.
    :param article_id: Unique identifier for the article.
    :return: Cached summary or None.
    """
    return cache.get(article_id)

if __name__ == '__main__':
    # Example usage:
    article_id = "article_123"
    summary_text = "This is a sample summary."
    cache_summary(article_id, summary_text)
    print("Cached Summary for article_123:")
    print(get_cached_summary(article_id))
