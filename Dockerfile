FROM python:3.12-slim

WORKDIR /app

RUN pip install --no-cache-dir uv

COPY pyproject.toml uv.lock README.md VISION.md ./
COPY wikifi ./wikifi

RUN uv sync --frozen --no-dev

ENTRYPOINT ["uv", "run", "wikifi"]
CMD ["--help"]
