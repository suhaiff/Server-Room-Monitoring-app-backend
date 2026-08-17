.PHONY: up down test seed simulate
up:
	docker compose up --build
down:
	docker compose down
test:
	docker compose run --rm backend pytest -q
seed:
	docker compose run --rm backend python -m app.seed
simulate:
	docker compose up --build simulator-api simulator-ui
