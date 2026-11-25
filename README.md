
# Inventory & Warehouse Management API

Backend application for managing products, warehouses, inventory, stock operations, and transaction history.

## Technology Stack

- **Language:** Python 3.13
- **Framework:** FastAPI
- **Database:** PostgreSQL
- **ORM:** SQLAlchemy
- **Database Migrations:** Alembic
- **Validation:** Pydantic
- **Authentication:** JWT
- **Password Hashing:** Argon2

## Project Features

- User and role management
- Permission-based access control
- Warehouse management
- Product and category management
- Inventory tracking
- Stock IN and OUT operations
- Stock adjustments
- Warehouse-to-warehouse transfers
- Inventory transaction history
- Low-stock alerts
- Reports and analytics

## Project Structure

```text
Final Project/
├── app/
│   ├── __init__.py
│   └── main.py
├── venv/
├── .env.example
├── .gitignore
├── README.md
└── requirements.txt
```

## Local Development Setup

### 1. Prerequisites

- Python 3.13
- PostgreSQL
- Git

### 2. Clone the Repository

```bash
git clone <repository-url>
cd <project-folder>
```

### 3. Create Virtual Environment

```powershell
py -3.13 -m venv venv
```

### 4. Activate Virtual Environment

```powershell
.\venv\Scripts\Activate.ps1
```

### 5. Install Dependencies

```powershell
python -m pip install -r requirements.txt
```

### 6. Configure Environment Variables

Create a `.env` file using `.env.example` as a template.

Update the database connection string and secret key.

### 7. Run the Application

```powershell
uvicorn app.main:app --reload
```

## API Documentation

Once the application is running:

- **Swagger UI:** http://127.0.0.1:8000/docs
- **ReDoc:** http://127.0.0.1:8000/redoc
- **Health Check:** http://127.0.0.1:8000/health

## Development Status

Initial project setup completed. Database configuration and API module development are pending.
