# Makefile for News Aggregator Project

.PHONY: run test docker-build docker-clean

# Run the API Gateway (example)
run:
	python backend/api_gateway/api_gateway.py 8000

# Run tests using pytest
test:
	pytest --maxfail=1 --disable-warnings -q

# Build Docker image
docker-build:
	docker build -t news-aggregator:latest .

# Clean Docker image (example)
docker-clean:
	docker rmi news-aggregator:latest
