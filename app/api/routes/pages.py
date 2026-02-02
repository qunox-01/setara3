from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from app.core.config import TEMPLATES_DIR

router = APIRouter()
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


@router.get("/", response_class=HTMLResponse)
def home(request: Request):
    return templates.TemplateResponse(
        "home.html",
        {"request": request, "title": "Home"},
    )


@router.get("/som-mapping", response_class=HTMLResponse)
def som_mapping(request: Request):
    # You can pass data to the template later (e.g., mapping stats, job status)
    return templates.TemplateResponse(
        "som_mapping.html",
        {"request": request, "title": "SOM Mapping"},
    )
