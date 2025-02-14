# Dockerfile - Container image for the News Aggregator backend services
FROM python:3.9-slim

# Set working directory
WORKDIR /app

# Install curl for health checks
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

# Copy requirements file and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the entire project
COPY . .

# Expose port 5000 for the API gateway
EXPOSE 5000

# Add health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:5000/health || exit 1

# Set resource limits
ENV PYTHONUNBUFFERED=1
ENV PYTHONIOENCODING=UTF-8

# Command to run the API gateway
CMD ["python", "news-aggregator/backend/api_gateway/api_gateway.py"]
