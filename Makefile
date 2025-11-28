fmt:
	uv run ruff format

lint:
	uv run ruff check

mypy:
	uv run mypy .

run:
	uv run main.py