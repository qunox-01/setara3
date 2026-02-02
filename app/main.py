from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.core.config import STATIC_DIR
from app.api.router import router as api_router

app = FastAPI(title="FastAPI Pages (Tailwind)")

# Static files (optional for later: images, custom css, js)
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# Routes
app.include_router(api_router)
