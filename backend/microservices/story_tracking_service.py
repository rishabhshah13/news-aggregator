#!/usr/bin/env python3
"""
story_tracking_service.py - Microservice for Story Tracking
Wraps the story clustering logic and provides API endpoints for tracking stories.
"""

from summarization.story_tracking.story_tracking import cluster_articles

def run_story_tracking(article_embeddings):
    labels = cluster_articles(article_embeddings)
    return labels

if __name__ == '__main__':
    # Example dummy embeddings:
    import numpy as np
    dummy_embeddings = [np.random.rand(10) for _ in range(10)]
    print("Story Tracking Service Output:")
    print(run_story_tracking(dummy_embeddings))
