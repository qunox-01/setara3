from __future__ import annotations

from fastapi import HTTPException

from app.database import AsyncSessionLocal
from app.models import ConsentLog

POLICY_VERSION = "2026-03-16"

_TRUE_VALUES = {"1", "true", "yes", "on"}


def is_accepted(value: str | None) -> bool:
    return (value or "").strip().lower() in _TRUE_VALUES


def validate_legal_acceptance(accept_legal: str | None, policy_version: str | None) -> None:
    if not is_accepted(accept_legal):
        raise HTTPException(
            status_code=422,
            detail="You must accept Terms, Privacy Policy, and Cookie Policy to continue.",
        )
    if (policy_version or "").strip() != POLICY_VERSION:
        raise HTTPException(
            status_code=422,
            detail="Legal policy version is missing or outdated. Please refresh and try again.",
        )


async def log_consent(
    *,
    session_id: str,
    action: str,
    source: str = "",
    policy_version: str = POLICY_VERSION,
) -> None:
    async with AsyncSessionLocal() as session:
        session.add(
            ConsentLog(
                session_id=session_id,
                action=action,
                policy_version=policy_version,
                source=source,
            )
        )
        await session.commit()
