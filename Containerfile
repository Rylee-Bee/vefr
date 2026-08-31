FROM python:3.12-slim
WORKDIR /app
ENV NORN_HOME=/app \
    NORN_VAULT=/app/data/vault.json \
    NORN_JOURNAL=/app/data/journal.json
COPY pyproject.toml ./
COPY src ./src
RUN pip install --no-cache-dir .
COPY web ./web
COPY worlds ./worlds
RUN mkdir -p /app/data
CMD ["uvicorn", "norn.main:app", "--host", "0.0.0.0", "--port", "8820"]
