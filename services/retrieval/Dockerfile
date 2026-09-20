FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir --default-timeout=200 -r requirements.txt

COPY main.py .
COPY index_store/ ./index_store/

EXPOSE 8002

CMD uvicorn main:app --host 0.0.0.0 --port ${PORT:-8002}