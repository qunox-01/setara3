import io

import pandas as pd
from fastapi import APIRouter, HTTPException, Query, Request, UploadFile, File, Form
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates

from app.dependencies import get_session_id
from app.services import coverage as coverage_service
from app.utils.legal import validate_legal_acceptance, log_consent, POLICY_VERSION

router = APIRouter()
templates = Jinja2Templates(directory="templates")


@router.get("/tools/coverage", response_class=HTMLResponse)
async def coverage_tool(request: Request):
    return templates.TemplateResponse("tools/coverage.html", {"request": request})


@router.post("/api/tools/coverage/analyze")
async def coverage_analyze(
    request: Request,
    file: UploadFile = File(...),
    label_col: str = Query(None),
    grid_size: int = Query(None),
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
            df = pd.read_csv(io.BytesIO(contents), encoding=encoding, sep=None, engine="python")
            break
        except Exception as exc:
            last_error = exc

    if df is None:
        raise HTTPException(status_code=422, detail=f"Could not parse CSV: {last_error}")

    if len(df) > 500_000:
        raise HTTPException(status_code=422, detail="File has more than 500,000 rows.")

    if len(df.columns) > 50:
        raise HTTPException(status_code=422, detail="File has more than 50 columns.")

    if len(df) < 50:
        raise HTTPException(status_code=422, detail="Dataset must have at least 50 rows for coverage analysis.")

    numeric_cols = df.select_dtypes(include=["number"]).columns.tolist()
    check_cols = [c for c in numeric_cols if c != label_col]
    if len(check_cols) < 3:
        raise HTTPException(
            status_code=422,
            detail=f"Need at least 3 numeric columns. Found {len(check_cols)} (excluding label)."
        )

    # Sample large datasets
    if len(df) > 100_000:
        df = df.sample(n=100_000, random_state=42)

    try:
        result = coverage_service.analyse(df, label_col=label_col or None, grid_size=grid_size or None)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except MemoryError:
        raise HTTPException(status_code=413, detail="Dataset too large to process in memory.")

    await log_consent(
        session_id=get_session_id(request),
        action="upload_coverage",
        source="tool_coverage",
        policy_version=policy_version,
    )

    return JSONResponse(content=result)
