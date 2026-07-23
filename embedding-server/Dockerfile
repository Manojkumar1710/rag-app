FROM python:3.11-slim

WORKDIR /app

# System deps needed by torch/pillow
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libgl1 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY download_models.py .
# Pre-download model weights into the image so startup is fast and offline-safe.
RUN python download_models.py

COPY main.py .

EXPOSE 8001

HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8001/health')" || exit 1

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8001"]
