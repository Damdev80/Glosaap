"""
Servicio de cálculo de periodicidades, adaptador de esquema para tabla externa
de glosas y motor de exportación a Excel (.xlsx) y PDF (.pdf).

Diseñado de forma desacoplada para conectar cualquier tabla de base de datos
externa una vez definidos el nombre de tabla y el mapeo de columnas.
"""
from __future__ import annotations

import calendar
import os
import re
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Any

import openpyxl
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

from app.config.settings import TEMP_DIR, ensure_dir, get_output_dir, logger
from app.core.date_utils import parse_email_date

# ==================== CONSTANTES DE PERIODICIDAD ====================

PERIOD_ROLLING_DAYS: dict[str, int] = {
    "SEMANAL": 7,
    "QUINCENAL": 15,
    "MENSUAL": 30,
    "TRIMESTRAL": 90,
    "SEMESTRAL": 180,
}

PERIOD_LABELS: dict[str, str] = {
    "SEMANAL": "Semanal",
    "QUINCENAL": "Quincenal",
    "MENSUAL": "Mensual",
    "TRIMESTRAL": "Trimestral",
    "SEMESTRAL": "Semestral",
    "PERSONALIZADO": "Personalizado",
}

VALID_PERIODICITIES = tuple(PERIOD_LABELS.keys())

DEFAULT_COLUMN_MAPPING: dict[str, str] = {
    "id_glosa": "id_glosa",
    "fecha_glosa": "fecha_glosa",
    "numero_factura": "numero_factura",
    "entidad_eps": "entidad_eps",
    "codigo_glosa": "codigo_glosa",
    "concepto_glosa": "concepto_glosa",
    "valor_facturado": "valor_facturado",
    "valor_glosado": "valor_glosado",
    "estado_glosa": "estado_glosa",
    "usuario_auditor": "usuario_auditor",
    "servicio_glosado": "servicio_glosado",
    "centro_costo": "centro_costo",
    "observacion_general": "observacion_general",
}

MAX_PDF_DETAIL_ROWS = 500


# ==================== CALCULADORA DE PERIODOS ====================


class PeriodRangeCalculator:
    """Calcula rangos de fechas para cortes semanales, quincenales, mensuales, trimestrales y semestrales."""

    @staticmethod
    def get_period_label(periodicity: str) -> str:
        """Retorna la etiqueta legible para una periodicidad dada."""
        key = str(periodicity or "MENSUAL").strip().upper()
        return PERIOD_LABELS.get(key, "Personalizado")

    @staticmethod
    def calculate_range(
        periodicity: str,
        ref_date: date | None = None,
        mode: str = "rolling",
    ) -> tuple[date, date]:
        """
        Calcula el par (fecha_desde, fecha_hasta) según periodicidad y modo.

        Args:
            periodicity: SEMANAL, QUINCENAL, MENSUAL, TRIMESTRAL, SEMESTRAL o PERSONALIZADO.
            ref_date: Fecha de referencia (default: hoy).
            mode: "rolling" (últimos N días desde ref_date) o "calendar" (periodo calendario).
        """
        ref = ref_date or date.today()
        period_key = str(periodicity or "MENSUAL").strip().upper()
        mode_key = str(mode or "rolling").strip().lower()

        if mode_key == "calendar":
            return PeriodRangeCalculator._calculate_calendar_range(period_key, ref)

        days = PERIOD_ROLLING_DAYS.get(period_key, 30)
        return (ref - timedelta(days=days), ref)

    @staticmethod
    def _calculate_calendar_range(period_key: str, ref: date) -> tuple[date, date]:
        """Calcula rangos alineados a calendario natural."""
        if period_key == "SEMANAL":
            start = ref - timedelta(days=ref.weekday())
            end = start + timedelta(days=6)
            return (start, end)

        if period_key == "QUINCENAL":
            last_day = calendar.monthrange(ref.year, ref.month)[1]
            if ref.day <= 15:
                return (date(ref.year, ref.month, 1), date(ref.year, ref.month, 15))
            return (date(ref.year, ref.month, 16), date(ref.year, ref.month, last_day))

        if period_key == "MENSUAL":
            last_day = calendar.monthrange(ref.year, ref.month)[1]
            return (date(ref.year, ref.month, 1), date(ref.year, ref.month, last_day))

        if period_key == "TRIMESTRAL":
            q_start_month = ((ref.month - 1) // 3) * 3 + 1
            q_end_month = q_start_month + 2
            last_day = calendar.monthrange(ref.year, q_end_month)[1]
            return (date(ref.year, q_start_month, 1), date(ref.year, q_end_month, last_day))

        if period_key == "SEMESTRAL":
            if ref.month <= 6:
                return (date(ref.year, 1, 1), date(ref.year, 6, 30))
            return (date(ref.year, 7, 1), date(ref.year, 12, 31))

        # PERSONALIZADO u otro fallback
        return (ref - timedelta(days=30), ref)


# ==================== ESQUEMA CONFIGURABLE Y MODELOS ====================


@dataclass
class ExternalTableSchema:
    """Esquema parametrizable de la tabla externa de glosas y mapeo de columnas."""

    database_name: str = "BD_EXTERNA"
    table_name: str = "TABLA_GLOSAS"
    column_mapping: dict[str, str] = field(default_factory=lambda: dict(DEFAULT_COLUMN_MAPPING))

    def configure(
        self,
        database_name: str,
        table_name: str,
        column_mapping: dict[str, str] | None = None,
    ) -> None:
        """Actualiza en caliente la base de datos, tabla y mapeo de columnas."""
        if database_name:
            self.database_name = str(database_name).strip()
        if table_name:
            self.table_name = str(table_name).strip()
        if column_mapping:
            merged = dict(self.column_mapping)
            for logical_key, physical_col in column_mapping.items():
                if logical_key in DEFAULT_COLUMN_MAPPING and physical_col:
                    merged[logical_key] = str(physical_col).strip()
            self.column_mapping = merged

    def resolve_value(self, raw_row: dict[str, Any], logical_key: str, default: Any = "") -> Any:
        """Extrae un valor del registro tolerando alias mapeados y diferencias de mayúsculas."""
        if not isinstance(raw_row, dict):
            return default

        target_col = self.column_mapping.get(logical_key, logical_key)
        candidates = [target_col, logical_key]

        # 1. Búsqueda exacta
        for key in candidates:
            if key in raw_row and raw_row[key] is not None:
                return raw_row[key]

        # 2. Búsqueda case-insensitive
        lower_map = {str(k).strip().lower(): v for k, v in raw_row.items()}
        for key in candidates:
            val = lower_map.get(str(key).strip().lower())
            if val is not None:
                return val

        return default


@dataclass
class ExternalGlosasReportData:
    """Contenedor completo de métricas, agrupaciones y detalle del informe de glosas."""

    periodicity: str
    period_label: str
    fecha_desde: str
    fecha_hasta: str
    generated_at: str
    database_name: str
    table_name: str
    total_glosas: int
    total_facturas: int
    valor_total_facturado: float
    valor_total_glosado: float
    porcentaje_glosado: float
    promedio_por_glosa: float
    resumen_por_entidad: list[dict[str, Any]] = field(default_factory=list)
    resumen_por_estado: list[dict[str, Any]] = field(default_factory=list)
    resumen_por_servicio: list[dict[str, Any]] = field(default_factory=list)
    resumen_por_facturador: list[dict[str, Any]] = field(default_factory=list)
    resumen_top_conceptos: list[dict[str, Any]] = field(default_factory=list)
    registros: list[dict[str, Any]] = field(default_factory=list)
    is_preview_data: bool = False
    source_note: str = ""


# ==================== UTILIDADES DE CONVERSIÓN ====================


def _to_float(value: Any) -> float:
    """Convierte valores numéricos, Decimal SQL o strings monetarios COP/US a float seguro.

    Un separador seguido de exactamente 3 dígitos (ej. "$250.000", "1.000.000")
    se interpreta como separador de miles; 1-2 dígitos finales como decimales.
    """
    if value is None or value == "":
        return 0.0
    if isinstance(value, (int, float, Decimal)):
        try:
            fval = float(value)
            return 0.0 if fval != fval else fval  # NaN guard
        except Exception:
            return 0.0
    texto = str(value).strip()
    if not texto:
        return 0.0

    negativo = texto.startswith("(") and texto.endswith(")")
    limpio = re.sub(r"[^\d,.\-]", "", texto)
    if not limpio or limpio in {"-", ",", "."}:
        return 0.0

    negativo = negativo or limpio.startswith("-") or limpio.endswith("-")
    limpio = limpio.replace("-", "")
    if not limpio:
        return 0.0

    ultimo = max(limpio.rfind(","), limpio.rfind("."))
    if ultimo == -1:
        numero = limpio
    elif len(limpio) - ultimo - 1 in (1, 2):
        entero = re.sub(r"[,.]", "", limpio[:ultimo]) or "0"
        decimales = re.sub(r"[,.]", "", limpio[ultimo + 1:])
        numero = f"{entero}.{decimales}"
    else:
        numero = re.sub(r"[,.]", "", limpio)

    try:
        res = float(numero) if numero else 0.0
        return -res if negativo else res
    except ValueError:
        return 0.0


def _to_iso_date(value: Any) -> date | None:
    """Parsea fechas en ISO, YYYY-MM-DD HH:MM:SS, DD/MM/YYYY o RFC 2822."""
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    txt = str(value).strip()
    try:
        return date.fromisoformat(txt[:10])
    except ValueError:
        pass
    for fmt in ("%d/%m/%Y", "%Y/%m/%d", "%d-%m-%Y"):
        try:
            return datetime.strptime(txt[:10], fmt).date()
        except ValueError:
            continue
    parsed = parse_email_date(txt)
    return parsed.date() if parsed else None


# ==================== SERVICIO DE INFORME ====================


class ExternalGlosasReportService:
    """Orquesta la consulta, normalización y agregación de glosas desde una tabla externa."""

    def __init__(
        self,
        schema: ExternalTableSchema | None = None,
        custom_query_fn: Callable[[str, str, str | None], list[dict[str, Any]]] | None = None,
    ):
        self.schema = schema or ExternalTableSchema()
        self.custom_query_fn = custom_query_fn

    def set_query_provider(
        self,
        query_fn: Callable[[str, str, str | None], list[dict[str, Any]]] | None,
    ) -> None:
        """Registra una función proveedora de registros SQL/API (desde, hasta, entidad)."""
        self.custom_query_fn = query_fn

    def build_report_from_records(
        self,
        records: list[dict[str, Any]],
        periodicity: str,
        fecha_desde: str,
        fecha_hasta: str,
        entidad_filter: str | None = None,
        is_preview_data: bool = False,
        source_note: str = "",
        breakdowns: dict[str, list[dict[str, Any]]] | None = None,
    ) -> ExternalGlosasReportData:
        """Normaliza registros crudos aplicando mapeo de columnas, filtros y agregaciones."""
        d_desde = _to_iso_date(fecha_desde)
        d_hasta = _to_iso_date(fecha_hasta)
        entidad_clean = str(entidad_filter or "").strip().upper()
        filter_entidad = entidad_clean not in ("", "TODAS", "ALL", "NONE")

        normalized: list[dict[str, Any]] = []
        for idx, row in enumerate(records or [], start=1):
            raw_fecha = self.schema.resolve_value(row, "fecha_glosa", "")
            fecha_obj = _to_iso_date(raw_fecha)
            if d_desde and fecha_obj and fecha_obj < d_desde:
                continue
            if d_hasta and fecha_obj and fecha_obj > d_hasta:
                continue

            entidad_val = str(self.schema.resolve_value(row, "entidad_eps", "SIN ENTIDAD")).strip().upper()
            if filter_entidad and entidad_clean not in entidad_val:
                continue

            val_facturado = _to_float(self.schema.resolve_value(row, "valor_facturado", 0.0))
            val_glosado = _to_float(self.schema.resolve_value(row, "valor_glosado", 0.0))
            estado_val = str(self.schema.resolve_value(row, "estado_glosa", "PENDIENTE")).strip().upper() or "PENDIENTE"

            normalized.append(
                {
                    "id_glosa": str(self.schema.resolve_value(row, "id_glosa", idx)),
                    "fecha_glosa": fecha_obj.isoformat() if fecha_obj else str(raw_fecha or ""),
                    "numero_factura": str(self.schema.resolve_value(row, "numero_factura", "")).strip(),
                    "entidad_eps": entidad_val,
                    "codigo_glosa": str(self.schema.resolve_value(row, "codigo_glosa", "")).strip(),
                    "concepto_glosa": str(self.schema.resolve_value(row, "concepto_glosa", "")).strip(),
                    "servicio_glosado": str(self.schema.resolve_value(row, "servicio_glosado", "")).strip(),
                    "centro_costo": str(self.schema.resolve_value(row, "centro_costo", "")).strip(),
                    "observacion_general": str(self.schema.resolve_value(row, "observacion_general", "")).strip(),
                    "estado_glosa": estado_val,
                    "usuario_auditor": str(self.schema.resolve_value(row, "usuario_auditor", "")).strip(),
                    "valor_facturado": round(val_facturado, 2),
                    "valor_glosado": round(val_glosado, 2),
                }
            )

        # Ordenar cronológicamente descendente
        normalized.sort(key=lambda r: (r["fecha_glosa"], r["id_glosa"]), reverse=True)

        total_glosas = len(normalized)
        facturas_unicas: set[str] = set()
        total_facturado_raw = 0.0
        for r in normalized:
            fac = r["numero_factura"]
            if fac:
                if fac not in facturas_unicas:
                    facturas_unicas.add(fac)
                    total_facturado_raw += r["valor_facturado"]
            else:
                total_facturado_raw += r["valor_facturado"]

        total_facturas = len(facturas_unicas)
        total_facturado = round(total_facturado_raw, 2)
        total_glosado = round(sum(r["valor_glosado"] for r in normalized), 2)
        pct_glosado = round((total_glosado / total_facturado * 100.0), 2) if total_facturado > 0 else 0.0
        promedio_glosa = round((total_glosado / total_glosas), 2) if total_glosas > 0 else 0.0

        # Agrupar por entidad (deduplicando valor facturado por factura dentro de cada entidad)
        entidad_map: dict[str, dict[str, Any]] = {}
        estado_map: dict[str, dict[str, Any]] = {}
        for r in normalized:
            ent = r["entidad_eps"] or "SIN ENTIDAD"
            if ent not in entidad_map:
                entidad_map[ent] = {
                    "entidad": ent,
                    "cantidad_glosas": 0,
                    "_facturas": set(),
                    "valor_facturado": 0.0,
                    "valor_glosado": 0.0,
                }
            e_item = entidad_map[ent]
            e_item["cantidad_glosas"] += 1
            fac = r["numero_factura"]
            if fac:
                if fac not in e_item["_facturas"]:
                    e_item["_facturas"].add(fac)
                    e_item["valor_facturado"] += r["valor_facturado"]
            else:
                e_item["valor_facturado"] += r["valor_facturado"]
            e_item["valor_glosado"] += r["valor_glosado"]

            est = r["estado_glosa"]
            if est not in estado_map:
                estado_map[est] = {
                    "estado": est,
                    "cantidad_glosas": 0,
                    "valor_glosado": 0.0,
                }
            estado_map[est]["cantidad_glosas"] += 1
            estado_map[est]["valor_glosado"] += r["valor_glosado"]

        resumen_por_entidad: list[dict[str, Any]] = []
        for e_item in entidad_map.values():
            cant = e_item["cantidad_glosas"]
            resumen_por_entidad.append(
                {
                    "entidad": e_item["entidad"],
                    "cantidad_glosas": cant,
                    "facturas_unicas": len(e_item["_facturas"]),
                    "valor_facturado": round(e_item["valor_facturado"], 2),
                    "valor_glosado": round(e_item["valor_glosado"], 2),
                    "participacion_pct": round((cant / total_glosas * 100.0), 1) if total_glosas > 0 else 0.0,
                }
            )
        resumen_por_entidad.sort(key=lambda x: x["cantidad_glosas"], reverse=True)

        resumen_por_estado: list[dict[str, Any]] = []
        for st_item in estado_map.values():
            cant = st_item["cantidad_glosas"]
            resumen_por_estado.append(
                {
                    "estado": st_item["estado"],
                    "cantidad_glosas": cant,
                    "valor_glosado": round(st_item["valor_glosado"], 2),
                    "participacion_pct": round((cant / total_glosas * 100.0), 1) if total_glosas > 0 else 0.0,
                }
            )
        resumen_por_estado.sort(key=lambda x: x["cantidad_glosas"], reverse=True)

        resumen_por_servicio, resumen_por_facturador, resumen_top_conceptos = (
            self._build_breakdowns(normalized, breakdowns)
        )

        period_key = str(periodicity or "MENSUAL").strip().upper()
        return ExternalGlosasReportData(
            periodicity=period_key,
            period_label=PeriodRangeCalculator.get_period_label(period_key),
            fecha_desde=d_desde.isoformat() if d_desde else str(fecha_desde),
            fecha_hasta=d_hasta.isoformat() if d_hasta else str(fecha_hasta),
            generated_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            database_name=self.schema.database_name,
            table_name=self.schema.table_name,
            total_glosas=total_glosas,
            total_facturas=total_facturas,
            valor_total_facturado=total_facturado,
            valor_total_glosado=total_glosado,
            porcentaje_glosado=pct_glosado,
            promedio_por_glosa=promedio_glosa,
            resumen_por_entidad=resumen_por_entidad,
            resumen_por_estado=resumen_por_estado,
            resumen_por_servicio=resumen_por_servicio,
            resumen_por_facturador=resumen_por_facturador,
            resumen_top_conceptos=resumen_top_conceptos,
            registros=normalized,
            is_preview_data=is_preview_data,
            source_note=source_note,
        )

    @staticmethod
    def _add_value_pct(rows: list[dict[str, Any]], value_key: str = "total_valor_glosado") -> list[dict[str, Any]]:
        """Calcula participación porcentual sobre el total glosado del agrupado."""
        total_val = sum(float(r.get(value_key) or 0.0) for r in rows)
        for r in rows:
            val = float(r.get(value_key) or 0.0)
            r[value_key] = round(val, 2)
            r["participacion_pct"] = round((val / total_val * 100.0), 1) if total_val > 0 else 0.0
        rows.sort(key=lambda x: x.get(value_key, 0.0), reverse=True)
        return rows

    def _build_breakdowns(
        self,
        normalized: list[dict[str, Any]],
        breakdowns: dict[str, list[dict[str, Any]]] | None,
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
        """Normaliza los 3 desgloses (SQL o agregados en memoria en modo preview/test)."""
        if breakdowns is not None:
            por_servicio = [
                {
                    "servicio_glosado": str(r.get("servicio_glosado") or "SIN SERVICIO ASOCIADO").strip(),
                    "cantidad_glosas": int(r.get("cantidad_glosas") or 0),
                    "facturas_afectadas": int(r.get("facturas_afectadas") or 0),
                    "total_valor_glosado": _to_float(r.get("total_valor_glosado")),
                }
                for r in breakdowns.get("por_servicio", [])
            ]
            por_facturador = [
                {
                    "usuario_facturador": str(r.get("usuario_facturador") or "SIN USUARIO").strip(),
                    "nombre_facturador": str(r.get("nombre_facturador") or "SIN NOMBRE").strip(),
                    "cantidad_items_glosados": int(r.get("cantidad_items_glosados") or 0),
                    "facturas_glosadas": int(r.get("facturas_glosadas") or 0),
                    "total_valor_glosado": _to_float(r.get("total_valor_glosado")),
                }
                for r in breakdowns.get("por_facturador", [])
            ]
            top_conceptos = [
                {
                    "codigo_concepto": str(r.get("codigo_concepto") or "").strip(),
                    "nombre_concepto": str(r.get("nombre_concepto") or "").strip(),
                    "clase_objecion": str(r.get("clase_objecion") or "Ninguno").strip(),
                    "cantidad_glosas": int(r.get("cantidad_glosas") or 0),
                    "facturas_afectadas": int(r.get("facturas_afectadas") or 0),
                    "total_valor_glosado": _to_float(r.get("total_valor_glosado")),
                }
                for r in breakdowns.get("top_conceptos", [])
            ]
            return (
                self._add_value_pct(por_servicio),
                self._add_value_pct(por_facturador),
                self._add_value_pct(top_conceptos),
            )

        # Fallback en memoria desde registros normalizados
        srv_map: dict[str, dict[str, Any]] = {}
        fac_map: dict[str, dict[str, Any]] = {}
        con_map: dict[str, dict[str, Any]] = {}
        for r in normalized:
            fac_num = r.get("numero_factura") or ""
            val_g = float(r.get("valor_glosado") or 0.0)

            srv_name = r.get("servicio_glosado") or "SIN SERVICIO ASOCIADO"
            if srv_name not in srv_map:
                srv_map[srv_name] = {"servicio_glosado": srv_name, "cantidad_glosas": 0, "_facs": set(), "total_valor_glosado": 0.0}
            srv_map[srv_name]["cantidad_glosas"] += 1
            if fac_num:
                srv_map[srv_name]["_facs"].add(fac_num)
            srv_map[srv_name]["total_valor_glosado"] += val_g

            usr = r.get("usuario_auditor") or "SISTEMA"
            if usr not in fac_map:
                fac_map[usr] = {"usuario_facturador": usr, "nombre_facturador": usr, "cantidad_items_glosados": 0, "_facs": set(), "total_valor_glosado": 0.0}
            fac_map[usr]["cantidad_items_glosados"] += 1
            if fac_num:
                fac_map[usr]["_facs"].add(fac_num)
            fac_map[usr]["total_valor_glosado"] += val_g

            cod = r.get("codigo_glosa") or "N/A"
            if cod not in con_map:
                con_map[cod] = {
                    "codigo_concepto": cod,
                    "nombre_concepto": r.get("concepto_glosa") or "",
                    "clase_objecion": "Ninguno",
                    "cantidad_glosas": 0,
                    "_facs": set(),
                    "total_valor_glosado": 0.0,
                }
            con_map[cod]["cantidad_glosas"] += 1
            if fac_num:
                con_map[cod]["_facs"].add(fac_num)
            con_map[cod]["total_valor_glosado"] += val_g

        por_servicio = [
            {
                "servicio_glosado": v["servicio_glosado"],
                "cantidad_glosas": v["cantidad_glosas"],
                "facturas_afectadas": len(v["_facs"]),
                "total_valor_glosado": v["total_valor_glosado"],
            }
            for v in srv_map.values()
        ]
        por_facturador = [
            {
                "usuario_facturador": v["usuario_facturador"],
                "nombre_facturador": v["nombre_facturador"],
                "cantidad_items_glosados": v["cantidad_items_glosados"],
                "facturas_glosadas": len(v["_facs"]),
                "total_valor_glosado": v["total_valor_glosado"],
            }
            for v in fac_map.values()
        ]
        top_conceptos = [
            {
                "codigo_concepto": v["codigo_concepto"],
                "nombre_concepto": v["nombre_concepto"],
                "clase_objecion": v["clase_objecion"],
                "cantidad_glosas": v["cantidad_glosas"],
                "facturas_afectadas": len(v["_facs"]),
                "total_valor_glosado": v["total_valor_glosado"],
            }
            for v in con_map.values()
        ]
        return (
            self._add_value_pct(por_servicio),
            self._add_value_pct(por_facturador),
            self._add_value_pct(top_conceptos),
        )

    def fetch_report(
        self,
        periodicity: str = "MENSUAL",
        fecha_desde: str | None = None,
        fecha_hasta: str | None = None,
        entidad_filter: str | None = None,
        mode: str = "rolling",
    ) -> ExternalGlosasReportData:
        """
        Obtiene los datos del periodo indicado desde el proveedor externo (si está conectado)
        o genera datos de previsualización consistentes si el origen SQL no está disponible.
        """
        period_key = str(periodicity or "MENSUAL").strip().upper()
        calc_desde, calc_hasta = PeriodRangeCalculator.calculate_range(period_key, mode=mode)

        f_desde = (_to_iso_date(fecha_desde) or calc_desde).isoformat()
        f_hasta = (_to_iso_date(fecha_hasta) or calc_hasta).isoformat()

        if self.custom_query_fn is not None:
            try:
                raw_records = self.custom_query_fn(f_desde, f_hasta, entidad_filter)
                breakdowns = None
                fetch_bd = getattr(self.custom_query_fn, "fetch_breakdowns", None)
                if callable(fetch_bd):
                    try:
                        breakdowns = fetch_bd(f_desde, f_hasta, entidad_filter)
                    except Exception as bd_ex:
                        logger.warning("No se pudieron cargar desgloses SQL adicionales: %s", bd_ex)

                note = (
                    "Conectado a SQL Server"
                    if raw_records
                    else "Conectado a SQL Server (0 registros encontrados para este rango de fechas)"
                )
                return self.build_report_from_records(
                    records=raw_records,
                    periodicity=period_key,
                    fecha_desde=f_desde,
                    fecha_hasta=f_hasta,
                    entidad_filter=entidad_filter,
                    is_preview_data=False,
                    source_note=note,
                    breakdowns=breakdowns,
                )
            except Exception as ex:
                logger.warning("Fallo consulta SQL externa, usando fallback de previsualizacion: %s", ex)
                preview_records = self._generate_preview_records(f_desde, f_hasta)
                return self.build_report_from_records(
                    records=preview_records,
                    periodicity=period_key,
                    fecha_desde=f_desde,
                    fecha_hasta=f_hasta,
                    entidad_filter=entidad_filter,
                    is_preview_data=True,
                    source_note=f"Modo previsualizacion (SQL no disponible: {ex})",
                )

        # Datos de previsualización mientras se configura proveedor externo
        preview_records = self._generate_preview_records(f_desde, f_hasta)
        return self.build_report_from_records(
            records=preview_records,
            periodicity=period_key,
            fecha_desde=f_desde,
            fecha_hasta=f_hasta,
            entidad_filter=entidad_filter,
            is_preview_data=True,
            source_note="Modo previsualizacion (sin proveedor SQL conectado).",
        )

    def _generate_preview_records(self, fecha_desde: str, fecha_hasta: str) -> list[dict[str, Any]]:
        """Genera un lote representativo dentro del rango consultado para previsualización y testing."""
        d_start = _to_iso_date(fecha_desde) or (date.today() - timedelta(days=30))
        d_end = _to_iso_date(fecha_hasta) or date.today()
        span = max((d_end - d_start).days, 1)

        samples = [
            ("SANITAS", "GL-1001", "FC000048102", "TA0601", "Tarifa pactada superior a contrato", "OBJETADA", 2450000.0, 420000.0),
            ("SANITAS", "GL-1002", "FC000048109", "SO4801", "Soporte de historia clinica incompleto", "EN REVISION", 1890000.0, 315000.0),
            ("MUTUALSER", "GL-1003", "FC000048115", "FA0203", "Falta autorizacion de procedimiento", "PENDIENTE", 3200000.0, 680000.0),
            ("COOSALUD", "GL-1004", "FC000048122", "AU0101", "Autorizacion vencida al egreso", "CONTESTADA", 1420000.0, 290000.0),
            ("PREVISORA", "GL-1005", "FC000048130", "TA0302", "Diferencia en cobro de insumos", "PENDIENTE", 980000.0, 175000.0),
            ("SANITAS", "GL-1006", "FC000048144", "SO2104", "Falta firma de auditoria medica", "ACEPTADA", 4150000.0, 510000.0),
            ("MUTUALSER", "GL-1007", "FC000048151", "FA0105", "Factura radicada fuera de termino", "OBJETADA", 2100000.0, 445000.0),
            ("COOSALUD", "GL-1008", "FC000048166", "DE0102", "Devolucion por inconsistencia en RIPS", "PENDIENTE", 1650000.0, 380000.0),
        ]

        records: list[dict[str, Any]] = []
        total = len(samples)
        for idx, (eps, id_g, fact, cod, conc, est, v_fac, v_glo) in enumerate(samples):
            offset_days = int(round((idx / max(total - 1, 1)) * span))
            rec_date = min(d_start + timedelta(days=offset_days), d_end)
            records.append(
                {
                    self.schema.column_mapping["id_glosa"]: id_g,
                    self.schema.column_mapping["fecha_glosa"]: rec_date.isoformat(),
                    self.schema.column_mapping["numero_factura"]: fact,
                    self.schema.column_mapping["entidad_eps"]: eps,
                    self.schema.column_mapping["codigo_glosa"]: cod,
                    self.schema.column_mapping["concepto_glosa"]: conc,
                    self.schema.column_mapping["estado_glosa"]: est,
                    self.schema.column_mapping["usuario_auditor"]: "AUDITORIA_SISTEMA",
                    self.schema.column_mapping["valor_facturado"]: v_fac,
                    self.schema.column_mapping["valor_glosado"]: v_glo,
                }
            )
        return records


# ==================== MOTOR DE EXPORTACIÓN (EXCEL Y PDF) ====================


def _format_money_cop(val: float | int | None) -> str:
    """Formatea valores monetarios en pesos colombianos sin decimales innecesarios."""
    try:
        return f"${float(val or 0.0):,.0f}".replace(",", ".")
    except Exception:
        return "$0"


def _pdf_escape(text: str) -> bytes:
    """Escapa paréntesis/barras y codifica a WinAnsi (cp1252) para PDF Type1 estándar."""
    safe = str(text or "").replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
    return safe.encode("cp1252", errors="replace")


class _NativePdfBuilder:
    """Generador ligero de documentos PDF 1.4 multipágina con tablas e identidad visual."""

    PAGE_W = 792.0  # Carta Horizontal (Landscape) para máxima legibilidad en tablas
    PAGE_H = 612.0
    MARGIN_X = 36.0
    MARGIN_BOTTOM = 36.0

    def __init__(self):
        self._pages: list[list[bytes]] = []
        self._current: list[bytes] = []
        self.y = self.PAGE_H - 36.0
        self.new_page()

    def new_page(self) -> None:
        self._current = []
        self._pages.append(self._current)
        self.y = self.PAGE_H - 36.0

    def rect(
        self,
        x: float,
        y: float,
        w: float,
        h: float,
        fill_rgb: tuple[float, float, float] | None = None,
        stroke_rgb: tuple[float, float, float] | None = None,
        line_width: float = 0.6,
    ) -> None:
        cmds: list[bytes] = []
        if fill_rgb is not None:
            cmds.append(f"{fill_rgb[0]:.3f} {fill_rgb[1]:.3f} {fill_rgb[2]:.3f} rg".encode("ascii"))
        if stroke_rgb is not None:
            cmds.append(f"{line_width:.2f} w {stroke_rgb[0]:.3f} {stroke_rgb[1]:.3f} {stroke_rgb[2]:.3f} RG".encode("ascii"))
        cmds.append(f"{x:.2f} {y:.2f} {w:.2f} {h:.2f} re".encode("ascii"))
        if fill_rgb is not None and stroke_rgb is not None:
            cmds.append(b"B")
        elif fill_rgb is not None:
            cmds.append(b"f")
        else:
            cmds.append(b"S")
        self._current.append(b" ".join(cmds))

    def text(
        self,
        x: float,
        y: float,
        txt: str,
        size: float = 9.0,
        bold: bool = False,
        rgb: tuple[float, float, float] = (0.12, 0.16, 0.23),
        align: str = "left",
        max_chars: int | None = None,
    ) -> None:
        s = str(txt or "")
        if max_chars and len(s) > max_chars:
            s = s[: max(max_chars - 3, 1)] + "..."

        font_key = "F2" if bold else "F1"
        draw_x = x
        if align == "right":
            approx_w = len(s) * size * (0.52 if bold else 0.48)
            draw_x = x - approx_w
        elif align == "center":
            approx_w = len(s) * size * (0.52 if bold else 0.48)
            draw_x = x - approx_w / 2.0

        escaped = _pdf_escape(s)
        cmd = (
            b"BT "
            + f"/{font_key} {size:.1f} Tf {rgb[0]:.3f} {rgb[1]:.3f} {rgb[2]:.3f} rg "
            f"1 0 0 1 {draw_x:.2f} {y:.2f} Tm (".encode("ascii")
            + escaped
            + b") Tj ET"
        )
        self._current.append(cmd)

    def build_bytes(self, title_meta: str = "Informe de Glosas - Glosaap") -> bytes:
        total_pages = len(self._pages)
        for idx, page_cmds in enumerate(self._pages, start=1):
            footer_left = f"Glosaap - Clinica La Concepcion | Generado: {datetime.now().strftime('%Y-%m-%d %H:%M')}"
            footer_right = f"Pagina {idx} de {total_pages}"
            page_cmds.append(b"0.78 0.82 0.88 RG 0.5 w 36.00 28.00 m 756.00 28.00 l S")
            escaped_l = _pdf_escape(footer_left)
            escaped_r = _pdf_escape(footer_right)
            page_cmds.append(
                b"BT /F1 7.5 Tf 0.40 0.45 0.52 rg 1 0 0 1 36.00 17.00 Tm (" + escaped_l + b") Tj ET"
            )
            approx_r = len(footer_right) * 7.5 * 0.48
            page_cmds.append(
                b"BT /F1 7.5 Tf 0.40 0.45 0.52 rg 1 0 0 1 "
                + f"{756.0 - approx_r:.2f} 17.00 Tm (".encode("ascii")
                + escaped_r
                + b") Tj ET"
            )

        objects: list[bytes] = []
        # 1: Catalog, 2: Pages, 3: F1 Helvetica, 4: F2 Helvetica-Bold
        page_obj_nums: list[int] = []
        next_obj_num = 5
        page_pairs: list[tuple[int, int, bytes]] = []
        for page_cmds in self._pages:
            stream_data = b"\n".join(page_cmds)
            page_id = next_obj_num
            content_id = next_obj_num + 1
            next_obj_num += 2
            page_obj_nums.append(page_id)
            page_pairs.append((page_id, content_id, stream_data))

        kids_ref = " ".join(f"{pid} 0 R" for pid in page_obj_nums)
        objects.append(b"<< /Type /Catalog /Pages 2 0 R >>")
        objects.append(f"<< /Type /Pages /Kids [ {kids_ref} ] /Count {len(page_obj_nums)} >>".encode("ascii"))
        objects.append(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>")
        objects.append(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold /Encoding /WinAnsiEncoding >>")

        for _page_id, content_id, stream_data in page_pairs:
            page_dict = (
                f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 {self.PAGE_W:.0f} {self.PAGE_H:.0f}] "
                f"/Resources << /Font << /F1 3 0 R /F2 4 0 R >> >> /Contents {content_id} 0 R >>"
            ).encode("ascii")
            content_obj = (
                f"<< /Length {len(stream_data)} >>\nstream\n".encode("ascii")
                + stream_data
                + b"\nendstream"
            )
            objects.append(page_dict)
            objects.append(content_obj)

        out = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
        offsets: list[int] = [0]
        for idx, obj_body in enumerate(objects, start=1):
            offsets.append(len(out))
            out.extend(f"{idx} 0 obj\n".encode("ascii"))
            out.extend(obj_body)
            out.extend(b"\nendobj\n")

        xref_offset = len(out)
        out.extend(f"xref\n0 {len(objects) + 1}\n".encode("ascii"))
        out.extend(b"0000000000 65535 f \n")
        for off in offsets[1:]:
            out.extend(f"{off:010d} 00000 n \n".encode("ascii"))

        out.extend(
            (
                f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\n"
                f"startxref\n{xref_offset}\n%%EOF\n"
            ).encode("ascii")
        )
        return bytes(out)


class GlosasReportExporter:
    """Exporta ExternalGlosasReportData hacia archivos Excel (.xlsx) y PDF (.pdf)."""

    def __init__(self, output_dir: str | None = None):
        if output_dir:
            self.output_dir = str(output_dir)
        else:
            default_dir = get_output_dir("reportes_glosas")
            if not ensure_dir(default_dir):
                default_dir = str(TEMP_DIR / "reportes_glosas")
                ensure_dir(default_dir)
            self.output_dir = default_dir
        ensure_dir(self.output_dir)

    def _build_default_filename(self, report: ExternalGlosasReportData, ext: str) -> str:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        period = str(report.periodicity or "INFORME").upper()
        name = f"Informe_Glosas_{period}_{report.fecha_desde}_a_{report.fecha_hasta}_{ts}.{ext}"
        return os.path.join(self.output_dir, name)

    # -------------------- EXPORTACIÓN EXCEL --------------------

    def export_to_excel(
        self,
        report: ExternalGlosasReportData,
        output_path: str | None = None,
    ) -> str:
        """Genera libro Excel con hojas 'Resumen del Informe' y 'Detalle de Glosas'."""
        target_path = output_path or self._build_default_filename(report, "xlsx")
        ensure_dir(os.path.dirname(os.path.abspath(target_path)))

        wb = openpyxl.Workbook()
        ws_res = wb.active
        if ws_res is None:
            ws_res = wb.create_sheet("Resumen del Informe")
        else:
            ws_res.title = "Resumen del Informe"

        navy_fill = PatternFill("solid", fgColor="1E3A8A")
        sub_fill = PatternFill("solid", fgColor="DBEAFE")
        zebra_fill = PatternFill("solid", fgColor="F8FAFC")
        total_fill = PatternFill("solid", fgColor="E2E8F0")

        title_font = Font(name="Calibri", size=14, bold=True, color="FFFFFF")
        header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
        section_font = Font(name="Calibri", size=11, bold=True, color="1E3A8A")
        bold_font = Font(name="Calibri", size=10, bold=True, color="0F172A")
        body_font = Font(name="Calibri", size=10, color="1E293B")

        thin_side = Side(style="thin", color="CBD5E1")
        border = Border(left=thin_side, right=thin_side, top=thin_side, bottom=thin_side)

        # Encabezado institucional
        ws_res.merge_cells("A1:F1")
        ws_res["A1"] = "CLINICA LA CONCEPCION - INFORME DE GLOSAS (BD EXTERNA)"
        ws_res["A1"].font = title_font
        ws_res["A1"].fill = navy_fill
        ws_res["A1"].alignment = Alignment(horizontal="left", vertical="center", indent=1)
        ws_res.row_dimensions[1].height = 28

        meta_rows = [
            ("Periodicidad del Corte:", report.period_label, "Fecha de Generacion:", report.generated_at),
            ("Rango Evaluado:", f"{report.fecha_desde} al {report.fecha_hasta}", "Origen de Datos:", f"{report.database_name}.{report.table_name}"),
            ("Modo de Datos:", "Previsualizacion (pendiente tabla final)" if report.is_preview_data else "Base de Datos Externa", "", ""),
        ]
        for r_idx, (l1, v1, l2, v2) in enumerate(meta_rows, start=2):
            ws_res.cell(r_idx, 1, l1).font = bold_font
            ws_res.cell(r_idx, 2, v1).font = body_font
            ws_res.cell(r_idx, 4, l2).font = bold_font
            ws_res.cell(r_idx, 5, v2).font = body_font

        # Bloque KPI
        ws_res["A6"] = "INDICADORES PRINCIPALES DEL PERIODO"
        ws_res["A6"].font = section_font
        kpi_headers = ["Cantidad Total de Glosas", "Facturas Unicas", "Valor Total Facturado", "Valor Total Glosado", "% Glosado", "Promedio por Glosa"]
        kpi_values = [
            report.total_glosas,
            report.total_facturas,
            report.valor_total_facturado,
            report.valor_total_glosado,
            report.porcentaje_glosado / 100.0,
            report.promedio_por_glosa,
        ]
        for c_idx, (h, val) in enumerate(zip(kpi_headers, kpi_values, strict=True), start=1):
            c_h = ws_res.cell(7, c_idx, h)
            c_h.font = bold_font
            c_h.fill = sub_fill
            c_h.alignment = Alignment(horizontal="center")
            c_h.border = border

            c_v = ws_res.cell(8, c_idx, val)
            c_v.font = bold_font
            c_v.alignment = Alignment(horizontal="center")
            c_v.border = border
            if c_idx in (3, 4, 6):
                c_v.number_format = "$#,##0"
            elif c_idx == 5:
                c_v.number_format = "0.0%"

        # Tabla 1: Resumen por Entidad / EPS
        row_cursor = 10
        ws_res.cell(row_cursor, 1, "DISTRIBUCION POR ENTIDAD / EPS").font = section_font
        row_cursor += 1
        ent_cols = ["Entidad / EPS", "Cantidad Glosas", "Facturas Unicas", "Valor Facturado", "Valor Glosado", "Participacion %"]
        for c_idx, col_name in enumerate(ent_cols, start=1):
            cell = ws_res.cell(row_cursor, c_idx, col_name)
            cell.font = header_font
            cell.fill = navy_fill
            cell.alignment = Alignment(horizontal="center")
            cell.border = border
        row_cursor += 1

        for idx_item, item in enumerate(report.resumen_por_entidad):
            fill = zebra_fill if idx_item % 2 else PatternFill(fill_type=None)
            vals = [
                item["entidad"],
                item["cantidad_glosas"],
                item["facturas_unicas"],
                item["valor_facturado"],
                item["valor_glosado"],
                item["participacion_pct"] / 100.0,
            ]
            for c_idx, val in enumerate(vals, start=1):
                c = ws_res.cell(row_cursor, c_idx, val)
                c.font = body_font
                c.fill = fill
                c.border = border
                if c_idx in (4, 5):
                    c.number_format = "$#,##0"
                    c.alignment = Alignment(horizontal="right")
                elif c_idx == 6:
                    c.number_format = "0.0%"
                    c.alignment = Alignment(horizontal="right")
                elif c_idx in (2, 3):
                    c.alignment = Alignment(horizontal="center")
            row_cursor += 1

        # Fila Total Entidades
        tot_vals = [
            "TOTAL GENERAL",
            report.total_glosas,
            report.total_facturas,
            report.valor_total_facturado,
            report.valor_total_glosado,
            1.0 if report.total_glosas > 0 else 0.0,
        ]
        for c_idx, val in enumerate(tot_vals, start=1):
            c = ws_res.cell(row_cursor, c_idx, val)
            c.font = bold_font
            c.fill = total_fill
            c.border = border
            if c_idx in (4, 5):
                c.number_format = "$#,##0"
                c.alignment = Alignment(horizontal="right")
            elif c_idx == 6:
                c.number_format = "0.0%"
                c.alignment = Alignment(horizontal="right")
            elif c_idx in (2, 3):
                c.alignment = Alignment(horizontal="center")

        # Tabla 2: Resumen por Estado
        row_cursor += 2
        ws_res.cell(row_cursor, 1, "RESUMEN POR ESTADO DE GLOSA").font = section_font
        row_cursor += 1
        est_cols = ["Estado", "Cantidad Glosas", "Valor Glosado", "Participacion %"]
        for c_idx, col_name in enumerate(est_cols, start=1):
            cell = ws_res.cell(row_cursor, c_idx, col_name)
            cell.font = header_font
            cell.fill = navy_fill
            cell.alignment = Alignment(horizontal="center")
            cell.border = border
        row_cursor += 1

        for idx_st, st in enumerate(report.resumen_por_estado):
            fill = zebra_fill if idx_st % 2 else PatternFill(fill_type=None)
            vals = [st["estado"], st["cantidad_glosas"], st["valor_glosado"], st["participacion_pct"] / 100.0]
            for c_idx, val in enumerate(vals, start=1):
                c = ws_res.cell(row_cursor, c_idx, val)
                c.font = body_font
                c.fill = fill
                c.border = border
                if c_idx == 3:
                    c.number_format = "$#,##0"
                    c.alignment = Alignment(horizontal="right")
                elif c_idx == 4:
                    c.number_format = "0.0%"
                    c.alignment = Alignment(horizontal="right")
                elif c_idx == 2:
                    c.alignment = Alignment(horizontal="center")
            row_cursor += 1

        res_widths = [26, 22, 18, 22, 22, 18]
        for c_idx, w in enumerate(res_widths, start=1):
            ws_res.column_dimensions[get_column_letter(c_idx)].width = w

        # Helper compartido para escribir hojas de agrupación (Servicio / Facturador / Conceptos)
        def write_breakdown_sheet(
            sheet_name: str,
            headers: list[str],
            rows_data: list[list[Any]],
            widths: list[int],
            money_col: int,
            pct_col: int,
            center_cols: tuple[int, ...],
            total_row: list[Any] | None = None,
        ) -> None:
            ws = wb.create_sheet(sheet_name)
            for c_idx, h in enumerate(headers, start=1):
                cell = ws.cell(1, c_idx, h)
                cell.font = header_font
                cell.fill = navy_fill
                cell.alignment = Alignment(horizontal="center", vertical="center")
                cell.border = border
            ws.row_dimensions[1].height = 24

            for r_idx, row_vals in enumerate(rows_data, start=2):
                fill = zebra_fill if r_idx % 2 else PatternFill(fill_type=None)
                for c_idx, val in enumerate(row_vals, start=1):
                    c = ws.cell(r_idx, c_idx, val)
                    c.font = body_font
                    c.fill = fill
                    c.border = border
                    if c_idx == money_col:
                        c.number_format = "$#,##0"
                        c.alignment = Alignment(horizontal="right")
                    elif c_idx == pct_col:
                        c.number_format = "0.0%"
                        c.alignment = Alignment(horizontal="right")
                    elif c_idx in center_cols:
                        c.alignment = Alignment(horizontal="center")

            if total_row:
                tot_r = len(rows_data) + 2
                for c_idx, val in enumerate(total_row, start=1):
                    c = ws.cell(tot_r, c_idx, val)
                    c.font = bold_font
                    c.fill = total_fill
                    c.border = border
                    if c_idx == money_col:
                        c.number_format = "$#,##0"
                        c.alignment = Alignment(horizontal="right")
                    elif c_idx == pct_col:
                        c.number_format = "0.0%"
                        c.alignment = Alignment(horizontal="right")
                    elif c_idx in center_cols:
                        c.alignment = Alignment(horizontal="center")

            for c_idx, w in enumerate(widths, start=1):
                ws.column_dimensions[get_column_letter(c_idx)].width = w
            ws.freeze_panes = "A2"
            if rows_data:
                last_col = get_column_letter(len(headers))
                ws.auto_filter.ref = f"A1:{last_col}{len(rows_data) + 1}"

        # Hoja 2: Glosas por Servicio
        srv_rows = [
            [
                s["servicio_glosado"],
                s["cantidad_glosas"],
                s["facturas_afectadas"],
                s["total_valor_glosado"],
                s["participacion_pct"] / 100.0,
            ]
            for s in report.resumen_por_servicio
        ]
        srv_tot_cant = sum(s["cantidad_glosas"] for s in report.resumen_por_servicio)
        srv_tot_val = round(sum(s["total_valor_glosado"] for s in report.resumen_por_servicio), 2)
        write_breakdown_sheet(
            sheet_name="Glosas por Servicio",
            headers=["Servicio Glosado", "Cantidad Glosas", "Facturas Afectadas", "Total Valor Glosado", "Participacion %"],
            rows_data=srv_rows,
            widths=[48, 18, 20, 22, 16],
            money_col=4,
            pct_col=5,
            center_cols=(2, 3),
            total_row=["TOTAL", srv_tot_cant, "", srv_tot_val, 1.0 if srv_tot_val > 0 else 0.0],
        )

        # Hoja 3: Glosas por Facturador
        fac_rows = [
            [
                f["usuario_facturador"],
                f["nombre_facturador"],
                f["cantidad_items_glosados"],
                f["facturas_glosadas"],
                f["total_valor_glosado"],
                f["participacion_pct"] / 100.0,
            ]
            for f in report.resumen_por_facturador
        ]
        fac_tot_items = sum(f["cantidad_items_glosados"] for f in report.resumen_por_facturador)
        fac_tot_val = round(sum(f["total_valor_glosado"] for f in report.resumen_por_facturador), 2)
        write_breakdown_sheet(
            sheet_name="Glosas por Facturador",
            headers=["Usuario Facturador", "Nombre Facturador", "Items Glosados", "Facturas Glosadas", "Total Valor Glosado", "Participacion %"],
            rows_data=fac_rows,
            widths=[20, 36, 18, 18, 22, 16],
            money_col=5,
            pct_col=6,
            center_cols=(1, 3, 4),
            total_row=["TOTAL", "", fac_tot_items, "", fac_tot_val, 1.0 if fac_tot_val > 0 else 0.0],
        )

        # Hoja 4: Top Conceptos de Objecion
        con_rows = [
            [
                c["codigo_concepto"],
                c["nombre_concepto"],
                c["clase_objecion"],
                c["cantidad_glosas"],
                c["facturas_afectadas"],
                c["total_valor_glosado"],
                c["participacion_pct"] / 100.0,
            ]
            for c in report.resumen_top_conceptos
        ]
        con_tot_cant = sum(c["cantidad_glosas"] for c in report.resumen_top_conceptos)
        con_tot_val = round(sum(c["total_valor_glosado"] for c in report.resumen_top_conceptos), 2)
        write_breakdown_sheet(
            sheet_name="Top Conceptos Objecion",
            headers=["Codigo Concepto", "Nombre Concepto", "Clase Objecion", "Cantidad Glosas", "Facturas Afectadas", "Total Valor Glosado", "Participacion %"],
            rows_data=con_rows,
            widths=[16, 54, 18, 18, 18, 22, 16],
            money_col=6,
            pct_col=7,
            center_cols=(1, 3, 4, 5),
            total_row=["TOTAL", "", "", con_tot_cant, "", con_tot_val, 1.0 if con_tot_val > 0 else 0.0],
        )

        # Hoja 5: Detalle de Glosas
        ws_det = wb.create_sheet("Detalle de Glosas")
        det_headers = [
            "ID Glosa",
            "Fecha",
            "Factura",
            "Entidad / EPS",
            "Codigo Glosa",
            "Concepto / Observacion",
            "Servicio Glosado",
            "Centro de Costo",
            "Estado",
            "Valor Facturado",
            "Valor Glosado",
        ]
        for c_idx, h in enumerate(det_headers, start=1):
            cell = ws_det.cell(1, c_idx, h)
            cell.font = header_font
            cell.fill = navy_fill
            cell.alignment = Alignment(horizontal="center", vertical="center")
            cell.border = border
        ws_det.row_dimensions[1].height = 24

        fast_mode = len(report.registros) > 5000
        no_fill = PatternFill(fill_type=None)
        right_align = Alignment(horizontal="right")
        center_align = Alignment(horizontal="center")

        for r_idx, reg in enumerate(report.registros, start=2):
            fill = zebra_fill if (not fast_mode and r_idx % 2) else no_fill
            row_vals = [
                reg["id_glosa"],
                reg["fecha_glosa"],
                reg["numero_factura"],
                reg["entidad_eps"],
                reg["codigo_glosa"],
                reg["concepto_glosa"],
                reg.get("servicio_glosado", ""),
                reg.get("centro_costo", ""),
                reg["estado_glosa"],
                reg["valor_facturado"],
                reg["valor_glosado"],
            ]
            for c_idx, val in enumerate(row_vals, start=1):
                c = ws_det.cell(r_idx, c_idx, val)
                if not fast_mode:
                    c.font = body_font
                    c.fill = fill
                    c.border = border
                if c_idx in (10, 11):
                    c.number_format = "$#,##0"
                    c.alignment = right_align
                elif c_idx in (1, 2, 5, 9):
                    c.alignment = center_align

        det_widths = [14, 14, 16, 26, 14, 42, 30, 24, 14, 18, 18]
        for c_idx, w in enumerate(det_widths, start=1):
            ws_det.column_dimensions[get_column_letter(c_idx)].width = w
        ws_det.freeze_panes = "A2"
        if report.registros:
            ws_det.auto_filter.ref = f"A1:K{len(report.registros) + 1}"

        wb.save(target_path)
        logger.info("Informe Excel exportado en: %s", target_path)
        return target_path

    # -------------------- EXPORTACIÓN PDF --------------------

    def export_to_pdf(
        self,
        report: ExternalGlosasReportData,
        output_path: str | None = None,
    ) -> str:
        """Genera resumen ejecutivo PDF con KPIs y tablas ejecutivas (Entidades, Conceptos y Facturadores)."""
        target_path = output_path or self._build_default_filename(report, "pdf")
        ensure_dir(os.path.dirname(os.path.abspath(target_path)))

        pdf = _NativePdfBuilder()
        navy = (0.118, 0.227, 0.541)
        white = (1.0, 1.0, 1.0)
        slate_dark = (0.09, 0.14, 0.22)
        slate_muted = (0.39, 0.45, 0.55)
        card_bg = (0.95, 0.97, 0.99)
        zebra_bg = (0.97, 0.98, 0.99)
        total_bg = (0.89, 0.91, 0.94)
        border_col = (0.80, 0.84, 0.90)

        def draw_page_banner(title_suffix: str = ""):
            pdf.rect(36, 536, 720, 44, fill_rgb=navy)
            pdf.text(48, 561, f"CLINICA LA CONCEPCION - INFORME EJECUTIVO DE GLOSAS{title_suffix}", size=13, bold=True, rgb=white)
            sub = (
                f"Periodicidad: {report.period_label}  |  Periodo: {report.fecha_desde} al {report.fecha_hasta}  |  "
                f"Origen: {report.database_name}.{report.table_name}"
            )
            pdf.text(48, 545, sub, size=8.5, bold=False, rgb=(0.86, 0.92, 1.0))

        draw_page_banner()

        # Tarjetas KPI (5 tarjetas horizontales)
        kpis = [
            ("Cantidad Glosas", f"{report.total_glosas:,}".replace(",", "."), "Registros en corte"),
            ("Facturas Unicas", f"{report.total_facturas:,}".replace(",", "."), "Cuentas afectadas"),
            ("Valor Facturado", _format_money_cop(report.valor_total_facturado), "Base auditada"),
            ("Valor Glosado", _format_money_cop(report.valor_total_glosado), f"{report.porcentaje_glosado:.1f}% del facturado"),
            ("Promedio Glosa", _format_money_cop(report.promedio_por_glosa), "Valor medio"),
        ]
        card_w = 136.0
        gap = 10.0
        kpi_y = 468.0
        for idx, (lbl, val, sub_lbl) in enumerate(kpis):
            cx = 36.0 + idx * (card_w + gap)
            pdf.rect(cx, kpi_y, card_w, 54, fill_rgb=card_bg, stroke_rgb=border_col, line_width=0.7)
            pdf.text(cx + 8, kpi_y + 40, lbl, size=8.0, bold=True, rgb=slate_muted)
            pdf.text(cx + 8, kpi_y + 22, val, size=12.0, bold=True, rgb=slate_dark)
            pdf.text(cx + 8, kpi_y + 8, sub_lbl, size=7.5, bold=False, rgb=slate_muted)

        # TABLA 1: Resumen por Entidad / EPS (Top 10)
        y_cursor = 446.0
        pdf.text(36, y_cursor, "Tabla 1. Resumen por Entidad / EPS (Top 10)", size=10.5, bold=True, rgb=navy)
        y_cursor -= 18.0

        sum_cols = [
            ("Entidad / EPS", 36, 210, "left"),
            ("Cantidad Glosas", 250, 90, "center"),
            ("Facturas", 345, 70, "center"),
            ("Valor Facturado", 420, 115, "right"),
            ("Valor Glosado", 540, 115, "right"),
            ("Participacion", 660, 86, "right"),
        ]
        pdf.rect(36, y_cursor - 4, 720, 17, fill_rgb=navy)
        for col_title, col_x, col_w, align in sum_cols:
            tx = col_x + 6 if align == "left" else (col_x + col_w / 2 if align == "center" else col_x + col_w - 6)
            pdf.text(tx, y_cursor + 2, col_title, size=8.0, bold=True, rgb=white, align=align)
        y_cursor -= 17.0

        for idx_ent, ent in enumerate(report.resumen_por_entidad[:10]):
            if idx_ent % 2 == 1:
                pdf.rect(36, y_cursor - 4, 720, 15, fill_rgb=zebra_bg)
            row_vals = [
                (ent["entidad"], 36, 210, "left", 36),
                (str(ent["cantidad_glosas"]), 250, 90, "center", 12),
                (str(ent["facturas_unicas"]), 345, 70, "center", 12),
                (_format_money_cop(ent["valor_facturado"]), 420, 115, "right", 18),
                (_format_money_cop(ent["valor_glosado"]), 540, 115, "right", 18),
                (f"{ent['participacion_pct']:.1f}%", 660, 86, "right", 10),
            ]
            for val_txt, col_x, col_w, align, max_c in row_vals:
                tx = col_x + 6 if align == "left" else (col_x + col_w / 2 if align == "center" else col_x + col_w - 6)
                pdf.text(tx, y_cursor + 1, val_txt, size=7.8, rgb=slate_dark, align=align, max_chars=max_c)
            y_cursor -= 15.0

        # Fila TOTAL GENERAL Tabla 1
        pdf.rect(36, y_cursor - 4, 720, 16, fill_rgb=total_bg)
        tot_ent_vals = [
            ("TOTAL GENERAL", 36, 210, "left", 25),
            (str(report.total_glosas), 250, 90, "center", 12),
            (str(report.total_facturas), 345, 70, "center", 12),
            (_format_money_cop(report.valor_total_facturado), 420, 115, "right", 18),
            (_format_money_cop(report.valor_total_glosado), 540, 115, "right", 18),
            ("100.0%" if report.total_glosas > 0 else "0.0%", 660, 86, "right", 10),
        ]
        for val_txt, col_x, col_w, align, max_c in tot_ent_vals:
            tx = col_x + 6 if align == "left" else (col_x + col_w / 2 if align == "center" else col_x + col_w - 6)
            pdf.text(tx, y_cursor + 1, val_txt, size=8.0, bold=True, rgb=slate_dark, align=align, max_chars=max_c)
        y_cursor -= 24.0

        # TABLA 2: Top Conceptos de Objecion (Top 10)
        if y_cursor < 140.0:
            pdf.new_page()
            draw_page_banner(" (Conceptos)")
            y_cursor = 510.0

        pdf.text(36, y_cursor, "Tabla 2. Top Conceptos de Objecion (Top 10)", size=10.5, bold=True, rgb=navy)
        y_cursor -= 18.0

        con_cols = [
            ("Codigo", 36, 56, "center"),
            ("Concepto de Objecion", 96, 300, "left"),
            ("Clase", 400, 80, "center"),
            ("Glosas", 484, 58, "center"),
            ("Facturas", 546, 58, "center"),
            ("Valor Glosado", 608, 92, "right"),
            ("% Valor", 704, 52, "right"),
        ]
        pdf.rect(36, y_cursor - 4, 720, 17, fill_rgb=navy)
        for col_title, cx, cw, align in con_cols:
            tx = cx + 6 if align == "left" else (cx + cw / 2 if align == "center" else cx + cw - 6)
            pdf.text(tx, y_cursor + 2, col_title, size=8.0, bold=True, rgb=white, align=align)
        y_cursor -= 17.0

        for idx_c, con in enumerate(report.resumen_top_conceptos[:10]):
            if y_cursor < 52.0:
                pdf.new_page()
                draw_page_banner(" (Conceptos)")
                y_cursor = 510.0
                pdf.rect(36, y_cursor - 4, 720, 17, fill_rgb=navy)
                for col_title, cx, cw, align in con_cols:
                    tx = cx + 6 if align == "left" else (cx + cw / 2 if align == "center" else cx + cw - 6)
                    pdf.text(tx, y_cursor + 2, col_title, size=8.0, bold=True, rgb=white, align=align)
                y_cursor -= 17.0

            if idx_c % 2 == 1:
                pdf.rect(36, y_cursor - 4, 720, 15, fill_rgb=zebra_bg)

            row_c = [
                (con.get("codigo_concepto", ""), 36, 56, "center", 10),
                (con.get("nombre_concepto", ""), 96, 300, "left", 58),
                (con.get("clase_objecion", ""), 400, 80, "center", 14),
                (str(con.get("cantidad_glosas", 0)), 484, 58, "center", 10),
                (str(con.get("facturas_afectadas", 0)), 546, 58, "center", 10),
                (_format_money_cop(con.get("total_valor_glosado", 0.0)), 608, 92, "right", 16),
                (f"{float(con.get('participacion_pct') or 0.0):.1f}%", 704, 52, "right", 8),
            ]
            for val_txt, cx, cw, align, max_c in row_c:
                tx = cx + 6 if align == "left" else (cx + cw / 2 if align == "center" else cx + cw - 6)
                pdf.text(tx, y_cursor + 1, val_txt, size=7.8, rgb=slate_dark, align=align, max_chars=max_c)
            y_cursor -= 15.0

        # TABLA 3: Glosas por Facturador (Top 10)
        y_cursor -= 22.0
        if y_cursor < 140.0:
            pdf.new_page()
            draw_page_banner(" (Facturadores)")
            y_cursor = 510.0

        pdf.text(36, y_cursor, "Tabla 3. Glosas por Facturador (Top 10)", size=10.5, bold=True, rgb=navy)
        y_cursor -= 18.0

        fac_cols = [
            ("Usuario", 36, 90, "left"),
            ("Nombre Facturador", 130, 250, "left"),
            ("Items Glosados", 384, 82, "center"),
            ("Facturas", 470, 72, "center"),
            ("Valor Glosado", 546, 120, "right"),
            ("% Valor", 670, 86, "right"),
        ]
        pdf.rect(36, y_cursor - 4, 720, 17, fill_rgb=navy)
        for col_title, cx, cw, align in fac_cols:
            tx = cx + 6 if align == "left" else (cx + cw / 2 if align == "center" else cx + cw - 6)
            pdf.text(tx, y_cursor + 2, col_title, size=8.0, bold=True, rgb=white, align=align)
        y_cursor -= 17.0

        for idx_f, fac in enumerate(report.resumen_por_facturador[:10]):
            if y_cursor < 52.0:
                pdf.new_page()
                draw_page_banner(" (Facturadores)")
                y_cursor = 510.0
                pdf.rect(36, y_cursor - 4, 720, 17, fill_rgb=navy)
                for col_title, cx, cw, align in fac_cols:
                    tx = cx + 6 if align == "left" else (cx + cw / 2 if align == "center" else cx + cw - 6)
                    pdf.text(tx, y_cursor + 2, col_title, size=8.0, bold=True, rgb=white, align=align)
                y_cursor -= 17.0

            if idx_f % 2 == 1:
                pdf.rect(36, y_cursor - 4, 720, 15, fill_rgb=zebra_bg)

            row_f = [
                (fac.get("usuario_facturador", ""), 36, 90, "left", 14),
                (fac.get("nombre_facturador", ""), 130, 250, "left", 44),
                (str(fac.get("cantidad_items_glosados", 0)), 384, 82, "center", 10),
                (str(fac.get("facturas_glosadas", 0)), 470, 72, "center", 10),
                (_format_money_cop(fac.get("total_valor_glosado", 0.0)), 546, 120, "right", 18),
                (f"{float(fac.get('participacion_pct') or 0.0):.1f}%", 670, 86, "right", 8),
            ]
            for val_txt, cx, cw, align, max_c in row_f:
                tx = cx + 6 if align == "left" else (cx + cw / 2 if align == "center" else cx + cw - 6)
                pdf.text(tx, y_cursor + 1, val_txt, size=7.8, rgb=slate_dark, align=align, max_chars=max_c)
            y_cursor -= 15.0

        # Nota al pie indicando Excel completo
        if y_cursor < 44.0:
            pdf.new_page()
            draw_page_banner(" (Nota)")
            y_cursor = 510.0
        pdf.text(
            36,
            y_cursor - 6,
            "Resumen ejecutivo (Entidades, Conceptos y Facturadores). Para consultar Glosas por Servicio y el detalle completo, abra el archivo Excel.",
            size=8.0,
            bold=True,
            rgb=slate_muted,
        )

        pdf_bytes = pdf.build_bytes()
        with open(target_path, "wb") as f:
            f.write(pdf_bytes)

        logger.info("Informe PDF exportado en: %s", target_path)
        return target_path


def create_default_dgh_report_service() -> tuple[ExternalGlosasReportService, Any]:
    """Crea la instancia por defecto conectada al proveedor SQL Server de DGH."""
    from app.config.settings import DEFAULT_DGH_SQL_DATABASE
    from app.service.dgh_sql_provider import (
        DGH_GLOSAS_COLUMN_MAPPING,
        DghSqlGlosasProvider,
    )

    provider = DghSqlGlosasProvider()
    schema = ExternalTableSchema(
        database_name=DEFAULT_DGH_SQL_DATABASE,
        table_name="CRNRECOBJC",
        column_mapping=dict(DGH_GLOSAS_COLUMN_MAPPING),
    )
    service = ExternalGlosasReportService(schema=schema, custom_query_fn=provider)
    return service, provider


# Instancias compartidas por defecto
default_report_service, default_sql_provider = create_default_dgh_report_service()
default_report_exporter = GlosasReportExporter()
