from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.middleware import register_middlewares
from app.api.openapi.tags import tags_metadata
from app.api.routes import router as api_router
from frontend.pages.routes import router as frontend_router
from infrastructure.configuration import configuration
from fastapi.staticfiles import StaticFiles
from infrastructure.initialization.ai_framework import ai_framework



@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application startup and shutdown events.
    """
    print("Starting Application")

    configuration.initialize()

    # Initialize AI Framework
    ai_framework.initialize()

    print("Application Ready")

    yield

    print("Shutdown Started")

    ai_framework.shutdown()

    print("Shutdown Completed")

app = FastAPI(
    title="Bhasha Mitra API",
    description="""
Offline AI-powered multilingual video translation platform.

Features:
- Video Upload
- Speech Recognition (ASR)
- Language Translation
- Subtitle Generation
- Text-to-Speech
- Job Management
- Provider Discovery
- Model Management
""",
    version="1.0.0",
    lifespan=lifespan,

    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",

    openapi_tags=tags_metadata,

    contact={
        "name": "Bhasha Mitra Team",
        "email": "support@bhashamitra.local",
    },

    license_info={
        "name": "Proprietary",
    },
)


# Register middleware
register_middlewares(app)

# Register API routes
app.include_router(api_router)

# Mount static files
app.mount(
    "/static",
    StaticFiles(directory="frontend/static"),
    name="static"
)

# Register frontend routes
app.include_router(frontend_router)


@app.get("/", tags=["Root"])
async def root():
    """
    Root endpoint.
    """

    return {
        "application": "Bhasha Mitra",
        "version": app.version,
        "status": "Running",
    }