import json

from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select

from app.database import AsyncSessionLocal
from app.models import Report

router = APIRouter()
templates = Jinja2Templates(directory="templates")


@router.get("/report/{report_id}", response_class=HTMLResponse)
async def view_report(request: Request, report_id: str):
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Report).where(Report.id == report_id)
        )
        report = result.scalar_one_or_none()

    if not report:
        raise HTTPException(status_code=404, detail="Report not found.")

    try:
        scorecard_data = json.loads(report.scorecard_json)
    except (json.JSONDecodeError, TypeError):
        scorecard_data = {}

    return templates.TemplateResponse(
        "report.html",
        {
            "request": request,
            "report": report,
            "scorecard": scorecard_data,
        },
    )
