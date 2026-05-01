from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from src.api.router import router
from src import config

is_prod = config.ENV == "production"
app = FastAPI(
    docs_url=None if is_prod else "/docs",
    redoc_url=None if is_prod else "/redoc",
    openapi_url=None if is_prod else "/openapi.json"
)
app.mount("/static", StaticFiles(directory="src/api/static"), name="static")
app.include_router(router)

