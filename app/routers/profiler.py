import io

import pandas as pd
from fastapi import APIRouter, Request, UploadFile, File, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates

from app.services import profiler as profiler_service

router = APIRouter()
templates = Jinja2Templates(directory="templates")


@router.get("/tools/profiler", response_class=HTMLResponse)
async def profiler_tool(request: Request):
    return templates.TemplateResponse("tools/profiler.html", {"request": request})


@router.post("/api/tools/profiler/analyze")
async def profiler_analyze(file: UploadFile = File(...)):
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

    try:
        result = profiler_service.compute_profile(df)
    except MemoryError:
        raise HTTPException(status_code=413, detail="Dataset too large to process in memory.")

    return JSONResponse(content=result)
