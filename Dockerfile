# Single-stage build: this service's default (mock) path has no heavy
# ML dependencies, so a multi-stage build buys little here. Real
# adapters (Whisper) install their own heavier deps but are never
# required for the default path -- see docker-compose.yml profiles.

FROM python:3.11-slim

WORKDIR /srv

# Install deps first so Docker layer caching skips this step when only
# application code changes.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app

EXPOSE 8000

CMD ["uvicorn", "app.api.main:app", "--host", "0.0.0.0", "--port", "8000"]