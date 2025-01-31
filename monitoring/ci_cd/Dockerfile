# Dockerfile - Container image for the News Aggregator backend services
FROM python:3.9-slim

# Set working directory
WORKDIR /app

# Copy requirements file (if available) and install dependencies
# COPY requirements.txt .
# RUN pip install --no-cache-dir -r requirements.txt

# Copy the entire project (for demonstration; adjust as needed)
COPY . .

# Expose port 5000 for the API gateway (example)
EXPOSE 5000

# Command to run the API gateway; modify as needed for production
CMD ["python", "news-aggregator/backend/api_gateway/api_gateway.py"]
