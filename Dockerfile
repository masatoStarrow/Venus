FROM python:3.13-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8002

CMD ["gunicorn", "main:app", "--bind", "0.0.0.0:8002", "--workers", "4", "--worker-class", "uvicorn.workers.UvicornWorker"]
