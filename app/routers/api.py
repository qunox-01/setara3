import io
import json
import os
import re
from datetime import datetime, timezone

import numpy as np
import pandas as pd
from fastapi import APIRouter, Request, Form, BackgroundTasks, HTTPException
from fastapi.responses import HTMLResponse, Response, StreamingResponse

from app.database import AsyncSessionLocal
from app.dependencies import get_session_id
from app.models import Email, Feedback, AnalyticsEvent, ContactMessage, BookingRequest
from app.services.email import (
    send_booking_confirmation,
    send_booking_notification,
    send_contact_confirmation,
    send_contact_notification,
    send_lead_capture_confirmation,
    send_lead_capture_notification,
)
from app.utils.legal import validate_legal_acceptance, log_consent, POLICY_VERSION

router = APIRouter()
EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


@router.post("/api/email-capture", response_class=HTMLResponse)
async def email_capture(
    request: Request,
    background_tasks: BackgroundTasks,
    email: str = Form(...),
    source: str = Form(default=""),
    tool: str = Form(default=""),
    utm_source: str = Form(default=""),
    accept_legal: str = Form(default=""),
    policy_version: str = Form(default=POLICY_VERSION),
):
    validate_legal_acceptance(accept_legal, policy_version)
    session_id = get_session_id(request)
    cleaned_email = email.strip().lower()
    if not EMAIL_PATTERN.match(cleaned_email):
        raise HTTPException(status_code=422, detail="Please provide a valid email address.")

    async with AsyncSessionLocal() as session:
        record = Email(email=cleaned_email, source=source, tool=tool, utm_source=utm_source)
        session.add(record)
        await session.commit()

    await log_consent(
        session_id=session_id,
        action="email_submit",
        source=source or "homepage",
        policy_version=policy_version,
    )
    background_tasks.add_task(send_lead_capture_confirmation, cleaned_email, source, tool)
    background_tasks.add_task(send_lead_capture_notification, cleaned_email, source, tool, utm_source)

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


@router.post("/api/contact-feedback", response_class=HTMLResponse)
async def contact_feedback(
    request: Request,
    background_tasks: BackgroundTasks,
    name: str = Form(..., min_length=2, max_length=120),
    email: str = Form(..., max_length=255),
    category: str = Form(default="general", max_length=40),
    subject: str = Form(default="", max_length=180),
    message: str = Form(..., min_length=10, max_length=5000),
):
    session_id = get_session_id(request)
    cleaned_email = email.strip().lower()
    if not EMAIL_PATTERN.match(cleaned_email):
        raise HTTPException(status_code=422, detail="Please provide a valid email address.")

    cleaned_message = message.strip()
    if not cleaned_message:
        raise HTTPException(status_code=422, detail="Message cannot be empty.")

    cleaned_subject = subject.strip() or "General inquiry"
    cleaned_category = (category or "general").strip().lower()

    async with AsyncSessionLocal() as session:
        record = ContactMessage(
            name=name.strip(),
            email=cleaned_email,
            category=cleaned_category,
            subject=cleaned_subject,
            message=cleaned_message,
            session_id=session_id,
        )
        session.add(record)
        await session.commit()

    cleaned_name = name.strip()
    background_tasks.add_task(
        send_contact_notification,
        name=cleaned_name,
        email=cleaned_email,
        category=cleaned_category,
        subject=cleaned_subject,
        message=cleaned_message,
    )
    background_tasks.add_task(
        send_contact_confirmation,
        name=cleaned_name,
        email=cleaned_email,
        subject=cleaned_subject,
    )

    return HTMLResponse(
        content="""
        <div class="p-4 bg-green-50 border border-green-200 rounded-lg">
            <p class="text-green-800 font-semibold">Thanks, your message has been sent.</p>
            <p class="text-sm text-green-700 mt-1">We will reply as soon as possible. You can also email contactus@xariff.com directly.</p>
        </div>
        """
    )


@router.post("/api/booking", response_class=HTMLResponse)
async def booking_request(
    request: Request,
    background_tasks: BackgroundTasks,
    name: str = Form(..., min_length=2, max_length=120),
    email: str = Form(..., max_length=255),
    company: str = Form(default="", max_length=120),
    role: str = Form(default="", max_length=120),
    dataset_description: str = Form(default="", max_length=3000),
    use_case: str = Form(default="", max_length=3000),
    dataset_size: str = Form(default="", max_length=80),
    goals: str = Form(default="", max_length=3000),
):
    session_id = get_session_id(request)
    cleaned_email = email.strip().lower()
    if not EMAIL_PATTERN.match(cleaned_email):
        raise HTTPException(status_code=422, detail="Please provide a valid email address.")

    async with AsyncSessionLocal() as session:
        record = BookingRequest(
            name=name.strip(),
            email=cleaned_email,
            company=company.strip(),
            role=role.strip(),
            dataset_description=dataset_description.strip(),
            use_case=use_case.strip(),
            dataset_size=dataset_size.strip(),
            goals=goals.strip(),
            session_id=session_id,
        )
        session.add(record)
        await session.commit()

    background_tasks.add_task(
        send_booking_notification,
        name=name.strip(),
        email=cleaned_email,
        company=company.strip(),
        role=role.strip(),
        dataset_description=dataset_description.strip(),
        dataset_size=dataset_size.strip(),
    )
    background_tasks.add_task(
        send_booking_confirmation,
        name=name.strip(),
        email=cleaned_email,
        dataset_description=dataset_description.strip(),
    )

    return HTMLResponse(
        content="""
        <div class="p-6 bg-green-50 border border-green-200 rounded-2xl text-center">
            <div class="text-3xl mb-3">&#10003;</div>
            <p class="text-green-800 font-bold text-lg">Booking request received!</p>
            <p class="text-green-700 text-sm mt-2">We'll review your dataset details and get back to you within 1–2 business days to confirm your audit.</p>
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
    elif tool == "drift_reference":
        # Reference (training) dataset — stable credit applicant population
        n = 400
        df = pd.DataFrame({
            "age":           rng.integers(22, 60, n).tolist(),
            "annual_income": rng.normal(55_000, 10_000, n).round(0),
            "loan_amount":   rng.normal(12_000, 3_000, n).round(0),
            "credit_score":  rng.integers(600, 820, n).tolist(),
            "employment_years": rng.integers(1, 20, n).tolist(),
            "num_accounts":  rng.integers(1, 7, n).tolist(),
            "region":        rng.choice(["North", "South", "East", "West"], n, p=[0.3, 0.3, 0.2, 0.2]).tolist(),
            "product":       rng.choice(["Standard", "Premium", "Basic"], n, p=[0.5, 0.3, 0.2]).tolist(),
            "default":       rng.choice([0, 1], n, p=[0.85, 0.15]).tolist(),
        })

    elif tool == "drift_current":
        # Current (production) dataset — shifted population: younger, lower income, different region mix
        rng2 = np.random.default_rng(99)
        n = 350
        df = pd.DataFrame({
            "age":           rng2.integers(18, 45, n).tolist(),          # shifted younger
            "annual_income": rng2.normal(42_000, 14_000, n).round(0),   # lower income + higher variance
            "loan_amount":   rng2.normal(12_500, 3_200, n).round(0),    # similar
            "credit_score":  rng2.integers(550, 780, n).tolist(),        # slightly lower
            "employment_years": rng2.integers(0, 12, n).tolist(),        # less experience
            "num_accounts":  rng2.integers(1, 5, n).tolist(),
            "region":        rng2.choice(["North", "South", "East", "West"], n, p=[0.1, 0.1, 0.6, 0.2]).tolist(),  # East dominates
            "product":       rng2.choice(["Standard", "Premium", "Basic"], n, p=[0.3, 0.1, 0.6]).tolist(),          # Basic dominates
            "default":       rng2.choice([0, 1], n, p=[0.72, 0.28]).tolist(),  # higher default rate
        })

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
    from app.utils.markdown import list_articles

    base = "https://xariff.com"
    template_lastmods = {
        "/": "templates/home.html",
        "/tools": "templates/tools/index.html",
        "/tools/profiler": "templates/tools/profiler.html",
        "/tools/quality": "templates/tools/quality.html",
        "/tools/scorecard": "templates/tools/scorecard.html",
        "/tools/coverage": "templates/tools/coverage.html",
        "/tools/outliers": "templates/tools/outliers.html",
        "/tools/drift": "templates/tools/drift.html",
        "/research": "templates/blog/index.html",
        "/about": "templates/about.html",
        "/contact": "templates/contact.html",
        "/booking": "templates/booking.html",
        "/privacy": "templates/legal/privacy.html",
        "/terms": "templates/legal/terms.html",
        "/cookies": "templates/legal/cookies.html",
    }

    def lastmod_for(path: str) -> str:
        file_path = template_lastmods.get(path)
        if not file_path or not os.path.exists(file_path):
            return datetime.now(timezone.utc).date().isoformat()
        return datetime.fromtimestamp(os.path.getmtime(file_path), tz=timezone.utc).date().isoformat()

    static_urls = [
        ("/",               "1.0", "weekly",  lastmod_for("/")),
        ("/tools",          "0.9", "weekly",  lastmod_for("/tools")),
        ("/tools/profiler", "0.8", "monthly", lastmod_for("/tools/profiler")),
        ("/tools/quality",  "0.8", "monthly", lastmod_for("/tools/quality")),
        ("/tools/scorecard","0.8", "monthly", lastmod_for("/tools/scorecard")),
        ("/tools/coverage", "0.8", "monthly", lastmod_for("/tools/coverage")),
        ("/tools/outliers", "0.8", "monthly", lastmod_for("/tools/outliers")),
        ("/tools/drift",    "0.8", "monthly", lastmod_for("/tools/drift")),
        ("/research",       "0.7", "weekly",  lastmod_for("/research")),
        ("/about",          "0.5", "monthly", lastmod_for("/about")),
        ("/contact",        "0.5", "monthly", lastmod_for("/contact")),
        ("/booking",        "0.6", "monthly", lastmod_for("/booking")),
        ("/privacy",        "0.3", "yearly",  lastmod_for("/privacy")),
        ("/terms",          "0.3", "yearly",  lastmod_for("/terms")),
        ("/cookies",        "0.3", "yearly",  lastmod_for("/cookies")),
    ]
    url_tags = "\n".join(
        f"  <url><loc>{base}{u}</loc><lastmod>{lastmod}</lastmod><changefreq>{freq}</changefreq><priority>{pri}</priority></url>"
        for u, pri, freq, lastmod in static_urls
    )
    # Add individual blog article URLs
    articles = list_articles("content/articles")
    for article in articles:
        slug = article.get("slug", "")
        date = article.get("date", "")
        lastmod = f"<lastmod>{date}</lastmod>" if date else ""
        url_tags += f"\n  <url><loc>{base}/research/{slug}</loc>{lastmod}<changefreq>monthly</changefreq><priority>0.7</priority></url>"

    xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
{url_tags}
</urlset>"""
    return Response(content=xml, media_type="application/xml")


@router.get("/robots.txt")
async def robots():
    robots_path = os.path.join(os.path.dirname(__file__), "..", "..", "robots.txt")
    try:
        with open(os.path.normpath(robots_path), "r", encoding="utf-8") as f:
            content = f.read()
    except FileNotFoundError:
        content = "User-agent: *\nAllow: /\nSitemap: https://xariff.com/sitemap.xml\n"
    return Response(content=content, media_type="text/plain")
