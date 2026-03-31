import io
import json
from datetime import datetime

from fastapi import HTTPException
from fastapi.responses import StreamingResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from weasyprint import HTML

from app.database import AsyncSessionLocal
from app.models import ToolResult

templates = Jinja2Templates(directory="templates")

_TOOL_TEMPLATES = {
    "quality": "pdf/quality_pdf.html",
    "scorecard": "pdf/scorecard_pdf.html",
    "profiler": "pdf/profiler_pdf.html",
    "coverage": "pdf/coverage_pdf.html",
    "outliers": "pdf/outliers_pdf.html",
    "drift": "pdf/drift_pdf.html",
}


async def render_tool_pdf(tool: str, result_id: str) -> StreamingResponse:
    async with AsyncSessionLocal() as session:
        row = await session.execute(
            select(ToolResult).where(
                ToolResult.id == result_id,
                ToolResult.tool == tool,
            )
        )
        tool_result = row.scalar_one_or_none()

    if not tool_result:
        raise HTTPException(status_code=404, detail="Result not found.")

    try:
        result = json.loads(tool_result.result_json)
    except (json.JSONDecodeError, TypeError):
        raise HTTPException(status_code=500, detail="Could not parse stored result.")

    template_name = _TOOL_TEMPLATES[tool]
    generated_at = tool_result.created_at.strftime("%B %d, %Y") if tool_result.created_at else ""

    html_string = templates.get_template(template_name).render(
        result=result,
        generated_at=generated_at,
    )

    pdf_bytes = HTML(string=html_string).write_pdf()
    filename = f"xariff-{tool}-{result_id[:8]}.pdf"

    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )
