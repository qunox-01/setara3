import io
import json
import uuid

import pandas as pd
from fastapi import APIRouter, Request, UploadFile, File, HTTPException, Form
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates

from fastapi.encoders import jsonable_encoder

from app.database import AsyncSessionLocal
from app.dependencies import get_session_id
from app.models import ToolResult
from app.services import profiler as profiler_service
from app.utils.analytics import track_event
from app.utils.legal import validate_legal_acceptance, log_consent, POLICY_VERSION
from app.utils.pdf import render_tool_pdf

router = APIRouter()
templates = Jinja2Templates(directory="templates")


@router.get("/tools/profiler", response_class=HTMLResponse)
async def profiler_tool(request: Request):
    return templates.TemplateResponse("tools/profiler.html", {"request": request})


@router.get("/tools/profiler/pdf/{result_id}")
async def profiler_pdf(result_id: str):
    response = await render_tool_pdf("profiler", result_id)
    response.headers["X-Robots-Tag"] = "noindex, nofollow, noarchive"
    return response


@router.post("/api/tools/profiler/analyze")
async def profiler_analyze(
    request: Request,
    file: UploadFile = File(...),
    accept_legal: str = Form(default=""),
    policy_version: str = Form(default=POLICY_VERSION),
):
    validate_legal_acceptance(accept_legal, policy_version)
    filename = file.filename or ""
    if not filename.lower().endswith(".csv"):
        raise HTTPException(status_code=422, detail="Only CSV files are supported.")

    contents = await file.read()
    if len(contents) / (1024 * 1024) > 50:
        raise HTTPException(status_code=422, detail="File exceeds 50MB limit.")

    df = None
    last_error: Exception | None = None
    for encoding in ("utf-8", "latin-1"):
        try:
            df = pd.read_csv(
                io.BytesIO(contents),
                encoding=encoding,
                sep=None,
                engine="python",
            )
            break
        except Exception as exc:
            last_error = exc

    if df is None:
        raise HTTPException(status_code=422, detail=f"Could not parse CSV: {last_error}")

    if len(df) > 500_000:
        raise HTTPException(status_code=422, detail="File has more than 500,000 rows.")

    if len(df.columns) > 50:
        raise HTTPException(
            status_code=422,
            detail=f"Dataset has {len(df.columns)} features. Maximum allowed is 50."
        )

    try:
        result = profiler_service.compute_profile(df)
    except MemoryError:
        raise HTTPException(status_code=413, detail="Dataset too large to process in memory.")

    session_id = get_session_id(request)
    await log_consent(
        session_id=session_id,
        action="upload_profiler",
        source="tool_profiler",
        policy_version=policy_version,
    )
    result_id = str(uuid.uuid4())
    async with AsyncSessionLocal() as db:
        await track_event(
            db,
            event="file_upload",
            tool="profiler",
            session_id=session_id,
            metadata={"rows": len(df), "cols": len(df.columns)},
        )
        db.add(ToolResult(id=result_id, tool="profiler", result_json=json.dumps(jsonable_encoder(result))))
        await db.commit()

    return JSONResponse(content={**result, "result_id": result_id})
