
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
import os
from backend.config.settings import UPLOAD_DIR, CHROMA_PERSIST_DIR, CORS_ORIGINS
from backend.api.database.database import init_db
from backend.utils.logger import logger
from fastapi.middleware.cors import CORSMiddleware
from backend.utils.exceptions import MedicalAssistantError
from fastapi.responses import JSONResponse
from backend.api.routers import chat_router, imaging_router, voice_router, conversations_router
from fastapi.staticfiles import StaticFiles


@asynccontextmanager
async def lifespan(app: FastAPI):
    # --- Startup Logic ---
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    os.makedirs(CHROMA_PERSIST_DIR, exist_ok=True)
    os.makedirs("./data", exist_ok=True)
    init_db()
    logger.info("Database initialized. Multi-Agent Medical Assistant API is starting up.")

    yield  # The app runs while paused here

    # --- Shutdown Logic (Optional) ---
    logger.info("Multi-Agent Medical Assistant API is shutting down.")


app = FastAPI(
    title="Multi-Agent Medical Assistant API",
    description="Backend for a multi-agent clinical decision-support system "
                "(RAG, imaging, web search, voice, human-in-the-loop).",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS or ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(MedicalAssistantError)
def handle_app_error(request: Request, exc: MedicalAssistantError):
    logger.error(f"{type(exc).__name__}: {exc.message}")
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.message, "extra": exc.details})


app.include_router(chat_router.router)
app.include_router(imaging_router.router)
app.include_router(voice_router.router)
app.include_router(conversations_router.router)

# Serve uploaded images/figures so the frontend can display them inline
app.mount("/media", StaticFiles(directory=UPLOAD_DIR), name="media")


@app.get("/api/health")
def health_check():
    return {"status": "ok", "service": "multi-agent-medical-assistant"}