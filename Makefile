# Vigil developer commands. Nothing is installed on the host outside backend/.venv and frontend/node_modules.
BACKEND_PY := backend/.venv/bin/python

.PHONY: setup up down test test-db test-backend test-frontend typecheck gates api-types check-api-types migrate demo-data erd ci

setup: ## Create the backend venv and install frontend deps (local only)
	cd backend && python3 -m venv .venv && .venv/bin/pip install -q -e '.[dev]'
	cd frontend && npm ci

up: ## Start Postgres, backend and frontend
	docker compose up --build

down:
	docker compose down

test: test-backend test-frontend

test-db: ## Start the throwaway test database (in memory, port 55432)
	docker compose --profile test up -d --wait db-test

test-backend: test-db
	cd backend && .venv/bin/pytest -q
	cd eval && ../$(BACKEND_PY) -m pytest -q -p no:cacheprovider

test-frontend:
	cd frontend && npm test

typecheck:
	cd backend && .venv/bin/mypy
	cd frontend && npm run typecheck

gates: ## Run the quality gates (test environment only; needs `make test-db`; fails the build on any gate failure)
	VIGIL_ENV=test $(BACKEND_PY) eval/gates.py

migrate: ## Provision database roles and migrate the dev database to head
	cd backend && .venv/bin/python -m app.db.provision

demo-data: ## Load the synthetic demo Practice into the dev database (dev only)
	cd backend && .venv/bin/python -m app.db.demo_data

erd: ## Regenerate the clickable data-model diagram (docs/data-model/index.html)
	cd backend && .venv/bin/python -m app.db.erd

api-types: ## Regenerate frontend types from the backend's OpenAPI schema
	cd backend && .venv/bin/python -m app.openapi_export > openapi.json
	cd frontend && npm run gen:api

check-api-types: api-types ## Fail if the committed frontend types are out of date
	git diff --exit-code -- frontend/generated/api.ts

ci: test typecheck gates check-api-types ## Everything a build must pass
