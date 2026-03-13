from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.templating import Jinja2Templates

router = APIRouter()
templates = Jinja2Templates(directory="templates")


@router.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse("home.html", {"request": request})


@router.get("/about", response_class=HTMLResponse)
async def about(request: Request):
    return templates.TemplateResponse("about.html", {"request": request})


@router.get("/tools", response_class=HTMLResponse)
async def tools_index(request: Request):
    return templates.TemplateResponse("tools/index.html", {"request": request})


@router.get("/robots.txt", include_in_schema=False)
async def robots_txt():
    return FileResponse("robots.txt", media_type="text/plain")
