from fastapi import FastAPI, HTTPException
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.core.config import settings
from app.database.connection import engine

app = FastAPI(
    title=settings.app_name,
    version="1.0.0",
    debug=settings.debug,
)


@app.get("/", tags=["General"])
def root():
    return {
        "message": "Inventory & Warehouse Management API",
        "environment": settings.app_env,
        "status": "running",
    }


@app.get("/health", tags=["Health"])
def health_check():
    return {"status": "healthy"}


@app.get("/health/db", tags=["Health"])
def database_health_check():
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))

        return {
            "status": "healthy",
            "database": "connected",
        }

    except SQLAlchemyError:
        raise HTTPException(
            status_code=503,
            detail="Database connection failed",
        )
