import logging
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.database import create_tables
from app.routers import pages, tools, analysis, articles, reports, api, profiler, coverage

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        await create_tables()
    except Exception:
        # Keep serving even if DB bootstrap fails; Fly health checks need a live listener.
        logger.exception("Database initialization failed during startup")
    yield


app = FastAPI(title="xariff", lifespan=lifespan)

app.mount("/static", StaticFiles(directory="static"), name="static")

templates = Jinja2Templates(directory="templates")

app.include_router(pages.router)
app.include_router(profiler.router)
app.include_router(coverage.router)
app.include_router(tools.router)
app.include_router(analysis.router)
app.include_router(articles.router)
app.include_router(reports.router)
app.include_router(api.router)


@app.middleware("http")
async def session_middleware(request: Request, call_next):
    response = await call_next(request)
    if not request.cookies.get("session_id"):
        response.set_cookie(
            "session_id",
            str(uuid.uuid4()),
            max_age=60 * 60 * 24 * 365,
            httponly=True,
            samesite="lax",
        )
    return response
