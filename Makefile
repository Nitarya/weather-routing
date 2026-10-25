.PHONY: install dev-backend dev-frontend build test lint collectstatic

install:
	python3 -m venv .venv
	.venv/bin/pip install --upgrade pip
	.venv/bin/pip install -r backend/requirements.txt
	cd frontend && npm ci

dev-backend:
	cd backend && ../.venv/bin/python manage.py runserver 0.0.0.0:8000

dev-frontend:
	cd frontend && npm run dev

build:
	cd frontend && npm run build

test:
	cd backend && ../.venv/bin/python manage.py test routing

lint:
	.venv/bin/ruff check backend

collectstatic:
	cd backend && ../.venv/bin/python manage.py collectstatic --noinput
