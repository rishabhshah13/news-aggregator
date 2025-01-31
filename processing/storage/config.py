"""
config.py - Storage configuration module.
This file contains configuration settings for databases and blob storage.
"""

# Database configuration (example: PostgreSQL)
DATABASE_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "user": "news_user",
    "password": "password",
    "database": "news_db"
}

# Blob storage configuration (example: AWS S3)
S3_CONFIG = {
    "bucket_name": "news-aggregator-bucket",
    "region": "us-east-1"
}
