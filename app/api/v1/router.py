from fastapi import APIRouter

from app.api.v1.endpoints import auth, catalog, chat, observability, orders, refunds, system


api_router = APIRouter()
api_router.include_router(system.router)
api_router.include_router(auth.router)
api_router.include_router(chat.router)
api_router.include_router(catalog.router)
api_router.include_router(orders.router)
api_router.include_router(refunds.router)
api_router.include_router(observability.router)
