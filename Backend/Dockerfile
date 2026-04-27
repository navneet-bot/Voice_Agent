FROM python:3.11-slim

WORKDIR /app

# Copy requirement files and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy all source code
COPY . .

# Expose the application port
EXPOSE 8000

# Run using gunicorn with uvicorn worker for production readiness
CMD ["gunicorn", "-k", "uvicorn.workers.UvicornWorker", "-w", "1", "--bind", "0.0.0.0:8000", "main:app"]
