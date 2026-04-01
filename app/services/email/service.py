from __future__ import annotations

import logging
from pathlib import Path

import httpx
from jinja2 import Environment, FileSystemLoader, select_autoescape

from app.config import settings

logger = logging.getLogger(__name__)

_TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"
_jinja = Environment(
    loader=FileSystemLoader(str(_TEMPLATES_DIR)),
    autoescape=select_autoescape(["html", "xml"]),
)


def _is_enabled() -> bool:
    return bool(settings.resend_api_key.strip())


def _render(template_name: str, context: dict) -> str:
    return _jinja.get_template(template_name).render(**context)


async def _send_email(
    *,
    to_email: str,
    subject: str,
    html_template: str,
    text_template: str,
    context: dict,
    reply_to: str | None = None,
) -> None:
    if not to_email.strip():
        logger.info("Skipping email send because recipient is empty")
        return

    if not _is_enabled():
        logger.info("Skipping email send because RESEND_API_KEY is not configured")
        return

    payload = {
        "from": settings.email_from,
        "to": [to_email],
        "subject": subject,
        "html": _render(html_template, context),
        "text": _render(text_template, context),
    }
    if reply_to:
        payload["reply_to"] = [reply_to]

    headers = {
        "Authorization": f"Bearer {settings.resend_api_key}",
        "Content-Type": "application/json",
    }
    url = f"{settings.resend_api_base.rstrip('/')}/emails"

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(url, headers=headers, json=payload)
            response.raise_for_status()
    except httpx.HTTPError:
        logger.exception("Failed to send email via Resend")


async def send_lead_capture_confirmation(email: str, source: str, tool: str) -> None:
    await _send_email(
        to_email=email,
        subject="We received your Xariff request",
        html_template="lead_capture_confirmation.html",
        text_template="lead_capture_confirmation.txt",
        context={
            "email": email,
            "source": source or "homepage",
            "tool": tool or "general",
            "reply_to": settings.email_reply_to,
        },
        reply_to=settings.email_reply_to,
    )


async def send_lead_capture_notification(email: str, source: str, tool: str, utm_source: str) -> None:
    await _send_email(
        to_email=settings.lead_notification_to,
        subject="New Xariff email capture",
        html_template="lead_capture_notification.html",
        text_template="lead_capture_notification.txt",
        context={
            "email": email,
            "source": source or "homepage",
            "tool": tool or "",
            "utm_source": utm_source or "",
        },
        reply_to=email,
    )


async def send_contact_notification(
    *,
    name: str,
    email: str,
    category: str,
    subject: str,
    message: str,
) -> None:
    await _send_email(
        to_email=settings.contact_notification_to,
        subject=f"New contact message: {subject}",
        html_template="contact_notification.html",
        text_template="contact_notification.txt",
        context={
            "name": name,
            "email": email,
            "category": category,
            "subject": subject,
            "message": message,
        },
        reply_to=email,
    )


async def send_contact_confirmation(*, name: str, email: str, subject: str) -> None:
    await _send_email(
        to_email=email,
        subject="We received your message",
        html_template="contact_confirmation.html",
        text_template="contact_confirmation.txt",
        context={
            "name": name,
            "subject": subject,
            "reply_to": settings.email_reply_to,
        },
        reply_to=settings.email_reply_to,
    )


async def send_booking_confirmation(
    *,
    name: str,
    email: str,
    dataset_description: str,
) -> None:
    await _send_email(
        to_email=email,
        subject="We received your Data Terrain Analysis Audit request",
        html_template="booking_confirmation.html",
        text_template="booking_confirmation.txt",
        context={
            "name": name,
            "dataset_description": dataset_description,
            "reply_to": settings.email_reply_to,
        },
        reply_to=settings.email_reply_to,
    )


async def send_booking_notification(
    *,
    name: str,
    email: str,
    company: str,
    role: str,
    dataset_description: str,
    dataset_size: str,
) -> None:
    await _send_email(
        to_email=settings.contact_notification_to,
        subject=f"New Audit Booking from {name}",
        html_template="booking_notification.html",
        text_template="booking_notification.txt",
        context={
            "name": name,
            "email": email,
            "company": company,
            "role": role,
            "dataset_description": dataset_description,
            "dataset_size": dataset_size,
        },
        reply_to=email,
    )


async def send_scorecard_report_ready(*, email: str, report_id: str) -> None:
    report_url = f"{settings.public_base_url.rstrip('/')}/report/{report_id}"
    await _send_email(
        to_email=email,
        subject="Your Xariff report is ready",
        html_template="scorecard_report_ready.html",
        text_template="scorecard_report_ready.txt",
        context={
            "report_url": report_url,
            "report_id": report_id,
            "reply_to": settings.email_reply_to,
        },
        reply_to=settings.email_reply_to,
    )
