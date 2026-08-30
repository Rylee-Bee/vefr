FROM python:3.12-slim
WORKDIR /app
COPY pyproject.toml ./
COPY src ./src
RUN pip install --no-cache-dir .
COPY web ./web
COPY WORLD_BIBLE.md ./
CMD ["uvicorn", "old-name.main:app", "--host", "0.0.0.0", "--port", "8820"]
