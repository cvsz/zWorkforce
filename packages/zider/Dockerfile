FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY server/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY server/ /app/server/
COPY extension/ /app/extension/
COPY web/ /app/web/

EXPOSE 8085

CMD ["uvicorn", "server.app.main:app", "--host", "0.0.0.0", "--port", "8085"]
