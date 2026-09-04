install:
	uv sync --locked

pre-commit.install:
	uv run pre-commit install

compose.dev:
	docker compose -f compose.deps.dev.yml -f compose.dev.yml up --build -d

compose.dev.up:
	docker compose -f compose.deps.dev.yml -f compose.dev.yml up -d

compose.dev.down:
	docker compose -f compose.deps.dev.yml -f compose.dev.yml down

makemigrations:
	uv run python src/manage.py makemigrations

migrate:
	uv run python src/manage.py migrate

createsuperuser:
	uv run python src/manage.py createsuperuser

run:
	uv run uvicorn django_project.asgi:application --reload --app-dir src

lint:
	uv run ruff format src/
	uv run ruff check src/ --fix
	uv run mypy src/

test:
	uv run pytest src/
