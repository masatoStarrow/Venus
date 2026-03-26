FROM python:3.13-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8002

RUN chmod +x entrypoint.sh

ENTRYPOINT ["bash", "./entrypoint.sh"]
