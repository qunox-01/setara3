from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

router = APIRouter()
templates = Jinja2Templates(directory="templates")


@router.get("/tools/quality", response_class=HTMLResponse)
async def quality_tool(request: Request):
    return templates.TemplateResponse("tools/quality.html", {"request": request})


@router.get("/tools/scorecard", response_class=HTMLResponse)
async def scorecard_tool(request: Request):
    return templates.TemplateResponse("tools/scorecard.html", {"request": request})




