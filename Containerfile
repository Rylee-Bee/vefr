FROM python:3.12-slim
WORKDIR /app
ENV OLD-NAME-HOME=/app
ENV MUNR_VAULT=/app/data/vault.json
COPY pyproject.toml ./
COPY src ./src
RUN pip install --no-cache-dir .
COPY web ./web
COPY WORLD_BIBLE.md ./
COPY WHISPERS.md ./
COPY MAP.md ./
RUN mkdir -p /app/data
CMD ["uvicorn", "old-name.main:app", "--host", "0.0.0.0", "--port", "8820"]
