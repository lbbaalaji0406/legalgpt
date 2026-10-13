FROM python:3.11-slim

WORKDIR /app

# System build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python requirements
COPY backend/requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend application and statutory datasets
COPY backend/ backend/
COPY data/ data/

WORKDIR /app/backend

ENV PORT=8000
ENV PYTHONIOENCODING=utf-8
ENV DISABLE_CROSS_ENCODER=1
ENV DISABLE_NLI=1
EXPOSE 8000

CMD ["sh", "-c", "uvicorn api_server:app --host 0.0.0.0 --port ${PORT:-8000}"]
