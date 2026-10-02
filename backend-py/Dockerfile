FROM python:3.11-slim

WORKDIR /app

# System deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential zlib1g-dev \
    && rm -rf /var/lib/apt/lists/*

# Install uv for fast dependency install
RUN pip install --no-cache-dir uv

COPY requirements.txt .
RUN uv pip install --system --no-cache -r requirements.txt

ENV PYTHONPATH=/app/src

# Playwright browser for JS-page fallback
RUN playwright install chromium --with-deps

COPY . .

# BGE models are downloaded at first use; pre-cache if desired:
# RUN python -c "from FlagEmbedding import BGEM3FlagModel; BGEM3FlagModel('BAAI/bge-m3')"

RUN mkdir -p /app/data/lancedb /app/data/raw

EXPOSE 8080

CMD ["python", "main.py"]
