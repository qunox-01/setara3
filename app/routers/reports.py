import io
import json

from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from weasyprint import HTML

from app.database import AsyncSessionLocal
from app.models import Report

router = APIRouter()
templates = Jinja2Templates(directory="templates")


def _get_report_context(report: Report) -> dict:
    try:
        scorecard_data = json.loads(report.scorecard_json)
    except (json.JSONDecodeError, TypeError):
        scorecard_data = {}
    return {"report": report, "scorecard": scorecard_data}


@router.get("/report/{report_id}", response_class=HTMLResponse)
async def view_report(request: Request, report_id: str):
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Report).where(Report.id == report_id)
        )
        report = result.scalar_one_or_none()

    if not report:
        raise HTTPException(status_code=404, detail="Report not found.")

    return templates.TemplateResponse(
        "report.html",
        {"request": request, **_get_report_context(report)},
    )


@router.get("/report/{report_id}/pdf")
async def download_report_pdf(report_id: str):
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Report).where(Report.id == report_id)
        )
        report = result.scalar_one_or_none()

    if not report:
        raise HTTPException(status_code=404, detail="Report not found.")

    html_string = templates.get_template("report_pdf.html").render(
        **_get_report_context(report)
    )

    pdf_bytes = HTML(string=html_string).write_pdf()

    filename = f"xariff-report-{report_id[:8]}.pdf"
    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )
