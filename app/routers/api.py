import io
import json

import numpy as np
import pandas as pd
from fastapi import APIRouter, Request, Form, BackgroundTasks
from fastapi.responses import HTMLResponse, Response, StreamingResponse

from app.database import AsyncSessionLocal
from app.dependencies import get_session_id
from app.models import Email, Feedback, AnalyticsEvent

router = APIRouter()


@router.post("/api/email-capture", response_class=HTMLResponse)
async def email_capture(
    request: Request,
    email: str = Form(...),
    source: str = Form(default=""),
    tool: str = Form(default=""),
    utm_source: str = Form(default=""),
):
    async with AsyncSessionLocal() as session:
        record = Email(email=email, source=source, tool=tool, utm_source=utm_source)
        session.add(record)
        await session.commit()

    return HTMLResponse(
        content="""
        <div class="p-4 bg-green-50 border border-green-200 rounded-lg text-center">
            <p class="text-green-800 font-semibold">Thank you! We'll be in touch.</p>
        </div>
        """
    )


@router.post("/api/feedback", response_class=HTMLResponse)
async def feedback(
    request: Request,
    tool: str = Form(default=""),
    useful: str = Form(default=""),
    comment: str = Form(default=""),
):
    session_id = get_session_id(request)
    async with AsyncSessionLocal() as session:
        record = Feedback(tool=tool, useful=useful, comment=comment, session_id=session_id)
        session.add(record)
        await session.commit()

    return HTMLResponse(
        content="""
        <div class="p-3 bg-blue-50 border border-blue-200 rounded-lg text-center">
            <p class="text-blue-800">Thanks for your feedback!</p>
        </div>
        """
    )


@router.post("/api/track")
async def track_event(
    request: Request,
    background_tasks: BackgroundTasks,
    event: str = Form(default=""),
    tool: str = Form(default=""),
    metadata: str = Form(default="{}"),
    utm_source: str = Form(default=""),
    utm_campaign: str = Form(default=""),
):
    session_id = get_session_id(request)

    async def save_event():
        async with AsyncSessionLocal() as session:
            record = AnalyticsEvent(
                event=event,
                tool=tool,
                session_id=session_id,
                metadata_json=metadata,
                utm_source=utm_source,
                utm_campaign=utm_campaign,
            )
            session.add(record)
            await session.commit()

    background_tasks.add_task(save_event)
    return {"ok": True}


@router.get("/sample-data/{tool}")
async def sample_data(tool: str):
    rng = np.random.default_rng(42)

    if tool == "quality":
        n = 200
        df = pd.DataFrame(
            {
                "id": range(1, n + 1),
                "name": [f"sample_{i}" if i % 15 != 0 else None for i in range(n)],
                "age": [
                    int(rng.integers(18, 80))
                    if i % 20 != 0
                    else (999 if i % 40 == 0 else None)
                    for i in range(n)
                ],
                "score": rng.uniform(0, 100, n).round(2),
                "category": rng.choice(["A", "B", "C", None], n, p=[0.4, 0.3, 0.2, 0.1]).tolist(),
                "email": [
                    f"user{i}@example.com" if i % 25 != 0 else "not-an-email"
                    for i in range(n)
                ],
                "revenue": rng.exponential(1000, n).round(2),
            }
        )
        # Insert a few duplicate rows
        df = pd.concat([df, df.iloc[:5]], ignore_index=True)

    elif tool == "scorecard":
        n = 300
        df = pd.DataFrame(
            {
                "feature_1": rng.normal(0, 1, n).round(4),
                "feature_2": rng.uniform(-10, 10, n).round(4),
                "feature_3": rng.choice(["low", "medium", "high", None], n, p=[0.3, 0.4, 0.25, 0.05]).tolist(),
                "feature_4": rng.integers(1, 100, n).tolist(),
                "label": rng.choice([0, 1], n, p=[0.7, 0.3]).tolist(),
                "text": [f"sample text {i}" if i % 30 != 0 else None for i in range(n)],
            }
        )
    else:
        n = 100
        df = pd.DataFrame(
            {
                "col_a": rng.normal(0, 1, n).round(3),
                "col_b": rng.integers(0, 100, n).tolist(),
                "col_c": rng.choice(["x", "y", "z"], n).tolist(),
            }
        )

    output = io.StringIO()
    df.to_csv(output, index=False)
    output.seek(0)

    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=sample_{tool}.csv"},
    )


@router.get("/sitemap.xml")
async def sitemap():
    base = "https://xariff.com"
    urls = [
        "/",
        "/tools",
        "/tools/quality",
        "/tools/scorecard",
        "/blog",
        "/about",
    ]
    url_tags = "\n".join(
        f"  <url><loc>{base}{u}</loc></url>" for u in urls
    )
    xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
{url_tags}
</urlset>"""
    return Response(content=xml, media_type="application/xml")


@router.get("/robots.txt")
async def robots():
    content = """User-agent: *
Allow: /

Sitemap: https://xariff.com/sitemap.xml
"""
    return Response(content=content, media_type="text/plain")
