#!/usr/bin/env python3
"""
summarization_service.py - Microservice for Summarization
"""

def run_summarization(article_text):
    # For testing, return a simple summary
    return f"Summary: {article_text[:100]}..."

if __name__ == '__main__':
    sample_article = "Sample article content for summarization service testing."
    print("Summarization Service Output:")
    print(run_summarization(sample_article))
