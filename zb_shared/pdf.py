"""zb_shared.pdf — duenne, template-agnostische PDF-/HTML-Helfer.

Aus der Survey (wf_2d118cd3): die PDF-Engines divergieren stark (xhtml2pdf in Mitarbeiter-App
+ objektaudit-app, reportlab in objektbesuch-agent, Playwright in der Prozessdoku). Eine
gemeinsame Engine-Abstraktion lohnt NICHT. Geteilt wird nur, was ueberall identisch ist:

- escape_html()      — HTML-Escaping (bisher in jeder App als _esc() reimplementiert)
- format_date_de()   — ISO -> dd.mm.yyyy (mit Fallback)
- logo_data_uri()    — PNG/JPG -> data:-URI fuer Inline-Einbettung (mit Cache)
- html_to_pdf_bytes()— xhtml2pdf-Boilerplate (pisa.CreatePDF -> bytes). xhtml2pdf ist eine
                       OPTIONALE Dependency: nur Apps, die diesen Helfer nutzen, brauchen
                       `pip install "zb-shared[pdf]"`. Import erfolgt lazy.

App-spezifisch BLEIBT app-seitig: die konkreten HTML-Templates, Storage-Uploads, Bilder-Logik.
Konsolidierung P2.2, [d-303].
"""
from __future__ import annotations

import base64
import logging
import mimetypes
from io import BytesIO
from pathlib import Path
from typing import Optional, Union

logger = logging.getLogger(__name__)

_LOGO_CACHE: dict[str, Optional[str]] = {}


def escape_html(text: Optional[str], fallback: str = "") -> str:
    """HTML-Escaping fuer Text in Templates. Leeres/None -> fallback."""
    if text is None or text == "":
        return fallback
    return (
        str(text)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def format_date_de(iso_str: Optional[str], pattern: str = "%d.%m.%Y", fallback: str = "—") -> str:
    """Formatiert einen ISO-Datums-/Zeitstring nach deutschem Muster. Fehlertolerant."""
    if not iso_str:
        return fallback
    from datetime import datetime

    raw = str(iso_str).strip().replace("Z", "+00:00")
    for parse in (
        lambda s: datetime.fromisoformat(s),
        lambda s: datetime.fromisoformat(s.split("T")[0]),
        lambda s: datetime.strptime(s[:10], "%Y-%m-%d"),
    ):
        try:
            return parse(raw).strftime(pattern)
        except (ValueError, TypeError):
            continue
    return str(iso_str)


def logo_data_uri(logo_path: Union[str, Path], use_cache: bool = True) -> Optional[str]:
    """Liest eine Bilddatei und gibt eine `data:<mime>;base64,...`-URI zurueck
    (fuer <img src> in xhtml2pdf-HTML). None, wenn die Datei fehlt. Gecacht pro Pfad."""
    key = str(logo_path)
    if use_cache and key in _LOGO_CACHE:
        return _LOGO_CACHE[key]
    result: Optional[str] = None
    try:
        p = Path(logo_path)
        if p.is_file():
            mime = mimetypes.guess_type(p.name)[0] or "image/png"
            b64 = base64.b64encode(p.read_bytes()).decode("ascii")
            result = f"data:{mime};base64,{b64}"
        else:
            logger.warning("Logo nicht gefunden: %s", logo_path)
    except Exception as e:  # noqa: BLE001
        logger.warning("Logo konnte nicht geladen werden (%s): %s", logo_path, e)
    if use_cache:
        _LOGO_CACHE[key] = result
    return result


def html_to_pdf_bytes(html: str, encoding: str = "utf-8") -> Optional[bytes]:
    """Rendert HTML zu PDF-Bytes via xhtml2pdf (pisa). None bei Fehler.

    xhtml2pdf ist eine optionale Dependency -> `pip install "zb-shared[pdf]"`.
    Bei fehlendem Paket wird eine aussagekraeftige Warnung geloggt und None zurueckgegeben
    (Best-Effort, kein harter Crash)."""
    try:
        from xhtml2pdf import pisa  # type: ignore
    except ImportError:
        logger.error(
            "html_to_pdf_bytes braucht xhtml2pdf — bitte 'zb-shared[pdf]' installieren "
            "(pip install \"zb-shared[pdf] @ git+...\")."
        )
        return None
    buffer = BytesIO()
    try:
        status = pisa.CreatePDF(html, dest=buffer, encoding=encoding)
    except Exception as e:  # noqa: BLE001
        logger.exception("PDF-Erzeugung fehlgeschlagen: %s", e)
        return None
    if getattr(status, "err", 1):
        logger.error("xhtml2pdf meldete Fehler beim Rendern")
        return None
    return buffer.getvalue()
