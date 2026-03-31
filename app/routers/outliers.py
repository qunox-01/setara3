import io
import json
import uuid

import pandas as pd
from fastapi import APIRouter, HTTPException, Query, Request, UploadFile, File, Form
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates

from fastapi.encoders import jsonable_encoder

from app.database import AsyncSessionLocal
from app.dependencies import get_session_id
from app.models import ToolResult
from app.services import outliers as outliers_service
from app.utils.analytics import track_event
from app.utils.legal import validate_legal_acceptance, log_consent, POLICY_VERSION
from app.utils.pdf import render_tool_pdf

router = APIRouter()
templates = Jinja2Templates(directory="templates")


@router.get("/tools/outliers", response_class=HTMLResponse)
async def outliers_tool(request: Request):
    return templates.TemplateResponse("tools/outliers.html", {"request": request})


@router.get("/tools/outliers/pdf/{result_id}")
async def outliers_pdf(result_id: str):
    return await render_tool_pdf("outliers", result_id)

_MAX_FILE_MB = 50
_MAX_ROWS = 100_000


@router.post("/api/tools/outliers/analyze")
async def outliers_analyze(
    request: Request,
    file: UploadFile = File(...),
    method: str = Query("ensemble", description="isolation_forest | dbscan | ensemble"),
    contamination: float = Query(0.05, ge=0.001, le=0.5, description="Expected outlier fraction (Isolation Forest)"),
    eps: float | None = Query(None, gt=0, description="DBSCAN neighbourhood radius (auto-estimated if omitted)"),
    min_samples: int | None = Query(None, ge=2, description="DBSCAN min cluster size (auto-estimated if omitted)"),
    label_col: str | None = Query(None, description="Column to treat as label (excluded from features)"),
    accept_legal: str = Form(default=""),
    policy_version: str = Form(default=POLICY_VERSION),
):
    validate_legal_acceptance(accept_legal, policy_version)
    # ── Validate file ────────────────────────────────────────────────────────
    filename = file.filename or ""
    if not filename.lower().endswith(".csv"):
        raise HTTPException(status_code=422, detail="Only CSV files are supported.")

    contents = await file.read()
    if len(contents) / (1024 * 1024) > _MAX_FILE_MB:
        raise HTTPException(status_code=422, detail=f"File exceeds {_MAX_FILE_MB}MB limit.")

    # ── Parse CSV ────────────────────────────────────────────────────────────
    df: pd.DataFrame | None = None
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

    if len(df) < 10:
        raise HTTPException(status_code=422, detail="Dataset must have at least 10 rows.")

    # ── Validate method ──────────────────────────────────────────────────────
    if method not in ("isolation_forest", "dbscan", "ensemble"):
        raise HTTPException(
            status_code=422,
            detail="method must be one of: isolation_forest, dbscan, ensemble.",
        )

    # ── Validate numeric columns ─────────────────────────────────────────────
    numeric_cols = df.select_dtypes(include=["number"]).columns.tolist()
    check_cols = [c for c in numeric_cols if c != label_col]
    if len(check_cols) < 2:
        raise HTTPException(
            status_code=422,
            detail=f"Need at least 2 numeric columns. Found {len(check_cols)} (excluding label).",
        )

    # ── Sample large datasets ────────────────────────────────────────────────
    if len(df) > _MAX_ROWS:
        df = df.sample(n=_MAX_ROWS, random_state=42)

    # ── Run analysis ─────────────────────────────────────────────────────────
    try:
        result = outliers_service.analyse(
            df,
            method=method,
            contamination=contamination,
            eps=eps,
            min_samples=min_samples,
            label_col=label_col or None,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except MemoryError:
        raise HTTPException(status_code=413, detail="Dataset too large to process in memory.")

    session_id = get_session_id(request)
    await log_consent(
        session_id=session_id,
        action="upload_outliers",
        source="tool_outliers",
        policy_version=policy_version,
    )
    result_id = str(uuid.uuid4())
    async with AsyncSessionLocal() as db:
        await track_event(
            db,
            event="file_upload",
            tool="outliers",
            session_id=session_id,
            metadata={"rows": len(df), "cols": len(df.columns), "method": method},
        )
        db.add(ToolResult(id=result_id, tool="outliers", result_json=json.dumps(jsonable_encoder(result))))
        await db.commit()

    return JSONResponse(content={**result, "result_id": result_id})
