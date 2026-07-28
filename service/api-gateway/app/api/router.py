from fastapi import APIRouter
from app.api.v1.routes import proxy

api_router = APIRouter()
api_router.include_router(proxy.router, prefix="/v1", tags=["Proxy Gateway"])
