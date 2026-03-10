import io
import json
import uuid

import pandas as pd
from fastapi import APIRouter, Request, UploadFile, File, Form, HTTPException
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.templating import Jinja2Templates

from app.dependencies import validate_csv, get_session_id
from app.services import quality as quality_service
from app.services import scorecard as scorecard_service
from app.database import AsyncSessionLocal
from app.models import Report

router = APIRouter()
templates = Jinja2Templates(directory="templates")


@router.post("/tools/quality/analyse", response_class=HTMLResponse)
async def quality_analyse(request: Request, file: UploadFile = File(...)):
    df = await validate_csv(file)
    result = quality_service.analyse(df)
    return templates.TemplateResponse(
        "tools/partials/quality_results.html",
        {"request": request, **result},
    )


@router.post("/tools/quality/download")
async def quality_download(file: UploadFile = File(...)):
    df = await validate_csv(file)
    result = quality_service.analyse(df)
    flagged = result.get("flagged_rows", [])

    if not flagged:
        raise HTTPException(status_code=404, detail="No flagged rows found.")

    flagged_df = pd.DataFrame(flagged)
    output = io.StringIO()
    flagged_df.to_csv(output, index=False)
    output.seek(0)

    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=flagged_rows.csv"},
    )


@router.post("/tools/scorecard/analyse", response_class=HTMLResponse)
async def scorecard_analyse(
    request: Request,
    file: UploadFile = File(...),
    label_column: str = Form(default=""),
    stage: str = Form(default="exploration"),
):
    df = await validate_csv(file)
    result = scorecard_service.analyse(
        df,
        label_column=label_column or None,
        stage=stage,
    )
    return templates.TemplateResponse(
        "tools/partials/scorecard_results.html",
        {"request": request, **result},
    )


@router.post("/tools/scorecard/report", response_class=HTMLResponse)
async def scorecard_report(
    request: Request,
    file: UploadFile = File(...),
    label_column: str = Form(default=""),
    stage: str = Form(default="exploration"),
    email: str = Form(default=""),
):
    df = await validate_csv(file)
    result = scorecard_service.analyse(
        df,
        label_column=label_column or None,
        stage=stage,
    )

    report_id = str(uuid.uuid4())
    async with AsyncSessionLocal() as session:
        report = Report(
            id=report_id,
            email=email,
            scorecard_json=json.dumps(result),
        )
        session.add(report)
        await session.commit()

    report_url = f"/report/{report_id}"
    return HTMLResponse(
        content=f"""
        <div class="p-4 bg-green-50 border border-green-200 rounded-lg text-center">
            <p class="text-green-800 font-semibold mb-2">Your report is ready!</p>
            <a href="{report_url}" target="_blank"
               class="inline-block px-4 py-2 bg-green-600 text-white rounded hover:bg-green-700">
                View Report
            </a>
            <p class="text-sm text-green-600 mt-2">Share this link: <code>{report_url}</code></p>
        </div>
        """
    )
