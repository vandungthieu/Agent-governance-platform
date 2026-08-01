from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.v1.router import api_router
from app.core.config import settings
from app.database.db import check_db_connection, init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    lifespan=lifespan,
)

app.include_router(api_router, prefix=settings.API_V1_STR)


@app.get("/health")
def health_check():
    return {"status": "healthy", "service": settings.PROJECT_NAME}


@app.get(f"{settings.API_V1_STR}/db/health")
def db_health_check():
    try:
        check_db_connection()
    except Exception as exc:
        return {
            "status": "unhealthy",
            "database": "postgresql",
            "error": str(exc),
        }
    return {"status": "healthy", "database": "postgresql"}
