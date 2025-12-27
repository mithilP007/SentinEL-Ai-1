FROM python:3.10-slim

WORKDIR /app

# Install system dependencies (Pathway needs some libs)
RUN apt-get update && apt-get install -y \
    build-essential \
    libssl-dev \
    libffi-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Expose Dashboard and Vector Store ports
EXPOSE 8000
EXPOSE 8080

# Default command: Run the Dashboard (which launches the Agent loop)
CMD ["python", "-m", "uvicorn", "src.dashboard.app:app", "--host", "0.0.0.0", "--port", "8000"]
