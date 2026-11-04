FROM mcr.microsoft.com/playwright/python:v1.47.0-jammy

WORKDIR /app
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt && pip install --no-cache-dir "playwright==1.47.0"
COPY backend/ /app/
RUN mkdir -p /app/data
COPY data/ /app/data/
ENV PYTHONPATH=/app
ENV ENVIRONMENT=production

CMD uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}
