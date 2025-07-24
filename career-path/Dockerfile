FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Download NLTK data
RUN python -c "import nltk; import ssl; ssl._create_default_https_context = ssl._create_unverified_context; nltk.download('stopwords'); nltk.download('punkt')"

# Copy application code
COPY . .

# Create non-root user for running the app
RUN useradd --create-home --shell /bin/bash app && chown -R app:app /app
USER app

# Expose port
EXPOSE 8000

# Run the application
CMD ["uvicorn", "api_server:app", "--host", "0.0.0.0", "--port", "8000"]
