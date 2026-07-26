FROM python:3.11-slim

WORKDIR /app

ENV LOG_LEVEL=INFO \
    LOG_FORMAT=json \
    ENVIRONMENT=production \
    SERVICE_NAME=log-service \
    LOG_DIR=/var/log/apira

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p /var/log/apira

EXPOSE 8300

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8300", "--no-access-log"]
