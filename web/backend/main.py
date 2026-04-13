"""JobPilot Web UI Backend -- FastAPI application."""

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .config import CORS_ORIGINS
from .routes import applications, search, resume, gmail, settings, chat

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

FRONTEND_DIST = Path(__file__).parent.parent / "frontend" / "dist"


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("JobPilot Web UI starting...")
    yield
    logger.info("JobPilot Web UI shutting down...")


app = FastAPI(
    title="JobPilot",
    description="Job Application Management Agent -- Web UI API",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(applications.router)
app.include_router(search.router)
app.include_router(resume.router)
app.include_router(gmail.router)
app.include_router(settings.router)
app.include_router(chat.router)

# Serve built frontend in production
if FRONTEND_DIST.exists():
    app.mount("/", StaticFiles(directory=str(FRONTEND_DIST), html=True), name="frontend")


@app.get("/api/health")
async def health():
    return {"status": "ok", "service": "jobpilot-web"}
