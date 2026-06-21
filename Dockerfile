# Use a lightweight official Python runtime
FROM python:3.11-slim

# Install system dependencies needed for PDF processing, OpenVINO/CV2, and FAISS compilation
RUN apt-get update && apt-get install -y \
    build-essential \
    libgl1 \
    libglib2.0-0 \
    poppler-utils \
    && rm -rf /var/lib/apt/lists/*

# Set the working directory inside the container
WORKDIR /app

# Copy and install Python packages
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of your application code
COPY . .

# Expose Streamlit's default network port
EXPOSE 8501

# Run the application
CMD ["streamlit", "run", "ui/app.py"]