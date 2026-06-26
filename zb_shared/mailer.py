"""zb_shared.mailer — kanonischer E-Mail-Versand via Resend (DSGVO-konformer EU-Versand).

Vereinheitlicht die bisher 7 kopierten Resend-Aufrufstellen (raw `requests` vs. `resend`-SDK,
Base64-Boilerplate) aus Mitarbeiter-App / Reklamationsmanagement / objektaudit-app /
objektbesuch-agent. Konsolidierung P2.2, [d-303].

Design-Prinzipien (aus der Survey wf_2d118cd3):
- EINE Transport-Schicht: raw HTTP-POST auf die Resend-API via httpx (kein resend-SDK noetig;
  httpx ist ohnehin schon zb-shared-Dependency). Anhang-Content IMMER Base64-String.
- App-spezifisch BLEIBT app-seitig: from_email/from_name-Defaults, HTML-Template-Logik,
  Empfaenger-Bestimmung (DB/ENV), Reply-To. Diese werden als Argumente uebergeben.
- Best-Effort: wirft NIE — gibt {"sent": bool, "reason": str|None, "to": list, "id": str|None}
  zurueck (damit Cron-/WebSocket-Workflows nicht abbrechen, analog Bestandsverhalten).
- api_key default aus ENV RESEND_API_KEY, kann aber explizit uebergeben werden.

API:
    send_email(...)            -> dict      (sync)
    send_email_async(...)      -> dict      (async, z.B. objektbesuch-agent)
    send_email_with_pdf(...)   -> dict      (sync Convenience: 1 PDF-Anhang)
"""
from __future__ import annotations

import base64
import logging
import os
from typing import Optional

import httpx

logger = logging.getLogger(__name__)

RESEND_ENDPOINT = "https://api.resend.com/emails"


def _build_payload(
    from_email: str,
    from_name: str,
    to: list[str] | str,
    subject: str,
    html: str = "",
    text: str = "",
    attachments: Optional[list[dict]] = None,
    reply_to: Optional[str] = None,
) -> dict:
    """Baut die Resend-JSON-Payload. `attachments` ist eine Liste von
    {"filename": str, "content": bytes|str}. Bytes werden zu Base64-String kodiert;
    ein bereits uebergebener String wird unveraendert genutzt."""
    to_list = [to] if isinstance(to, str) else list(to)
    payload: dict = {
        "from": f"{from_name} <{from_email}>" if from_name else from_email,
        "to": to_list,
        "subject": subject,
    }
    if html:
        payload["html"] = html
    if text:
        payload["text"] = text
    if reply_to:
        payload["reply_to"] = reply_to
    if attachments:
        norm: list[dict] = []
        for att in attachments:
            content = att.get("content")
            if isinstance(content, (bytes, bytearray)):
                content = base64.b64encode(bytes(content)).decode("ascii")
            norm.append({"filename": att.get("filename", "anhang"), "content": content})
        payload["attachments"] = norm
    return payload


def _result_from_response(resp: httpx.Response, to_list: list[str]) -> dict:
    if 200 <= resp.status_code < 300:
        try:
            msg_id = resp.json().get("id")
        except Exception:  # noqa: BLE001
            msg_id = None
        logger.info("Resend angenommen: id=%s | to=%s", msg_id, to_list)
        return {"sent": True, "reason": None, "to": to_list, "id": msg_id}
    reason = f"HTTP {resp.status_code}: {resp.text[:300]}"
    logger.error("Resend lehnte den Versand ab: %s", reason)
    return {"sent": False, "reason": reason, "to": to_list, "id": None}


def _preflight(api_key: str, to_list: list[str]) -> Optional[dict]:
    """Gibt ein Fehler-dict zurueck, wenn nicht gesendet werden kann; sonst None."""
    if not api_key:
        logger.warning("RESEND_API_KEY fehlt — Mail-Versand uebersprungen")
        return {"sent": False, "reason": "RESEND_API_KEY fehlt", "to": to_list, "id": None}
    if not to_list:
        logger.warning("Kein Empfaenger — Mail uebersprungen")
        return {"sent": False, "reason": "Kein Empfaenger", "to": to_list, "id": None}
    return None


def send_email(
    from_email: str,
    from_name: str,
    to: list[str] | str,
    subject: str,
    html: str = "",
    text: str = "",
    attachments: Optional[list[dict]] = None,
    reply_to: Optional[str] = None,
    api_key: Optional[str] = None,
    timeout: float = 30.0,
) -> dict:
    """Versendet eine E-Mail ueber Resend (synchron). Wirft nie."""
    key = (api_key if api_key is not None else os.getenv("RESEND_API_KEY", "")).strip()
    to_list = [to] if isinstance(to, str) else list(to)
    pre = _preflight(key, to_list)
    if pre is not None:
        return pre
    payload = _build_payload(from_email, from_name, to_list, subject, html, text, attachments, reply_to)
    try:
        resp = httpx.post(
            RESEND_ENDPOINT,
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
            json=payload,
            timeout=timeout,
        )
        return _result_from_response(resp, to_list)
    except httpx.HTTPError as e:
        logger.error("Resend-Request fehlgeschlagen: %s", e)
        return {"sent": False, "reason": f"{type(e).__name__}: {e}", "to": to_list, "id": None}


async def send_email_async(
    from_email: str,
    from_name: str,
    to: list[str] | str,
    subject: str,
    html: str = "",
    text: str = "",
    attachments: Optional[list[dict]] = None,
    reply_to: Optional[str] = None,
    api_key: Optional[str] = None,
    timeout: float = 30.0,
) -> dict:
    """Versendet eine E-Mail ueber Resend (asynchron, nicht-blockierend). Wirft nie."""
    key = (api_key if api_key is not None else os.getenv("RESEND_API_KEY", "")).strip()
    to_list = [to] if isinstance(to, str) else list(to)
    pre = _preflight(key, to_list)
    if pre is not None:
        return pre
    payload = _build_payload(from_email, from_name, to_list, subject, html, text, attachments, reply_to)
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.post(
                RESEND_ENDPOINT,
                headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
                json=payload,
            )
        return _result_from_response(resp, to_list)
    except httpx.HTTPError as e:
        logger.error("Resend-Request fehlgeschlagen: %s", e)
        return {"sent": False, "reason": f"{type(e).__name__}: {e}", "to": to_list, "id": None}


def send_email_with_pdf(
    from_email: str,
    from_name: str,
    to: list[str] | str,
    subject: str,
    html: str,
    pdf_bytes: bytes,
    pdf_filename: str,
    reply_to: Optional[str] = None,
    api_key: Optional[str] = None,
) -> dict:
    """Convenience: versendet genau ein PDF als Anhang (Base64-Kodierung intern)."""
    return send_email(
        from_email=from_email,
        from_name=from_name,
        to=to,
        subject=subject,
        html=html,
        attachments=[{"filename": pdf_filename, "content": pdf_bytes}],
        reply_to=reply_to,
        api_key=api_key,
    )
