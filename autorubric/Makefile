up:
	docker-compose up -d --build

down:
	docker-compose down -v

logs:
	docker-compose logs -f

migrate:
	docker-compose exec api alembic upgrade head

test:
	cd backend && pytest

lint:
	cd backend && ruff check src tests && mypy src

fmt:
	cd backend && ruff format src tests

demo:
	python scripts/demo.py

models:
	bash scripts/download_model.sh
