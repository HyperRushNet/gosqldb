# Use official Python slim image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Copy project files
COPY . .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Expose port (Render sets $PORT automatically)
ENV PORT=10000

# Start Uvicorn with FastAPI
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "$PORT"]
