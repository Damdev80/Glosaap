"""
Utilidades centralizadas para análisis y formateo de fechas.
Maneja formatos estándar RFC 2822, ISO 8601, marcas de tiempo,
fechas en español (meses y días completos y abreviados),
zonas horarias con comentarios parentéticos como (COT), (UTC), (EST), (GMT-05:00), etc.
"""
from __future__ import annotations

import email.utils
import re
from datetime import datetime
from typing import Any

import pandas as pd

# Diccionario español -> inglés para traducción antes de parseo RFC/strptime
SPANISH_DATE_MAP = {
    "enero": "Jan", "febrero": "Feb", "marzo": "Mar", "abril": "Apr",
    "mayo": "May", "junio": "Jun", "julio": "Jul", "agosto": "Aug",
    "septiembre": "Sep", "setiembre": "Sep", "octubre": "Oct",
    "noviembre": "Nov", "diciembre": "Dec",
    "ene": "Jan", "feb": "Feb", "mar": "Mar", "abr": "Apr",
    "may": "May", "jun": "Jun", "jul": "Jul", "ago": "Aug",
    "sep": "Sep", "set": "Sep", "oct": "Oct", "nov": "Nov", "dic": "Dec",
    "lunes": "Mon", "martes": "Tue", "miercoles": "Wed", "miércoles": "Wed",
    "jueves": "Thu", "viernes": "Fri", "sabado": "Sat", "sábado": "Sat", "domingo": "Sun",
    "lun": "Mon", "mie": "Wed", "mié": "Wed",
    "jue": "Thu", "vie": "Fri", "sab": "Sat", "sáb": "Sat", "dom": "Sun",
}

STRPTIME_FORMATS = (
    "%a, %d %b %Y %H:%M:%S %z",
    "%a, %d %b %Y %H:%M:%S",
    "%d %b %Y %H:%M:%S %z",
    "%d %b %Y %H:%M:%S",
    "%Y-%m-%d %H:%M:%S",
    "%d/%m/%Y %H:%M:%S",
    "%d-%m-%Y %H:%M:%S",
    "%d %b %Y %H:%M",
    "%d %b %Y",
    "%Y-%m-%d",
    "%d/%m/%Y",
    "%d-%m-%Y",
)


def parse_email_date(msg_date: Any) -> datetime | None:
    """Parsea una fecha de correo o reporte a datetime naive (hora local).

    Soporta:
    - Objetos datetime o pd.Timestamp directos.
    - Encabezados RFC 2822 de IMAP.
    - Zonas horarias comentadas tipo `Thu, 20 Nov 2026 10:45:00 -0500 (COT)`.
    - Fechas en español: `jueves, 20 de noviembre de 2026 10:45:00`.
    - Fechas ISO y formatos colombianos comunes (DD/MM/YYYY).
    """
    if msg_date is None:
        return None

    if hasattr(msg_date, "strftime"):
        if getattr(msg_date, "tzinfo", None) is not None:
            try:
                return msg_date.astimezone().replace(tzinfo=None)
            except Exception:
                return msg_date.replace(tzinfo=None)
        if isinstance(msg_date, pd.Timestamp):
            return msg_date.to_pydatetime()
        return msg_date

    if not isinstance(msg_date, str):
        return None

    raw = msg_date.strip()
    if not raw:
        return None

    # 1. Limpiar comentarios entre paréntesis en cualquier parte (ej: (COT), (UTC), (GMT-05:00))
    cleaned = re.sub(r"\s*\([^)]*\)", " ", raw).strip()
    cleaned = re.sub(r"\s+GMT(\s|$)", " ", cleaned).strip()

    # 2. Traducir español a inglés y remover 'de'
    translated = cleaned
    for es, en in SPANISH_DATE_MAP.items():
        translated = re.sub(rf"\b{es}\.?\b", en, translated, flags=re.IGNORECASE)
    translated = re.sub(r"\bde\b", " ", translated, flags=re.IGNORECASE)
    translated = re.sub(r"\s+", " ", translated).strip()

    # 3. email.utils.parsedate_to_datetime (RFC 2822 estándar)
    for candidate in (translated, cleaned):
        try:
            dt = email.utils.parsedate_to_datetime(candidate)
            if dt is not None:
                if dt.tzinfo is not None:
                    try:
                        return dt.astimezone().replace(tzinfo=None)
                    except Exception:
                        return dt.replace(tzinfo=None)
                return dt
        except Exception:
            pass

    # 4. Formatos strptime explícitos
    for candidate in (translated, cleaned, raw):
        for fmt in STRPTIME_FORMATS:
            try:
                dt = datetime.strptime(candidate, fmt)
                if hasattr(dt, "tzinfo") and dt.tzinfo is not None:
                    try:
                        return dt.astimezone().replace(tzinfo=None)
                    except Exception:
                        return dt.replace(tzinfo=None)
                return dt
            except ValueError:
                continue

    # 5. Fallback con pandas
    try:
        if len(translated) >= 10 and translated[:4].isdigit() and translated[4] in ("-", "/"):
            pdt = pd.to_datetime(translated, errors="coerce")
        else:
            pdt = pd.to_datetime(translated, dayfirst=True, errors="coerce")
        if pd.notna(pdt):
            dt = pdt.to_pydatetime()
            if hasattr(dt, "tzinfo") and dt.tzinfo is not None:
                try:
                    return dt.astimezone().replace(tzinfo=None)
                except Exception:
                    return dt.replace(tzinfo=None)
            return dt
    except Exception:
        pass

    return None


def format_date_dmy(dt_or_str: Any) -> str:
    """Convierte cualquier fecha válida a string DD/MM/YYYY. Retorna '' si es inválida."""
    if dt_or_str is None or dt_or_str == "":
        return ""
    dt = parse_email_date(dt_or_str)
    return dt.strftime("%d/%m/%Y") if dt else ""


def format_date_iso(dt_or_str: Any) -> str:
    """Convierte cualquier fecha válida a string YYYY-MM-DD HH:MM:SS. Retorna '' si es inválida."""
    if dt_or_str is None or dt_or_str == "":
        return ""
    dt = parse_email_date(dt_or_str)
    return dt.strftime("%Y-%m-%d %H:%M:%S") if dt else ""
