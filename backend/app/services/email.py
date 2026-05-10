from __future__ import annotations

import logging

import httpx

from app.config import get_settings

logger = logging.getLogger(__name__)

_RESEND_ENDPOINT = "https://api.resend.com/emails"


async def send_password_reset_email(*, to: str, reset_url: str) -> None:
    """Send a password reset email via Resend.

    If RESEND_API_KEY is unset, logs the link instead (dev mode).
    """
    settings = get_settings()
    if not settings.resend_api_key:
        logger.warning("RESEND_API_KEY not set — password reset link for %s: %s", to, reset_url)
        return

    subject = "OptiPrice AI — Şifre Sıfırlama"
    html = f"""
        <div style="font-family:system-ui,sans-serif;max-width:480px;margin:0 auto;padding:24px">
          <h2 style="color:#0f172a">Şifrenizi sıfırlayın</h2>
          <p>OptiPrice AI hesabınız için şifre sıfırlama talebi aldık.</p>
          <p>
            <a href="{reset_url}"
               style="display:inline-block;background:#2563eb;color:#fff;padding:10px 18px;border-radius:6px;text-decoration:none">
              Şifremi sıfırla
            </a>
          </p>
          <p style="color:#64748b;font-size:13px">
            Bu bağlantı 1 saat içinde geçerliliğini yitirir. Talep sizden gelmediyse bu maili silebilirsiniz.
          </p>
        </div>
    """

    payload = {
        "from": settings.resend_from_email,
        "to": [to],
        "subject": subject,
        "html": html,
    }
    headers = {"Authorization": f"Bearer {settings.resend_api_key}"}

    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.post(_RESEND_ENDPOINT, json=payload, headers=headers)
        if resp.status_code >= 400:
            logger.error("Resend send failed (%s): %s", resp.status_code, resp.text)
            resp.raise_for_status()
