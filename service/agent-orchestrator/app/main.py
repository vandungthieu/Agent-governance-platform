from fastapi import FastAPI

from app.api import router
from app.core.config import settings
from app.db.init_db import init_db
from app.core.logging import configure_logging, request_logging_middleware


configure_logging()

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
)

app.middleware("http")(request_logging_middleware)
app.include_router(router, prefix=settings.API_V1_STR)


@app.on_event("startup")
def initialize_database() -> None:
    init_db()
