.PHONY: setup up down logs migrate seed test lint frontend backend

setup:
	cp .env.example .env

up:
	docker compose up --build

down:
	docker compose down

logs:
	docker compose logs -f --tail=200

migrate:
	docker compose run --rm backend alembic upgrade head

seed:
	docker compose run --rm backend python -m scripts.seed

test:
	docker compose run --rm backend pytest -q
	docker compose run --rm frontend npm run test

lint:
	docker compose run --rm backend ruff check .
	docker compose run --rm frontend npm run lint

