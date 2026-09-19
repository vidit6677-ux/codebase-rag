# Start from a lightweight Python base image
FROM python:3.11-slim

# Set working directory inside the container
WORKDIR /app

# Copy dependency list first (Docker caches this layer if requirements.txt doesn't change)
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the actual application code
COPY backend/ ./backend/
COPY frontend/ ./frontend/

# The container needs the pre-built index and the cloned repo data too,
# since build_index.py needs to have already been run.
# We'll copy those in as well:
COPY backend/index_store/ ./backend/index_store/

# Expose the port FastAPI/uvicorn will run on
EXPOSE 8000

# Set working directory to backend so relative paths (../frontend) resolve correctly
WORKDIR /app/backend

# Run the server
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]