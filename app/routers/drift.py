import io

import pandas as pd
from fastapi import APIRouter, HTTPException, Query, UploadFile, File
from fastapi.responses import JSONResponse

from app.services import drift as drift_service

router = APIRouter()

_MAX_FILE_MB = 50
_MAX_ROWS = 100_000


def _parse_csv(contents: bytes, label: str) -> pd.DataFrame:
    """Try multiple encodings; raise 422 on failure."""
    last_error: Exception | None = None
    for encoding in ("utf-8", "latin-1"):
        try:
            return pd.read_csv(io.BytesIO(contents), encoding=encoding, sep=None, engine="python")
        except Exception as exc:
            last_error = exc
    raise HTTPException(status_code=422, detail=f"Could not parse {label} CSV: {last_error}")


@router.post("/api/tools/drift/analyze")
async def drift_analyze(
    reference_file: UploadFile = File(..., description="Reference (baseline) CSV dataset"),
    current_file: UploadFile = File(..., description="Current (new/production) CSV dataset"),
    n_bins: int = Query(10, ge=5, le=50, description="Number of bins for numeric PSI calculation"),
):
    # ── Validate files ────────────────────────────────────────────────────────
    for f, label in ((reference_file, "reference"), (current_file, "current")):
        fname = f.filename or ""
        if not fname.lower().endswith(".csv"):
            raise HTTPException(status_code=422, detail=f"Only CSV files are supported ({label} file).")

    ref_contents = await reference_file.read()
    cur_contents = await current_file.read()

    for contents, label in ((ref_contents, "reference"), (cur_contents, "current")):
        if len(contents) / (1024 * 1024) > _MAX_FILE_MB:
            raise HTTPException(status_code=422, detail=f"{label.capitalize()} file exceeds {_MAX_FILE_MB}MB limit.")

    # ── Parse CSVs ────────────────────────────────────────────────────────────
    ref_df = _parse_csv(ref_contents, "reference")
    cur_df = _parse_csv(cur_contents, "current")

    if len(ref_df) < 10:
        raise HTTPException(status_code=422, detail="Reference dataset must have at least 10 rows.")
    if len(cur_df) < 10:
        raise HTTPException(status_code=422, detail="Current dataset must have at least 10 rows.")

    # ── Sample large datasets ─────────────────────────────────────────────────
    if len(ref_df) > _MAX_ROWS:
        ref_df = ref_df.sample(n=_MAX_ROWS, random_state=42)
    if len(cur_df) > _MAX_ROWS:
        cur_df = cur_df.sample(n=_MAX_ROWS, random_state=42)

    # ── Check common columns ──────────────────────────────────────────────────
    common = [c for c in ref_df.columns if c in cur_df.columns]
    if not common:
        raise HTTPException(
            status_code=422,
            detail="No common columns found between the two datasets. Ensure both files share column names.",
        )

    # ── Run analysis ──────────────────────────────────────────────────────────
    try:
        result = drift_service.analyse(ref_df, cur_df, n_bins=n_bins)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except MemoryError:
        raise HTTPException(status_code=413, detail="Datasets too large to process in memory.")

    return JSONResponse(content=result)
