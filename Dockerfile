FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim
WORKDIR /bot

COPY pyproject.toml uv.lock* ./
RUN uv sync --frozen --no-dev
COPY . /bot

EXPOSE 8080
CMD ["uv", "run", "main.py", "--frozen", "--no-sync"]