"""Transactional Email Provider abstraction (Phase S2-01).

Strictly adheres to zero-PII and zero-secret logging:
- Raw verification / reset tokens and recipient email addresses are NEVER logged.
- Automated tests always use `MockEmailProvider` (enforced in `tests/conftest.py`).
- `PostmarkEmailProvider` passes credentials via HTTP headers (`X-Postmark-Server-Token`),
  never URL query strings.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Protocol
from urllib.parse import urlencode

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class OutboxEmailRecord:
    purpose: str
    recipient: str
    token: str
    action_url: str


_MOCK_OUTBOX: list[OutboxEmailRecord] = []


def get_mock_email_outbox() -> list[OutboxEmailRecord]:
    return list(_MOCK_OUTBOX)


def clear_mock_email_outbox() -> None:
    _MOCK_OUTBOX.clear()


class EmailProvider(Protocol):
    def send_email_verification(self, recipient: str, token: str) -> None: ...

    def send_password_reset(self, recipient: str, token: str) -> None: ...

    def send_candidate_invite(
        self,
        recipient: str,
        invite_token: str,
        organization_name: str,
        form_title: str,
    ) -> None: ...

    def send_candidate_otp(
        self,
        recipient: str,
        otp_code: str,
        organization_name: str,
        form_title: str,
    ) -> None: ...


def _build_action_url(path: str, token: str) -> str:
    base = settings.FRONTEND_PUBLIC_URL.rstrip("/")
    query = urlencode({"token": token})
    return f"{base}{path}?{query}"


class MockEmailProvider:
    """In-memory transactional email sink for local development and tests."""

    def send_email_verification(self, recipient: str, token: str) -> None:
        url = _build_action_url("/verify-email", token)
        _MOCK_OUTBOX.append(
            OutboxEmailRecord(
                purpose="email_verification",
                recipient=recipient,
                token=token,
                action_url=url,
            )
        )
        logger.info(
            "Queued transactional email: purpose=email_verification provider=mock"
        )

    def send_password_reset(self, recipient: str, token: str) -> None:
        url = _build_action_url("/reset-password", token)
        _MOCK_OUTBOX.append(
            OutboxEmailRecord(
                purpose="password_reset",
                recipient=recipient,
                token=token,
                action_url=url,
            )
        )
        logger.info("Queued transactional email: purpose=password_reset provider=mock")

    def send_candidate_invite(
        self,
        recipient: str,
        invite_token: str,
        organization_name: str,
        form_title: str,
    ) -> None:
        base = settings.FRONTEND_PUBLIC_URL.rstrip("/")
        url = f"{base}/portal/invite/{invite_token}"
        _MOCK_OUTBOX.append(
            OutboxEmailRecord(
                purpose="candidate_invite",
                recipient=recipient,
                token=invite_token,
                action_url=url,
            )
        )
        logger.info(
            "Queued transactional email: purpose=candidate_invite provider=mock"
        )

    def send_candidate_otp(
        self,
        recipient: str,
        otp_code: str,
        organization_name: str,
        form_title: str,
    ) -> None:
        _MOCK_OUTBOX.append(
            OutboxEmailRecord(
                purpose="candidate_otp",
                recipient=recipient,
                token=otp_code,
                action_url="",
            )
        )
        logger.info("Queued transactional email: purpose=candidate_otp provider=mock")


class PostmarkEmailProvider:
    """EU-ready HTTP transactional email sender via Postmark API."""

    _ENDPOINT = "https://api.postmarkapp.com/email"

    def _send(self, recipient: str, subject: str, text_body: str, purpose: str) -> None:
        server_token = (settings.POSTMARK_SERVER_TOKEN or "").strip()
        if not server_token:
            raise RuntimeError("POSTMARK_SERVER_TOKEN is not configured.")
        response = httpx.post(
            self._ENDPOINT,
            headers={
                "Accept": "application/json",
                "Content-Type": "application/json",
                "X-Postmark-Server-Token": server_token,
            },
            json={
                "From": settings.EMAIL_FROM_ADDRESS,
                "To": recipient,
                "Subject": subject,
                "TextBody": text_body,
                "MessageStream": "outbound",
            },
            timeout=10.0,
        )
        response.raise_for_status()
        logger.info(
            "Sent transactional email: purpose=%s provider=postmark status=%d",
            purpose,
            response.status_code,
        )

    def send_email_verification(self, recipient: str, token: str) -> None:
        action_url = _build_action_url("/verify-email", token)
        body = (
            "Verify your AI Form Assistant email address by opening the link below:\n\n"
            f"{action_url}\n\n"
            f"This link expires in {settings.EMAIL_VERIFICATION_TTL_HOURS} hours."
        )
        self._send(
            recipient=recipient,
            subject="Verify your email — AI Form Assistant",
            text_body=body,
            purpose="email_verification",
        )

    def send_password_reset(self, recipient: str, token: str) -> None:
        action_url = _build_action_url("/reset-password", token)
        body = (
            "A password reset was requested for your AI Form Assistant account.\n"
            "If you requested this change, open the single-use link below:\n\n"
            f"{action_url}\n\n"
            f"This link expires in {settings.PASSWORD_RESET_TTL_MINUTES} minutes. "
            "If you did not request a reset, you can safely ignore this message."
        )
        self._send(
            recipient=recipient,
            subject="Reset your password — AI Form Assistant",
            text_body=body,
            purpose="password_reset",
        )

    def send_candidate_invite(
        self,
        recipient: str,
        invite_token: str,
        organization_name: str,
        form_title: str,
    ) -> None:
        base = settings.FRONTEND_PUBLIC_URL.rstrip("/")
        action_url = f"{base}/portal/invite/{invite_token}"
        body = (
            f"{organization_name} has invited you to complete '{form_title}' "
            "using AI Form Assistant.\n\n"
            f"Open your secure intake link:\n{action_url}\n\n"
            "You will be asked to verify your email with a 6-digit code before starting. "
            "This invitation expires in 14 days."
        )
        self._send(
            recipient=recipient,
            subject=f"Application intake invitation from {organization_name}",
            text_body=body,
            purpose="candidate_invite",
        )

    def send_candidate_otp(
        self,
        recipient: str,
        otp_code: str,
        organization_name: str,
        form_title: str,
    ) -> None:
        body = (
            f"Your 6-digit verification code for '{form_title}' "
            f"({organization_name}) is:\n\n"
            f"{otp_code}\n\n"
            "This code expires in 10 minutes. If you did not request this code, "
            "you can safely ignore this email."
        )
        self._send(
            recipient=recipient,
            subject=f"Your verification code for {organization_name}",
            text_body=body,
            purpose="candidate_otp",
        )


def get_email_provider() -> EmailProvider:
    if settings.EMAIL_PROVIDER == "postmark":
        return PostmarkEmailProvider()
    return MockEmailProvider()
