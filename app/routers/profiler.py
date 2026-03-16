import io

import pandas as pd
from fastapi import APIRouter, Request, UploadFile, File, HTTPException, Form
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates

from app.dependencies import get_session_id
from app.services import profiler as profiler_service
from app.utils.legal import validate_legal_acceptance, log_consent, POLICY_VERSION

router = APIRouter()
templates = Jinja2Templates(directory="templates")


@router.get("/tools/profiler", response_class=HTMLResponse)
async def profiler_tool(request: Request):
    return templates.TemplateResponse("tools/profiler.html", {"request": request})


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

    await log_consent(
        session_id=get_session_id(request),
        action="upload_profiler",
        source="tool_profiler",
        policy_version=policy_version,
    )

    return JSONResponse(content=result)
