#!/usr/bin/env python3
"""
cache.py - Caching module.
This script sets up Redis caching to store frequently accessed data.
"""

import redis

# Configure Redis client
redis_client = redis.Redis(host='localhost', port=6379, db=0)

def set_cache(key, value, expire=3600):
    """
    Stores a key-value pair in Redis cache with expiration.
    :param key: Cache key.
    :param value: Value to cache.
    :param expire: Expiration time in seconds (default: 1 hour).
    """
    redis_client.setex(key, expire, value)

def get_cache(key):
    """
    Retrieves a value from Redis cache by key.
    :param key: Cache key.
    :return: Cached value or None.
    """
    return redis_client.get(key)

if __name__ == '__main__':
    set_cache('sample_key', 'sample_value')
    cached = get_cache('sample_key')
    print("Cached Value:", cached.decode('utf-8') if cached else "None")
