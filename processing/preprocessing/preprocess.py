#!/usr/bin/env python3
"""
preprocess.py - Data preprocessing module.
This script includes functions for cleaning raw data,
removing unwanted HTML, and normalizing text.
"""

def clean_data(raw_data):
    """
    Cleans raw text data.
    :param raw_data: The raw text to be cleaned.
    :return: Cleaned text.
    """
    # TODO: Implement more sophisticated cleaning if needed.
    return raw_data.strip()

if __name__ == '__main__':
    sample_data = "   <html>Sample News Content</html>   "
    cleaned = clean_data(sample_data)
    print("Cleaned Data:", cleaned)
