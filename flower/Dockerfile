FROM python:3.10-slim

WORKDIR /app

# Install system dependencies including curl for health checks
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
RUN pip install --upgrade pip && pip install celery[redis] flower

# Expose the port
EXPOSE 5555

# Set environment variables for Flower
ENV CELERY_BROKER_URL=redis://redis:6379/0
ENV FLOWER_PORT=5555

CMD ["python", "-m", "celery", "flower"]
