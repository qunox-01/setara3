import io

import pandas as pd
from fastapi import Request, UploadFile, HTTPException

from app.config import settings


def get_session_id(request: Request) -> str:
    return request.cookies.get("session_id", "anonymous")


async def validate_csv(file: UploadFile) -> pd.DataFrame:
    filename = file.filename or ""
    if not (filename.endswith(".csv") or filename.endswith(".tsv")):
        raise HTTPException(
            status_code=422,
            detail="Only CSV and TSV files are supported.",
        )

    contents = await file.read()

    size_mb = len(contents) / (1024 * 1024)
    if size_mb > settings.max_file_size_mb:
        raise HTTPException(
            status_code=422,
            detail=f"File exceeds {settings.max_file_size_mb}MB limit.",
        )

    try:
        sep = "\t" if filename.endswith(".tsv") else ","
        df = pd.read_csv(io.BytesIO(contents), sep=sep, low_memory=False)
    except Exception as exc:
        raise HTTPException(
            status_code=422,
            detail=f"Could not parse file: {exc}",
        )

    if len(df) > settings.max_rows:
        raise HTTPException(
            status_code=422,
            detail=f"File has more than {settings.max_rows:,} rows.",
        )

    if len(df.columns) > settings.max_cols:
        raise HTTPException(
            status_code=422,
            detail=f"File has more than {settings.max_cols} columns.",
        )

    return df
