FROM python:3.11-slim

# PortAudio is required to compile PyAudio
RUN apt-get update && apt-get install -y --no-install-recommends \
    portaudio19-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY gateway/ gateway/
COPY screen/ screen/

RUN mkdir -p logs

EXPOSE 8000

CMD ["python", "gateway/main.py"]
