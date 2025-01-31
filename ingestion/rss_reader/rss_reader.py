#!/usr/bin/env python3
"""
rss_reader.py - RSS feed reader for the news aggregator.
This script uses the feedparser library to parse RSS feeds.
"""

import feedparser

def parse_feed(feed_url):
    """
    Parses an RSS feed from the provided URL.
    :param feed_url: URL of the RSS feed.
    :return: Parsed feed object.
    """
    return feedparser.parse(feed_url)

if __name__ == '__main__':
    # Example usage: Parse a sample RSS feed.
    sample_feed = "https://example.com/rss"
    feed = parse_feed(sample_feed)
    print("Feed Title:", feed.feed.get("title", "No Title"))
    for entry in feed.entries:
        print("Article Title:", entry.get("title", "No Title"))
