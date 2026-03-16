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
    elif tool == "coverage":
        # Synthetic seismic dataset with deliberate feature-space gaps
        # (high-magnitude + low-distance events are underrepresented)
        n_common = 220
        n_rare   = 30
        df = pd.DataFrame(
            {
                "magnitude": np.concatenate([
                    rng.uniform(3.0, 5.5, n_common),   # common: low-medium magnitude
                    rng.uniform(6.8, 8.5, n_rare),      # rare: high magnitude
                ]),
                "dmin": np.concatenate([
                    rng.uniform(80, 600, n_common),     # common: far events
                    rng.uniform(5, 40, n_rare),         # rare: close events
                ]),
                "depth": rng.uniform(5, 200, n_common + n_rare).round(1),
                "gap": rng.uniform(50, 320, n_common + n_rare).round(1),
                "nst": rng.integers(4, 80, n_common + n_rare).tolist(),
                "label": np.concatenate([
                    rng.choice([0, 1], n_common, p=[0.85, 0.15]),
                    rng.choice([0, 1], n_rare,   p=[0.30, 0.70]),
                ]).tolist(),
            }
        ).sample(frac=1, random_state=42).reset_index(drop=True)
        df["magnitude"] = df["magnitude"].round(3)
        df["dmin"]      = df["dmin"].round(1)
    elif tool == "outliers":
        # Synthetic credit-risk dataset with realistic outlier structure:
        #   - most customers cluster around normal income/spend/age ranges
        #   - ~5% are injected as extreme outliers (very high spend, unusual age, etc.)
        n_normal = 285
        n_outlier = 15
        df_normal = pd.DataFrame(
            {
                "age":             rng.integers(22, 65, n_normal).tolist(),
                "annual_income":   rng.normal(55_000, 12_000, n_normal).round(0),
                "monthly_spend":   rng.normal(1_800, 400, n_normal).round(0),
                "credit_score":    rng.integers(580, 850, n_normal).tolist(),
                "num_accounts":    rng.integers(1, 8, n_normal).tolist(),
                "late_payments":   rng.integers(0, 3, n_normal).tolist(),
                "label":           rng.choice([0, 1], n_normal, p=[0.85, 0.15]).tolist(),
            }
        )
        df_outlier = pd.DataFrame(
            {
                "age":             rng.choice([17, 91, 95, 14, 88], n_outlier).tolist(),
                "annual_income":   rng.choice([320_000, 5_000, 280_000, 3_500], n_outlier).tolist(),
                "monthly_spend":   rng.choice([18_000, 22_000, 150, 25_000], n_outlier).tolist(),
                "credit_score":    rng.choice([200, 210, 950, 980, 190], n_outlier).tolist(),
                "num_accounts":    rng.choice([25, 30, 0], n_outlier).tolist(),
                "late_payments":   rng.choice([18, 22, 0], n_outlier).tolist(),
                "label":           rng.choice([0, 1], n_outlier).tolist(),
            }
        )
        df = (
            pd.concat([df_normal, df_outlier], ignore_index=True)
            .sample(frac=1, random_state=42)
            .reset_index(drop=True)
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
