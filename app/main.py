from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.api.v1 import api_router
from app.core.config import settings
from app.database.connection import engine

app = FastAPI(
    title=settings.app_name,
    version="1.0.0",
    debug=settings.debug,
)

# Local HTML UI may run on any localhost port (Live Server, http.server, etc.)
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"https?://(localhost|127\.0\.0\.1)(:\d+)?",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)


def _clean_validation_message(message: str) -> str:
    prefixes = ("Value error, ", "Assertion failed, ")
    for prefix in prefixes:
        if message.startswith(prefix):
            return message[len(prefix) :]
    return message


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    _request: Request,
    exc: RequestValidationError,
) -> JSONResponse:
    """Return clear field messages instead of raw Pydantic dumps."""
    errors: list[dict[str, str]] = []
    for err in exc.errors():
        loc = err.get("loc", ())
        field = ".".join(str(part) for part in loc if part not in ("body", "query", "path"))
        message = _clean_validation_message(str(err.get("msg", "Invalid value")))
        errors.append(
            {
                "field": field or "request",
                "message": message,
            }
        )

    if len(errors) == 1:
        detail = errors[0]["message"]
    else:
        detail = "Request validation failed. Please check the highlighted fields."

    return JSONResponse(
        status_code=422,
        content={"detail": detail, "errors": errors},
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
            detail="Database connection failed. Please try again later.",
        )
