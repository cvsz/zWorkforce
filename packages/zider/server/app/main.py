from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os

try:
    from app.config import settings
    from app.routes.api import router as api_router
except ImportError:
    from server.app.config import settings
    from server.app.routes.api import router as api_router

app = FastAPI(
    title=settings.app_name,
    version=settings.version,
    description="Full-Stack AI Sidebar, ChatPDF, Summarizer & Multi-Model Gateway"
)

# CORS config to allow browser extension and local web applications
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)

# Mount web workspace static assets if present
web_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "web")
if os.path.exists(web_dir):
    app.mount("/web", StaticFiles(directory=web_dir, html=True), name="web")

@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "service": "zider-bff",
        "version": settings.version
    }
