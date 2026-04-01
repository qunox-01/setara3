import io
import json
import re
import uuid

import pandas as pd
from fastapi import APIRouter, Request, UploadFile, File, Form, HTTPException, BackgroundTasks
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.templating import Jinja2Templates

from fastapi.encoders import jsonable_encoder

from app.dependencies import validate_csv, get_session_id
from app.services.email import send_scorecard_report_ready
from app.services import quality as quality_service
from app.services import scorecard as scorecard_service
from app.database import AsyncSessionLocal
from app.models import Report, ToolResult
from app.utils.analytics import track_event
from app.utils.legal import validate_legal_acceptance, log_consent, POLICY_VERSION
from app.utils.pdf import render_tool_pdf

router = APIRouter()
templates = Jinja2Templates(directory="templates")
EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


@router.post("/tools/quality/analyse", response_class=HTMLResponse)
async def quality_analyse(
    request: Request,
    file: UploadFile = File(...),
    accept_legal: str = Form(default=""),
    policy_version: str = Form(default=POLICY_VERSION),
):
    validate_legal_acceptance(accept_legal, policy_version)
    df = await validate_csv(file)
    result = quality_service.analyse(df)
    session_id = get_session_id(request)
    await log_consent(
        session_id=session_id,
        action="upload_quality",
        source="tool_quality",
        policy_version=policy_version,
    )
    result_id = str(uuid.uuid4())
    async with AsyncSessionLocal() as db:
        await track_event(
            db,
            event="file_upload",
            tool="quality",
            session_id=session_id,
            metadata={"rows": len(df), "cols": len(df.columns)},
        )
        db.add(ToolResult(id=result_id, tool="quality", result_json=json.dumps(jsonable_encoder(result))))
        await db.commit()
    return templates.TemplateResponse(
        "tools/partials/quality_results.html",
        {"request": request, "result_id": result_id, **result},
    )


@router.get("/tools/quality/pdf/{result_id}")
async def quality_pdf(result_id: str):
    response = await render_tool_pdf("quality", result_id)
    response.headers["X-Robots-Tag"] = "noindex, nofollow, noarchive"
    return response


@router.get("/tools/scorecard/pdf/{result_id}")
async def scorecard_pdf(result_id: str):
    response = await render_tool_pdf("scorecard", result_id)
    response.headers["X-Robots-Tag"] = "noindex, nofollow, noarchive"
    return response


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
    accept_legal: str = Form(default=""),
    policy_version: str = Form(default=POLICY_VERSION),
):
    validate_legal_acceptance(accept_legal, policy_version)
    df = await validate_csv(file)
    result = scorecard_service.analyse(
        df,
        label_column=label_column or None,
        stage=stage,
    )
    session_id = get_session_id(request)
    await log_consent(
        session_id=session_id,
        action="upload_scorecard",
        source="tool_scorecard",
        policy_version=policy_version,
    )
    result_id = str(uuid.uuid4())
    async with AsyncSessionLocal() as db:
        await track_event(
            db,
            event="file_upload",
            tool="scorecard",
            session_id=session_id,
            metadata={"rows": len(df), "cols": len(df.columns), "label_column": label_column, "stage": stage},
        )
        db.add(ToolResult(id=result_id, tool="scorecard", result_json=json.dumps(jsonable_encoder(result))))
        await db.commit()
    return templates.TemplateResponse(
        "tools/partials/scorecard_results.html",
        {"request": request, "result_id": result_id, **result},
    )


@router.post("/tools/scorecard/report", response_class=HTMLResponse)
async def scorecard_report(
    request: Request,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    label_column: str = Form(default=""),
    stage: str = Form(default="exploration"),
    email: str = Form(default=""),
    accept_legal: str = Form(default=""),
    policy_version: str = Form(default=POLICY_VERSION),
):
    validate_legal_acceptance(accept_legal, policy_version)
    cleaned_email = email.strip().lower()
    if cleaned_email and not EMAIL_PATTERN.match(cleaned_email):
        raise HTTPException(status_code=422, detail="Please provide a valid email address.")
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
            email=cleaned_email,
            scorecard_json=json.dumps(result),
        )
        session.add(report)
        await session.commit()

    session_id = get_session_id(request)
    await log_consent(
        session_id=session_id,
        action="report_generate",
        source="tool_scorecard",
        policy_version=policy_version,
    )
    async with AsyncSessionLocal() as db:
        await track_event(
            db,
            event="report_generate",
            tool="scorecard",
            session_id=session_id,
            metadata={"rows": len(df), "cols": len(df.columns), "label_column": label_column, "stage": stage},
        )

    if cleaned_email:
        background_tasks.add_task(
            send_scorecard_report_ready,
            email=cleaned_email,
            report_id=report_id,
        )

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
