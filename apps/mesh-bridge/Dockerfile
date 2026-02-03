FROM python:3.11-slim

WORKDIR /app

# Install system dependencies for serial communication
RUN apt-get update && apt-get install -y \
    gcc \
    libffi-dev \
    iputils-ping \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create data directories
RUN mkdir -p /var/lib/aegis/queue /var/lib/aegis/nomadnet

# Expose API port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

# Run the service
CMD ["uvicorn", "service:app", "--host", "0.0.0.0", "--port", "8000"]
