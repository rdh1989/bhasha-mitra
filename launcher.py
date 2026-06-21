from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.api.router import router

app = FastAPI(
    title="Bhasha Mitra",
    version="1.0.0"
)

app.mount(
    "/static",
    StaticFiles(directory="app/ui/static"),
    name="static"
)

app.include_router(router)