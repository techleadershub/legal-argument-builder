FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code and the local Qdrant database
# Note: This "bakes in" the database state at build time. 
# If you ingest new data, you must rebuild the image.
COPY . .

# Expose the port Streamlit runs on (App Runner defaults to 8080 usually)
EXPOSE 8080

# Environment variables
# STREAMLIT_SERVER_PORT tells Streamlit to listen on 8080
ENV STREAMLIT_SERVER_PORT=8080
ENV STREAMLIT_SERVER_ADDRESS=0.0.0.0

# Command to run the app
# Command to run the app
# check for ingestion on startup to ensure DB is ready in volatile environments
CMD ["sh", "-c", "echo 'Current working directory:' && pwd && ls -la && echo 'Starting ingestion...' && python ingest_case_law.py && echo 'Ingestion complete. Starting Streamlit...' && streamlit run app.py"]
