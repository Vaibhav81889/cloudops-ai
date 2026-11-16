FROM python:3.12-slim
LABEL org.opencontainers.image.source="https://github.com/Vaibhav81889/cloudops-ai"

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

WORKDIR /app

# Install dependencies first so Docker can cache this layer
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Then copy the application code and default config
COPY *.py config.toml ./

# Run as a non-root user; /data is where the database and logs live
RUN useradd --create-home --uid 10001 appuser \
    && mkdir -p /data && chown appuser /data
USER appuser
WORKDIR /data
VOLUME ["/data"]

EXPOSE 8000
CMD ["uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8000"]
