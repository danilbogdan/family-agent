.PHONY: install run lint type test ngrok

install:
	uv sync

run:
	uv run uvicorn app.main:app --reload

lint:
	uv run ruff check .

type:
	uv run mypy app tests

test:
	uv run pytest -q --cov=app --cov-report=term-missing

ngrok:
	ngrok http 8000
