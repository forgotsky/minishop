SHELL := /bin/bash
.DEFAULT_GOAL := help

.PHONY: help setup-backend run-backend setup-uni run-uni dev-up dev-down test-backend clean

help:
	@echo "Available targets:"
	@echo "  make setup-backend   - create venv and install backend deps"
	@echo "  make run-backend     - run FastAPI on :8000"
	@echo "  make setup-uni       - install uni-app dependencies"
	@echo "  make run-uni         - run uni-app H5 dev server"
	@echo "  make dev-up          - start docker compose stack"
	@echo "  make dev-down        - stop docker compose stack"
	@echo "  make test-backend    - run backend syntax check + API smoke test"
	@echo "  make clean           - remove caches/logs"

setup-backend:
	cd backend && python -m venv .venv && . .venv/bin/activate && pip install -r requirements.txt

run-backend:
	cd backend && . .venv/bin/activate && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

setup-uni:
	cd uni-app && npm install

run-uni:
	cd uni-app && npm run dev:h5

dev-up:
	docker compose up --build

dev-down:
	docker compose down

test-backend:
	cd backend && . .venv/bin/activate && \
	python -m py_compile app/main.py app/db.py app/models.py app/repository.py app/skills_seed.py app/skills_data.py && \
	(uvicorn app.main:app --host 127.0.0.1 --port 8000 >/tmp/uvicorn-skill.log 2>&1 & echo $$! >/tmp/uvicorn-skill.pid) && \
	sleep 2 && \
	curl -sf http://127.0.0.1:8000/api/health >/dev/null && \
	curl -sf http://127.0.0.1:8000/api/skills >/dev/null && \
	curl -sf -X POST http://127.0.0.1:8000/api/template -H 'Content-Type: application/json' -d '{"subject":"英语"}' >/dev/null && \
	curl -sf -X POST http://127.0.0.1:8000/api/plan -H 'Content-Type: application/json' -d '{"hour_tasks":[{"slot":"第1小时","wordsText":"book / pen","sentence":"This is a book.","usage":"造句"}],"daily_minutes":30,"days_per_week":3}' >/dev/null && \
	kill -9 $$(cat /tmp/uvicorn-skill.pid) >/dev/null 2>&1 || true
	@echo "Backend smoke test passed."

clean:
	rm -rf backend/__pycache__ backend/app/__pycache__ uni-app/dist frontend/dist
	find . -name '*.pyc' -delete
