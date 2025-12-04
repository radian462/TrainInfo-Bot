FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim
WORKDIR /bot

COPY pyproject.toml uv.lock* ./
RUN uv sync --no-dev --locked
COPY . /bot

EXPOSE 8080
CMD ["uv", "run", "--frozen", "--no-sync", "main.py"]