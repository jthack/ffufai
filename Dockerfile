# Use Python 3.11 slim image as base
FROM python:3.11-slim

# Install required system dependencies
RUN apt-get update && apt-get install -y \
    wget \
    golang \
    git \
    && rm -rf /var/lib/apt/lists/*

# Install ffuf
RUN go install github.com/ffuf/ffuf/v2@latest

# Set working directory
WORKDIR /app

# Copy requirements first to leverage Docker cache
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application
COPY ffufai.py .

# Add Go binaries to PATH
ENV PATH="/root/go/bin:${PATH}"

# Set the entrypoint
ENTRYPOINT ["python", "ffufai.py"]