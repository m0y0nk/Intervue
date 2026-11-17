import os
from contextlib import asynccontextmanager
import logging
from fastapi import FastAPI, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from .api.dashboard import router as dashboard_router
from .api.interview import router as interview_router
from .api.leetcode import router as leetcode_router
from .api.sessions import router as sessions_router
from .config import settings
from .database.session import init_db

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("intervue_backend")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Initializing database...")
    init_db()
    yield
    logger.info("Shutting down backend...")


app = FastAPI(
    title="Intervue Backend API",
    version="1.0.0",
    description="Unified interview engine for technical coding interviews",
    lifespan=lifespan,
)

# CORS configuration
origins = [origin.strip() for origin in settings.CORS_ORIGINS.split(",") if origin.strip()]
if not origins:
    origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(sessions_router)
app.include_router(interview_router)
app.include_router(dashboard_router)
app.include_router(leetcode_router)


@app.get("/health")
def health():
    return {
        "status": "ok",
        "gemini_model": settings.GEMINI_MODEL,
        "executor_url": settings.EXECUTOR_URL,
    }


# Serve built frontend static files if present (for single-container deployment)
static_candidates = [
    os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "frontend", "dist"),
    "/app/static",
    os.path.join(os.getcwd(), "frontend", "dist"),
    os.path.join(os.getcwd(), "static"),
]
static_dir = next((d for d in static_candidates if os.path.isdir(d)), None)

if static_dir and os.path.exists(os.path.join(static_dir, "index.html")):
    logger.info(f"Serving built frontend from {static_dir}")
    assets_dir = os.path.join(static_dir, "assets")
    if os.path.isdir(assets_dir):
        app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        if full_path.startswith("api/") or full_path == "api" or full_path == "health":
            return Response(status_code=404)
        file_path = os.path.join(static_dir, full_path)
        if full_path and os.path.isfile(file_path):
            return FileResponse(file_path)
        return FileResponse(os.path.join(static_dir, "index.html"))

