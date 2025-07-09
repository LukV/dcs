.PHONY: install format lint typecheck test serve clean commit bump pre-commit

install:
	uv sync --frozen

format:
	uv run ruff format src

lint:
	uv run ruff check src

typecheck:
	uv run mypy src

pre-commit:
	uv run pre-commit run --all-files

serve:
	uv run uvicorn dcs.api:app --reload --reload-dir src

clean:
	rm -rf .venv .pytest_cache __pycache__ dist build .ruff_cache

commit:
	uv run cz commit

bump:
	uv run cz bump
