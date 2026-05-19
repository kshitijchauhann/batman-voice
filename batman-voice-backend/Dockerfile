FROM python:3.11-slim

# Install system dependencies for audio libraries
RUN apt-get update && apt-get install -y \
    build-essential \
    libportaudio2 \
    portaudio19-dev \
    libsndfile1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY . .

# Expose the port uvicorn runs on
EXPOSE 8000

# Command to run the application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
