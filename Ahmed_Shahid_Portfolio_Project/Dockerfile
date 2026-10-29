FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/backend \
    UPLOAD_DIR=/app/database/uploads

WORKDIR /app

COPY requirements.txt /app/requirements.txt
RUN python -m pip install --no-cache-dir -r /app/requirements.txt \
    && python -c "import itsdangerous; print('itsdangerous installed successfully')"

COPY backend /app/backend
COPY frontend /app/frontend
COPY database /app/database

RUN useradd --create-home --uid 10001 appuser \
    && mkdir -p /app/database/uploads \
    && chown -R appuser:appuser /app/database /app/backend /app/frontend

USER appuser
WORKDIR /app/backend

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
