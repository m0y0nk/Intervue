from contextlib import asynccontextmanager
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .api.dashboard import router as dashboard_router
from .api.interview import router as interview_router
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


@app.get("/health")
def health():
    return {
        "status": "ok",
        "gemini_model": settings.GEMINI_MODEL,
        "executor_url": settings.EXECUTOR_URL,
    }
