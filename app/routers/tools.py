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



@router.get("/tools/outliers", response_class=HTMLResponse)
async def outliers_tool(request: Request):
    return templates.TemplateResponse(
        "tools/coming_soon.html",
        {"request": request, "tool_name": "Outlier Detector", "coming_soon": True},
    )
