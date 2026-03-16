import io

import pandas as pd
from fastapi import APIRouter, HTTPException, Query, Request, UploadFile, File, Form
from fastapi.responses import JSONResponse

from app.dependencies import get_session_id
from app.services import outliers as outliers_service
from app.utils.legal import validate_legal_acceptance, log_consent, POLICY_VERSION

router = APIRouter()

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

    await log_consent(
        session_id=get_session_id(request),
        action="upload_outliers",
        source="tool_outliers",
        policy_version=policy_version,
    )

    return JSONResponse(content=result)
