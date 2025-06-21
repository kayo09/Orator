FROM python:3.10-slim

WORKDIR /app

RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

RUN pip install --upgrade pip && pip install celery[redis] flower

CMD ["python", "-m", "flower", "--broker=redis://redis:6379/0", "--port=5555"]
