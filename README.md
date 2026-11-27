# Inventory & Warehouse Management API

FastAPI backend for multi-warehouse inventory: users/roles, warehouses, products, stock movements, alerts, and reports (Module 1 auth & warehouses implemented first).

## Stack

- Python 3.13, FastAPI, Pydantic
- PostgreSQL, SQLAlchemy 2, Alembic
- JWT access/refresh tokens, Argon2 password hashing

## Current status (Modules 1 + 2)

- Auth: register (STAFF), login, refresh, logout, change/forgot/reset password, `/auth/me`
- Users: Admin create (role + warehouse), list, get, update, activate/deactivate
- Warehouses: create/list/get/update/status, assign/unassign, list users, managers in detail
- Products: categories CRUD/status, fixed units (`GET /units`), products CRUD/status, images (URL-only), by-sku lookup
- RBAC seed: Admin / Manager / Staff permissions (catalog write = Admin)

Live docs: https://inventory-warehouse-api.onrender.com/docs

## Project structure

```text
app/
  api/v1/          # HTTP routes (auth, users, warehouses, units, categories, products)
  core/            # config, security (JWT/passwords), deps (permissions)
  database/        # engine + session
  db/seed_data.py  # RBAC catalog
  models/          # SQLAlchemy tables
  schemas/         # request/response validation
  services/        # business logic
  scripts/seed.py  # seed RBAC into DB
alembic/           # migrations
```

## Setup

```powershell
py -3.13 -m venv venv
.\venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

Copy `.env.example` to `.env` and set `DATABASE_URL` + `SECRET_KEY`.

Token defaults (also set these on Render Dashboard for the live service):

- `ACCESS_TOKEN_EXPIRE_MINUTES=1440` (24 hours)
- `REFRESH_TOKEN_EXPIRE_DAYS=180` (6 months)

This project currently uses the **shared Render Postgres** from local `.env` as well, so migrate/seed updates the same DB seniors test. Be careful with deletes.

```powershell
alembic upgrade head
python -m app.scripts.seed
uvicorn app.main:app --reload
```

- Swagger: http://127.0.0.1:8000/docs  
- Health: http://127.0.0.1:8000/health  

Admin bootstrap (if needed): create via your createsuperuser flow or existing `admin@test.com` account.

## Auth notes for clients

- Access token: use on every protected API (`Authorization: Bearer …`).
- Refresh token: optional; call `POST /api/v1/auth/refresh` to get a new access token after 24h without logging in again.
- After Admin **assigns** a user to a warehouse or changes role, call `GET /api/v1/auth/me` (or login/refresh again). The server always loads warehouse from the database; the JWT snapshot can be outdated for UI display.

## Password rules

Min 8 characters, with uppercase, lowercase, number, and special character. Change-password requires the new password to differ from the current one.
