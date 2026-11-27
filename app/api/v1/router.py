from fastapi import APIRouter

from app.api.v1 import auth, categories, products, units, users, warehouses

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(warehouses.router)
api_router.include_router(units.router)
api_router.include_router(categories.router)
api_router.include_router(products.router)
