FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY listener.py .
COPY config.py .

CMD ["python", "-u", "listener.py"]
