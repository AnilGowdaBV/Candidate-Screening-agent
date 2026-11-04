FROM mcr.microsoft.com/playwright/python:v1.47.0-jammy

WORKDIR /app
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt && pip install --no-cache-dir "playwright==1.47.0"
COPY backend/ /app/
COPY data/screening_golang.db data/screening_python.db data/screening_java.db data/screening_javascript.db data/screening_typescript.db data/screening_frontend.db data/screening_qa_automation.db /app/data/
ENV PYTHONPATH=/app
ENV ENVIRONMENT=production

CMD uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}
