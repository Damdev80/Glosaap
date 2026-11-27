"""
Módulo independiente tipo Tab para el Informe de Glosas (Base de Datos Externa).
Soporta periodicidades semanal, quincenal, mensual, trimestral, semestral y
personalizada, vista previa interactiva, búsqueda rápida, paginación y
exportación a Excel (.xlsx) y PDF (.pdf).
"""
from __future__ import annotations

import math
import os
import subprocess
import sys
import threading
from datetime import date, datetime

import flet as ft

from app.config.settings import logger
from app.service.glosas_report_exporter import (
    ExternalGlosasReportData,
    ExternalGlosasReportService,
    GlosasReportExporter,
    PeriodRangeCalculator,
    default_report_exporter,
    default_report_service,
    default_sql_provider,
)
from app.ui.components.loading_overlay import ToastNotification
from app.ui.styles import SPACING


class GlosasReportTabView:
    """Vista modular del Tab 'Informe de Glosas' dentro del Dashboard."""

    PAGE_SIZE = 50

    def __init__(
        self,
        page: ft.Page,
        report_service: ExternalGlosasReportService | None = None,
        exporter: GlosasReportExporter | None = None,
        sql_provider=None,
    ):
        self.page = page
        self.report_service = report_service or default_report_service
        self.exporter = exporter or default_report_exporter
        self.sql_provider = sql_provider or default_sql_provider
        self._toast = ToastNotification(page)

        self._loaded_once = False
        self._is_busy = False
        self._current_report: ExternalGlosasReportData | None = None
        self._last_exported_path: str | None = None
        self._search_query: str = ""
        self._page_index: int = 0
        self._active_subview: str = "detalle"

        init_desde, init_hasta = PeriodRangeCalculator.calculate_range(
            "MENSUAL", ref_date=date.today(), mode="rolling"
        )

        # Selectores de fecha nativos
        self._picker_desde = ft.DatePicker(
            first_date=datetime(2014, 1, 1),
            last_date=datetime(2035, 12, 31),
            on_change=lambda e: self._on_date_picked("desde", e),
        )
        self._picker_hasta = ft.DatePicker(
            first_date=datetime(2014, 1, 1),
            last_date=datetime(2035, 12, 31),
            on_change=lambda e: self._on_date_picked("hasta", e),
        )

        # Controles de filtro y periodicidad
        self._period_dropdown = ft.Dropdown(
            label="Periodicidad",
            value="MENSUAL",
            options=[
                ft.dropdown.Option("SEMANAL", "Semanal (7 dias)"),
                ft.dropdown.Option("QUINCENAL", "Quincenal (15 dias)"),
                ft.dropdown.Option("MENSUAL", "Mensual (30 dias)"),
                ft.dropdown.Option("TRIMESTRAL", "Trimestral (3 meses)"),
                ft.dropdown.Option("SEMESTRAL", "Semestral (6 meses)"),
                ft.dropdown.Option("PERSONALIZADO", "Personalizado"),
            ],
            dense=True,
            width=170,
            text_size=12,
            border_radius=8,
            content_padding=ft.padding.symmetric(horizontal=10, vertical=6),
            on_change=self._on_periodicity_change,
        )

        self._mode_dropdown = ft.Dropdown(
            label="Corte",
            value="rolling",
            options=[
                ft.dropdown.Option("rolling", "Ultimos N dias"),
                ft.dropdown.Option("calendar", "Corte calendario"),
            ],
            dense=True,
            width=145,
            text_size=12,
            border_radius=8,
            content_padding=ft.padding.symmetric(horizontal=10, vertical=6),
            on_change=self._on_periodicity_change,
        )

        self._desde_field = ft.TextField(
            label="Desde",
            hint_text="AAAA-MM-DD",
            value=init_desde.isoformat(),
            dense=True,
            width=148,
            height=40,
            text_size=12,
            border_radius=8,
            content_padding=ft.padding.only(left=10, right=4, top=6, bottom=6),
            suffix=ft.IconButton(
                icon=ft.Icons.CALENDAR_TODAY,
                icon_size=15,
                tooltip="Elegir fecha inicial",
                on_click=lambda e: self._open_date_picker(self._picker_desde),
            ),
            on_change=self._on_manual_date_change,
        )

        self._hasta_field = ft.TextField(
            label="Hasta",
            hint_text="AAAA-MM-DD",
            value=init_hasta.isoformat(),
            dense=True,
            width=148,
            height=40,
            text_size=12,
            border_radius=8,
            content_padding=ft.padding.only(left=10, right=4, top=6, bottom=6),
            suffix=ft.IconButton(
                icon=ft.Icons.CALENDAR_TODAY,
                icon_size=15,
                tooltip="Elegir fecha final",
                on_click=lambda e: self._open_date_picker(self._picker_hasta),
            ),
            on_change=self._on_manual_date_change,
        )

        self._entidad_dropdown = ft.Dropdown(
            label="Entidad / EPS",
            value="TODAS",
            options=[
                ft.dropdown.Option("TODAS", "Todas las entidades"),
                ft.dropdown.Option("SANITAS", "SANITAS"),
                ft.dropdown.Option("MUTUALSER", "MUTUALSER"),
                ft.dropdown.Option("COOSALUD", "COOSALUD"),
                ft.dropdown.Option("PREVISORA", "PREVISORA"),
                ft.dropdown.Option("FOMAG", "FOMAG"),
                ft.dropdown.Option("FAMILIAR", "FAMILIAR"),
            ],
            dense=True,
            expand=True,
            text_size=12,
            border_radius=8,
            content_padding=ft.padding.symmetric(horizontal=10, vertical=6),
            on_change=lambda e: self.refresh_report(),
        )

        # Botones de acción y exportación
        self._btn_consultar = ft.ElevatedButton(
            content=ft.Row([
                ft.Icon(ft.Icons.SEARCH, size=16),
                ft.Text("Consultar", size=12, weight=ft.FontWeight.W_600),
            ], spacing=6, tight=True),
            height=38,
            style=ft.ButtonStyle(
                shape=ft.RoundedRectangleBorder(radius=8),
                bgcolor=ft.Colors.PRIMARY,
                color=ft.Colors.ON_PRIMARY,
                padding=ft.padding.symmetric(horizontal=14, vertical=0),
            ),
            on_click=lambda e: self.refresh_report(),
        )

        self._btn_export_excel = ft.ElevatedButton(
            content=ft.Row([
                ft.Icon(ft.Icons.TABLE_VIEW, size=15),
                ft.Text("Excel", size=12, weight=ft.FontWeight.W_600),
            ], spacing=5, tight=True),
            height=34,
            tooltip="Exportar todo en Excel (5 hojas: Resumen, Servicios, Facturadores, Conceptos y Detalle)",
            style=ft.ButtonStyle(
                shape=ft.RoundedRectangleBorder(radius=8),
                bgcolor=ft.Colors.GREEN_700,
                color=ft.Colors.WHITE,
                padding=ft.padding.symmetric(horizontal=12, vertical=0),
            ),
            on_click=lambda e: self._export_report("excel"),
        )

        self._btn_export_pdf = ft.ElevatedButton(
            content=ft.Row([
                ft.Icon(ft.Icons.PICTURE_AS_PDF, size=15),
                ft.Text("PDF", size=12, weight=ft.FontWeight.W_600),
            ], spacing=5, tight=True),
            height=34,
            tooltip="Exportar resumen ejecutivo en PDF (KPIs + Entidades, Conceptos y Facturadores)",
            style=ft.ButtonStyle(
                shape=ft.RoundedRectangleBorder(radius=8),
                bgcolor=ft.Colors.RED_700,
                color=ft.Colors.WHITE,
                padding=ft.padding.symmetric(horizontal=12, vertical=0),
            ),
            on_click=lambda e: self._export_report("pdf"),
        )

        self._btn_open_folder = ft.OutlinedButton(
            content=ft.Row([
                ft.Icon(ft.Icons.FOLDER_OPEN, size=15),
                ft.Text("Carpeta", size=12),
            ], spacing=5, tight=True),
            height=34,
            tooltip="Abrir carpeta de exportaciones",
            style=ft.ButtonStyle(
                shape=ft.RoundedRectangleBorder(radius=8),
                padding=ft.padding.symmetric(horizontal=10, vertical=0),
            ),
            on_click=lambda e: self._open_output_folder(),
        )

        self._btn_config_sql = ft.OutlinedButton(
            content=ft.Row([
                ft.Icon(ft.Icons.STORAGE_OUTLINED, size=15),
                ft.Text("SQL", size=12),
            ], spacing=5, tight=True),
            height=34,
            tooltip="Configurar conexion SQL Server",
            style=ft.ButtonStyle(
                shape=ft.RoundedRectangleBorder(radius=8),
                padding=ft.padding.symmetric(horizontal=10, vertical=0),
            ),
            on_click=lambda e: self._open_sql_config_dialog(),
        )

        # Buscador rápido local para la tabla
        self._search_field = ft.TextField(
            hint_text="Buscar factura, codigo, entidad o concepto...",
            prefix_icon=ft.Icons.SEARCH,
            dense=True,
            width=265,
            height=34,
            text_size=11.5,
            border_radius=8,
            content_padding=ft.padding.symmetric(horizontal=10, vertical=4),
            on_change=self._on_search_change,
        )

        # Indicadores inline de estado SQL y última exportación
        self._status_pill = ft.Container(visible=False)
        self._export_pill = ft.Container(visible=False)
        self._progress_bar = ft.ProgressBar(height=3, visible=False)
        self._schema_banner = ft.Container(visible=False)
        self._kpi_row = ft.Row(spacing=10, alignment=ft.MainAxisAlignment.START)
        self._results_area = ft.Container(expand=True)

        self.container = self._build()

    # ==================== CONSTRUCCIÓN DE LA VISTA ====================

    def _build(self) -> ft.Container:
        """Construye la jerarquía compacta del módulo de informe y exportación."""
        # Flet 0.27.6: nunca combinar wrap=True con hijos expand=True en un Row.
        header_row = ft.Row([
            ft.Row([
                ft.Container(
                    content=ft.Icon(ft.Icons.ASSESSMENT_OUTLINED, size=18, color=ft.Colors.PRIMARY),
                    width=34,
                    height=34,
                    border_radius=8,
                    bgcolor=ft.Colors.PRIMARY_CONTAINER,
                    alignment=ft.alignment.center,
                ),
                ft.Column([
                    ft.Row([
                        ft.Text("Informe de Glosas", size=15, weight=ft.FontWeight.BOLD),
                        self._status_pill,
                        self._export_pill,
                    ], spacing=8, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                    ft.Text(
                        "Consulta consolidada por rango de fechas con exportacion a Excel y PDF",
                        size=11,
                        color=ft.Colors.ON_SURFACE_VARIANT,
                    ),
                ], spacing=1),
            ], spacing=10, vertical_alignment=ft.CrossAxisAlignment.CENTER, expand=True),
            ft.Row([
                self._btn_config_sql,
                self._btn_open_folder,
                ft.Container(width=1, height=22, bgcolor=ft.Colors.OUTLINE_VARIANT),
                self._btn_export_excel,
                self._btn_export_pdf,
            ], spacing=6, vertical_alignment=ft.CrossAxisAlignment.CENTER),
        ], spacing=10, vertical_alignment=ft.CrossAxisAlignment.CENTER)

        filters_row = ft.Row([
            self._period_dropdown,
            self._mode_dropdown,
            self._desde_field,
            self._hasta_field,
            self._entidad_dropdown,
            self._btn_consultar,
        ], spacing=8, vertical_alignment=ft.CrossAxisAlignment.CENTER)

        controls_bar = ft.Container(
            content=ft.Column([
                header_row,
                ft.Divider(height=1, thickness=0.6, color=ft.Colors.OUTLINE_VARIANT),
                filters_row,
            ], spacing=8),
            padding=ft.padding.symmetric(horizontal=SPACING["md"], vertical=10),
            bgcolor=ft.Colors.SURFACE,
            border_radius=12,
            border=ft.border.all(1, ft.Colors.OUTLINE_VARIANT),
        )

        body = ft.Column([
            controls_bar,
            self._progress_bar,
            self._schema_banner,
            self._kpi_row,
            self._results_area,
        ], spacing=8, expand=True)

        return ft.Container(
            content=body,
            expand=True,
        )

    # ==================== EVENTOS Y CARGA DE DATOS ====================

    def ensure_loaded(self, sync: bool = False) -> None:
        """Carga inicial diferida al activar por primera vez la pestaña del informe."""
        if self._loaded_once:
            return
        self._loaded_once = True
        if sync or self.report_service.custom_query_fn is None:
            self.load_report_sync()
        else:
            self.refresh_report()

    def _open_date_picker(self, picker: ft.DatePicker) -> None:
        """Abre un DatePicker nativo usando la API de diálogo de Flet."""
        try:
            self.page.open(picker)
        except Exception:
            pass

    def _on_date_picked(self, target: str, e) -> None:
        """Aplica la fecha seleccionada en el DatePicker y marca corte personalizado."""
        val = getattr(e.control, "value", None)
        if not val:
            return
        iso_str = val.strftime("%Y-%m-%d")
        if target == "desde":
            self._desde_field.value = iso_str
        else:
            self._hasta_field.value = iso_str
        self._period_dropdown.value = "PERSONALIZADO"
        self._safe_page_update()

    def _on_periodicity_change(self, e) -> None:
        """Recalcula automáticamente Desde/Hasta al cambiar periodicidad o tipo de corte."""
        period = str(self._period_dropdown.value or "MENSUAL").upper()
        mode = str(self._mode_dropdown.value or "rolling").lower()
        if period != "PERSONALIZADO":
            d_desde, d_hasta = PeriodRangeCalculator.calculate_range(period, ref_date=date.today(), mode=mode)
            self._desde_field.value = d_desde.isoformat()
            self._hasta_field.value = d_hasta.isoformat()
        self.refresh_report()

    def _on_manual_date_change(self, e) -> None:
        """Cambia la periodicidad a Personalizado cuando el usuario edita fechas manualmente."""
        if self._period_dropdown.value != "PERSONALIZADO":
            self._period_dropdown.value = "PERSONALIZADO"
            self._safe_page_update()

    def _on_search_change(self, e) -> None:
        """Filtra localmente los registros cargados en tabla y reinicia a página 1."""
        self._search_query = str(getattr(self._search_field, "value", "") or "").strip()
        self._page_index = 0
        if self._current_report is not None:
            self._render_tables(self._current_report)
            self._safe_page_update()

    def _go_page(self, delta: int) -> None:
        """Navega entre páginas de la sub-vista activa."""
        filtered = self._get_filtered_subview_items()
        total_pages = max(1, math.ceil(len(filtered) / self.PAGE_SIZE))
        new_idx = max(0, min(self._page_index + delta, total_pages - 1))
        if new_idx != self._page_index:
            self._page_index = new_idx
            if self._current_report is not None:
                self._render_tables(self._current_report)
                self._safe_page_update()

    def _set_subview(self, key: str) -> None:
        """Cambia la sub-vista activa ('detalle', 'servicios', 'facturadores', 'conceptos')."""
        if key not in ("detalle", "servicios", "facturadores", "conceptos"):
            return
        self._active_subview = key
        self._page_index = 0
        if self._current_report is not None:
            self._render_tables(self._current_report)
            self._safe_page_update()

    def _select_entity_filter(self, entidad: str) -> None:
        """Filtra por entidad al hacer clic en su tarjeta resumen (o limpia si ya estaba activa)."""
        current = str(self._entidad_dropdown.value or "TODAS")
        target = "TODAS" if current == entidad else entidad
        if not any(opt.key == target for opt in (self._entidad_dropdown.options or [])):
            self._entidad_dropdown.options.append(ft.dropdown.Option(target, target))
        self._entidad_dropdown.value = target
        self.refresh_report()

    def load_report_sync(self) -> ExternalGlosasReportData:
        """Ejecuta la consulta y renderiza en el hilo actual (útil en carga inicial y tests)."""
        period = str(self._period_dropdown.value or "MENSUAL")
        mode = str(self._mode_dropdown.value or "rolling")
        desde = str(self._desde_field.value or "").strip() or None
        hasta = str(self._hasta_field.value or "").strip() or None
        entidad = str(self._entidad_dropdown.value or "TODAS")

        report = self.report_service.fetch_report(
            periodicity=period,
            fecha_desde=desde,
            fecha_hasta=hasta,
            entidad_filter=entidad,
            mode=mode,
        )
        self._page_index = 0
        self._current_report = report
        self._render_report(report)
        self._safe_page_update()
        return report

    def refresh_report(self) -> None:
        """Consulta datos en segundo plano manteniendo la UI responsiva."""
        if self._is_busy:
            return
        self._set_busy(True)

        period = str(self._period_dropdown.value or "MENSUAL")
        mode = str(self._mode_dropdown.value or "rolling")
        desde = str(self._desde_field.value or "").strip() or None
        hasta = str(self._hasta_field.value or "").strip() or None
        entidad = str(self._entidad_dropdown.value or "TODAS")

        def worker():
            try:
                report = self.report_service.fetch_report(
                    periodicity=period,
                    fecha_desde=desde,
                    fecha_hasta=hasta,
                    entidad_filter=entidad,
                    mode=mode,
                )
                self._page_index = 0
                self._current_report = report
                self._render_report(report)
            except Exception as ex:
                logger.exception("Error consultando informe de glosas: %s", ex)
                self._notify(f"Error al consultar el informe: {ex}", is_error=True)
            finally:
                self._set_busy(False)

        threading.Thread(target=worker, daemon=True).start()

    def _export_report(self, fmt: str) -> None:
        """Exporta el informe actual en Excel o PDF en segundo plano."""
        if self._is_busy:
            return
        self._set_busy(True)

        period = str(self._period_dropdown.value or "MENSUAL")
        mode = str(self._mode_dropdown.value or "rolling")
        desde = str(self._desde_field.value or "").strip() or None
        hasta = str(self._hasta_field.value or "").strip() or None
        entidad = str(self._entidad_dropdown.value or "TODAS")

        def worker():
            try:
                report = self.report_service.fetch_report(
                    periodicity=period,
                    fecha_desde=desde,
                    fecha_hasta=hasta,
                    entidad_filter=entidad,
                    mode=mode,
                )
                self._page_index = 0
                self._current_report = report
                self._render_report(report)

                if fmt == "excel":
                    path = self.exporter.export_to_excel(report)
                    label = "Excel"
                else:
                    path = self.exporter.export_to_pdf(report)
                    label = "PDF"

                self._last_exported_path = path
                self._render_banner(report)
                self._notify(f"Informe {label} generado: {os.path.basename(path)}", is_error=False)
            except Exception as ex:
                logger.exception("Error exportando informe (%s): %s", fmt, ex)
                self._notify(f"No se pudo exportar el archivo: {ex}", is_error=True)
            finally:
                self._set_busy(False)

        threading.Thread(target=worker, daemon=True).start()

    # ==================== RENDERIZADO ====================

    def _format_money(self, val: float | int | None) -> str:
        """Formatea cifras monetarias en pesos colombianos."""
        try:
            return f"${float(val or 0.0):,.0f}".replace(",", ".")
        except Exception:
            return "$0"

    def _get_filtered_registros(self) -> list[dict]:
        """Retorna los registros detallados del informe actual filtrados por el buscador local."""
        if self._current_report is None:
            return []
        registros = self._current_report.registros
        q = self._search_query.lower()
        if not q:
            return registros
        return [
            r
            for r in registros
            if q in str(r.get("numero_factura", "")).lower()
            or q in str(r.get("codigo_glosa", "")).lower()
            or q in str(r.get("entidad_eps", "")).lower()
            or q in str(r.get("concepto_glosa", "")).lower()
            or q in str(r.get("servicio_glosado", "")).lower()
            or q in str(r.get("id_glosa", "")).lower()
        ]

    def _get_filtered_subview_items(self) -> list[dict]:
        """Retorna los ítems filtrados para la sub-vista activa."""
        if self._current_report is None:
            return []
        q = self._search_query.lower()
        if self._active_subview == "servicios":
            items = self._current_report.resumen_por_servicio
            if not q:
                return items
            return [r for r in items if q in str(r.get("servicio_glosado", "")).lower()]
        if self._active_subview == "facturadores":
            items = self._current_report.resumen_por_facturador
            if not q:
                return items
            return [
                r
                for r in items
                if q in str(r.get("usuario_facturador", "")).lower()
                or q in str(r.get("nombre_facturador", "")).lower()
            ]
        if self._active_subview == "conceptos":
            items = self._current_report.resumen_top_conceptos
            if not q:
                return items
            return [
                r
                for r in items
                if q in str(r.get("codigo_concepto", "")).lower()
                or q in str(r.get("nombre_concepto", "")).lower()
                or q in str(r.get("clase_objecion", "")).lower()
            ]
        return self._get_filtered_registros()

    def _render_report(self, report: ExternalGlosasReportData) -> None:
        """Actualiza dropdown de entidades, pills/banner, KPIs y tablas del informe."""
        self._sync_entity_dropdown_options(report)
        self._render_banner(report)
        self._render_kpis(report)
        self._render_tables(report)

    def _sync_entity_dropdown_options(self, report: ExternalGlosasReportData) -> None:
        """Puebla dinámicamente el filtro Entidad/EPS cuando se consulta sin filtro previo."""
        current_val = str(self._entidad_dropdown.value or "TODAS")
        if current_val.upper() not in ("TODAS", "ALL", "") or not report.resumen_por_entidad:
            return
        options = [ft.dropdown.Option("TODAS", "Todas las entidades")]
        seen = {"TODAS"}
        for item in report.resumen_por_entidad[:50]:
            ent = str(item.get("entidad") or "").strip()
            if not ent or ent in seen:
                continue
            seen.add(ent)
            cnt = item.get("cantidad_glosas", 0)
            options.append(ft.dropdown.Option(ent, f"{ent} ({cnt})"))
        self._entidad_dropdown.options = options

    def _render_banner(self, report: ExternalGlosasReportData) -> None:
        """Actualiza el chip inline de origen SQL y solo muestra alerta si hay fallback."""
        is_preview = report.is_preview_data
        pill_fg = ft.Colors.AMBER_900 if is_preview else ft.Colors.GREEN_800
        pill_bg = ft.Colors.AMBER_50 if is_preview else ft.Colors.GREEN_50
        dot_color = ft.Colors.AMBER_600 if is_preview else ft.Colors.GREEN_600
        pill_label = (
            "Modo previsualizacion"
            if is_preview
            else f"{report.database_name}.{report.table_name}  |  {report.fecha_desde} a {report.fecha_hasta}"
        )

        self._status_pill.content = ft.Row([
            ft.Icon(ft.Icons.CIRCLE, size=8, color=dot_color),
            ft.Text(pill_label, size=11, weight=ft.FontWeight.W_600, color=pill_fg),
        ], spacing=5, tight=True)
        self._status_pill.bgcolor = pill_bg
        self._status_pill.padding = ft.padding.symmetric(horizontal=9, vertical=3)
        self._status_pill.border_radius = 12
        self._status_pill.tooltip = report.source_note or pill_label
        self._status_pill.visible = True

        if self._last_exported_path and os.path.exists(self._last_exported_path):
            export_path = self._last_exported_path
            fname = os.path.basename(export_path)
            short_name = fname if len(fname) <= 30 else f"{fname[:27]}..."
            self._export_pill.content = ft.Row([
                ft.Icon(ft.Icons.CHECK_CIRCLE_OUTLINE, size=13, color=ft.Colors.PRIMARY),
                ft.Text(f"Abrir {short_name}", size=11, weight=ft.FontWeight.W_600, color=ft.Colors.PRIMARY),
            ], spacing=4, tight=True)
            self._export_pill.bgcolor = ft.Colors.PRIMARY_CONTAINER
            self._export_pill.padding = ft.padding.symmetric(horizontal=9, vertical=3)
            self._export_pill.border_radius = 12
            self._export_pill.tooltip = export_path
            self._export_pill.on_click = lambda e, p=export_path: self._open_file(p)
            self._export_pill.visible = True
        else:
            self._export_pill.visible = False

        # Banner de advertencia solo visible cuando hay previsualizacion/fallback
        if is_preview:
            status_note = report.source_note or "Datos de previsualizacion activos."
            self._schema_banner.content = ft.Container(
                content=ft.Row([
                    ft.Icon(ft.Icons.WARNING_AMBER_ROUNDED, size=18, color=ft.Colors.AMBER_800),
                    ft.Text(status_note, size=11.5, color=ft.Colors.ON_SURFACE, expand=True),
                    ft.TextButton("Configurar SQL", on_click=lambda e: self._open_sql_config_dialog()),
                ], spacing=8, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                padding=ft.padding.symmetric(horizontal=12, vertical=6),
                bgcolor=ft.Colors.AMBER_50,
                border_radius=8,
                border=ft.border.all(1, ft.Colors.AMBER_200),
            )
            self._schema_banner.visible = True
        else:
            self._schema_banner.content = None
            self._schema_banner.visible = False

    def _render_kpis(self, report: ExternalGlosasReportData) -> None:
        """Renderiza las 5 tarjetas KPI compactas del informe."""
        def kpi_card(title: str, value: str, subtitle: str, icon, icon_color, icon_bg) -> ft.Control:
            return ft.Container(
                content=ft.Row([
                    ft.Container(
                        content=ft.Icon(icon, size=20, color=icon_color),
                        width=38,
                        height=38,
                        border_radius=9,
                        bgcolor=icon_bg,
                        alignment=ft.alignment.center,
                    ),
                    ft.Column([
                        ft.Text(title, size=11, color=ft.Colors.ON_SURFACE_VARIANT, weight=ft.FontWeight.W_600, max_lines=1),
                        ft.Text(
                            value,
                            size=17,
                            weight=ft.FontWeight.BOLD,
                            color=ft.Colors.ON_SURFACE,
                            max_lines=1,
                            overflow=ft.TextOverflow.ELLIPSIS,
                        ),
                        ft.Text(subtitle, size=10.5, color=ft.Colors.ON_SURFACE_VARIANT, max_lines=1),
                    ], spacing=1, tight=True, expand=True),
                ], spacing=10, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                padding=ft.padding.symmetric(horizontal=12, vertical=10),
                border_radius=10,
                bgcolor=ft.Colors.SURFACE,
                border=ft.border.all(1, ft.Colors.OUTLINE_VARIANT),
                expand=1,
            )

        self._kpi_row.controls = [
            kpi_card(
                "Cantidad de Glosas",
                f"{report.total_glosas:,}".replace(",", "."),
                f"Corte {report.period_label.lower()}",
                ft.Icons.LIST_ALT,
                ft.Colors.BLUE_700,
                ft.Colors.BLUE_50,
            ),
            kpi_card(
                "Facturas Afectadas",
                f"{report.total_facturas:,}".replace(",", "."),
                "Cuentas unicas",
                ft.Icons.RECEIPT_LONG,
                ft.Colors.INDIGO_700,
                ft.Colors.INDIGO_50,
            ),
            kpi_card(
                "Valor Facturado",
                self._format_money(report.valor_total_facturado),
                "Base evaluada",
                ft.Icons.ATTACH_MONEY,
                ft.Colors.TEAL_700,
                ft.Colors.TEAL_50,
            ),
            kpi_card(
                "Valor Glosado",
                self._format_money(report.valor_total_glosado),
                f"{report.porcentaje_glosado:.1f}% del facturado",
                ft.Icons.MONEY_OFF,
                ft.Colors.RED_700,
                ft.Colors.RED_50,
            ),
            kpi_card(
                "Promedio por Glosa",
                self._format_money(report.promedio_por_glosa),
                "Media por registro",
                ft.Icons.ANALYTICS_OUTLINED,
                ft.Colors.AMBER_800,
                ft.Colors.AMBER_50,
            ),
        ]

    def _render_tables(self, report: ExternalGlosasReportData) -> None:
        """Renderiza tira horizontal de entidades y tabla pro paginada con buscador."""
        active_ent = str(self._entidad_dropdown.value or "TODAS")
        top_entities = report.resumen_por_entidad[:15]

        ent_cards: list[ft.Control] = []
        for item in top_entities:
            ent_name = item["entidad"]
            is_selected = active_ent != "TODAS" and active_ent == ent_name
            pct = float(item.get("participacion_pct") or 0.0)
            ent_cards.append(
                ft.Container(
                    content=ft.Column([
                        ft.Row([
                            ft.Text(
                                ent_name,
                                size=11.5,
                                weight=ft.FontWeight.BOLD,
                                color=ft.Colors.PRIMARY,
                                max_lines=1,
                                overflow=ft.TextOverflow.ELLIPSIS,
                                expand=True,
                            ),
                            ft.Container(
                                content=ft.Text(f"{pct:.1f}%", size=10, weight=ft.FontWeight.W_600, color=ft.Colors.PRIMARY),
                                bgcolor=ft.Colors.PRIMARY_CONTAINER,
                                padding=ft.padding.symmetric(horizontal=6, vertical=1),
                                border_radius=8,
                            ),
                        ], spacing=6, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                        ft.ProgressBar(
                            value=max(0.0, min(pct / 100.0, 1.0)),
                            height=4,
                            color=ft.Colors.PRIMARY,
                            bgcolor=ft.Colors.SURFACE_CONTAINER_HIGHEST,
                        ),
                        ft.Row([
                            ft.Text(f"{item['cantidad_glosas']} glosas", size=10.5, color=ft.Colors.ON_SURFACE_VARIANT),
                            ft.Text(f"{item['facturas_unicas']} fact.", size=10.5, color=ft.Colors.ON_SURFACE_VARIANT),
                        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                        ft.Text(
                            self._format_money(item["valor_glosado"]),
                            size=12.5,
                            weight=ft.FontWeight.BOLD,
                            color=ft.Colors.ON_SURFACE,
                        ),
                    ], spacing=4, tight=True),
                    padding=ft.padding.symmetric(horizontal=10, vertical=8),
                    width=215,
                    border_radius=10,
                    bgcolor=ft.Colors.SURFACE,
                    border=ft.border.all(
                        2 if is_selected else 1,
                        ft.Colors.PRIMARY if is_selected else ft.Colors.OUTLINE_VARIANT,
                    ),
                    tooltip=f"{ent_name} - Clic para filtrar",
                    ink=True,
                    on_click=lambda e, name=ent_name: self._select_entity_filter(name),
                )
            )

        summary_header_controls: list[ft.Control] = [
            ft.Text("Distribucion por Entidad / EPS", size=13, weight=ft.FontWeight.W_600),
            ft.Container(
                content=ft.Text(
                    f"Top {len(top_entities)} de {len(report.resumen_por_entidad)}"
                    if len(report.resumen_por_entidad) > len(top_entities)
                    else f"{len(report.resumen_por_entidad)} entidad(es)",
                    size=10.5,
                    color=ft.Colors.ON_SURFACE_VARIANT,
                ),
                bgcolor=ft.Colors.SURFACE_CONTAINER_HIGHEST,
                padding=ft.padding.symmetric(horizontal=8, vertical=2),
                border_radius=10,
            ),
        ]
        if active_ent != "TODAS":
            summary_header_controls.append(
                ft.TextButton(
                    content=ft.Row([
                        ft.Icon(ft.Icons.FILTER_ALT_OFF, size=14),
                        ft.Text(f"Limpiar filtro ({active_ent[:18]})", size=11),
                    ], spacing=4, tight=True),
                    on_click=lambda e: self._select_entity_filter(active_ent),
                )
            )
        summary_header_controls.append(ft.Container(expand=True))
        summary_header_controls.append(
            ft.Text("Clic en una tarjeta para filtrar", size=10.5, color=ft.Colors.ON_SURFACE_VARIANT)
        )

        summary_section = ft.Column([
            ft.Row(summary_header_controls, spacing=8, vertical_alignment=ft.CrossAxisAlignment.CENTER),
            ft.Row(ent_cards, scroll=ft.ScrollMode.AUTO, spacing=10)
            if ent_cards
            else ft.Text("Sin entidades para mostrar en el periodo", size=12, italic=True),
        ], spacing=6)

        # Filtrado local y paginación según sub-vista activa
        filtered_items = self._get_filtered_subview_items()
        total_filtered = len(filtered_items)
        total_pages = max(1, math.ceil(total_filtered / self.PAGE_SIZE))
        if self._page_index >= total_pages:
            self._page_index = total_pages - 1
        start = self._page_index * self.PAGE_SIZE
        end = start + self.PAGE_SIZE
        page_items = filtered_items[start:end]

        if self._active_subview == "servicios":
            active_table = self._build_servicios_table(page_items)
        elif self._active_subview == "facturadores":
            active_table = self._build_facturadores_table(page_items)
        elif self._active_subview == "conceptos":
            active_table = self._build_conceptos_table(page_items)
        else:
            active_table = self._build_detalle_table(page_items)

        if page_items:
            detail_box: ft.Control = ft.Container(
                content=ft.Column([
                    ft.Row([active_table], scroll=ft.ScrollMode.AUTO),
                ], scroll=ft.ScrollMode.AUTO, expand=True),
                border=ft.border.all(1, ft.Colors.OUTLINE_VARIANT),
                border_radius=10,
                bgcolor=ft.Colors.SURFACE,
                padding=0,
                expand=True,
            )
        else:
            detail_box = ft.Container(
                content=ft.Column([
                    ft.Icon(ft.Icons.FIND_IN_PAGE_OUTLINED, size=44, color=ft.Colors.PRIMARY),
                    ft.Text("No se encontraron glosas para los criterios seleccionados", size=14, weight=ft.FontWeight.BOLD),
                    ft.Text(
                        "Ajusta la periodicidad, las fechas, el buscador o el filtro de entidad y presiona Consultar.",
                        size=12,
                        color=ft.Colors.ON_SURFACE_VARIANT,
                    ),
                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, alignment=ft.MainAxisAlignment.CENTER, spacing=6),
                alignment=ft.alignment.center,
                border=ft.border.all(1, ft.Colors.OUTLINE_VARIANT),
                border_radius=10,
                bgcolor=ft.Colors.SURFACE,
                padding=24,
                expand=True,
            )

        count_badge = ft.Container(
            content=ft.Text(
                f"{total_filtered:,} filas".replace(",", "."),
                size=10.5,
                weight=ft.FontWeight.W_600,
                color=ft.Colors.ON_SURFACE_VARIANT,
            ),
            bgcolor=ft.Colors.SURFACE_CONTAINER_HIGHEST,
            padding=ft.padding.symmetric(horizontal=8, vertical=2),
            border_radius=10,
        )

        subview_defs = [
            ("detalle", "Detalle"),
            ("servicios", f"Por Servicio ({len(report.resumen_por_servicio)})"),
            ("facturadores", f"Por Facturador ({len(report.resumen_por_facturador)})"),
            ("conceptos", f"Top Conceptos ({len(report.resumen_top_conceptos)})"),
        ]
        subview_buttons: list[ft.Control] = []
        for sv_key, sv_label in subview_defs:
            is_act = self._active_subview == sv_key
            subview_buttons.append(
                ft.TextButton(
                    content=ft.Text(
                        sv_label,
                        size=11.5,
                        weight=ft.FontWeight.BOLD if is_act else ft.FontWeight.W_500,
                        color=ft.Colors.PRIMARY if is_act else ft.Colors.ON_SURFACE_VARIANT,
                    ),
                    style=ft.ButtonStyle(
                        bgcolor=ft.Colors.PRIMARY_CONTAINER if is_act else ft.Colors.SURFACE_CONTAINER_HIGHEST,
                        shape=ft.RoundedRectangleBorder(radius=8),
                        padding=ft.padding.symmetric(horizontal=10, vertical=4),
                    ),
                    on_click=lambda e, k=sv_key: self._set_subview(k),
                )
            )

        pagination_row = ft.Row([
            ft.IconButton(
                icon=ft.Icons.CHEVRON_LEFT,
                icon_size=18,
                tooltip="Pagina anterior",
                disabled=self._page_index <= 0,
                on_click=lambda e: self._go_page(-1),
            ),
            ft.Text(
                f"Pag {self._page_index + 1} / {total_pages}",
                size=11.5,
                weight=ft.FontWeight.W_600,
                color=ft.Colors.ON_SURFACE_VARIANT,
            ),
            ft.IconButton(
                icon=ft.Icons.CHEVRON_RIGHT,
                icon_size=18,
                tooltip="Pagina siguiente",
                disabled=self._page_index >= total_pages - 1,
                on_click=lambda e: self._go_page(1),
            ),
        ], spacing=2, vertical_alignment=ft.CrossAxisAlignment.CENTER)

        detail_header = ft.Row([
            ft.Row([
                *subview_buttons,
                count_badge,
            ], spacing=6, vertical_alignment=ft.CrossAxisAlignment.CENTER, expand=True),
            self._search_field,
            pagination_row,
        ], spacing=10, vertical_alignment=ft.CrossAxisAlignment.CENTER)

        self._results_area.content = ft.Column([
            summary_section,
            detail_header,
            detail_box,
        ], spacing=6, expand=True)

    def _build_servicios_table(self, page_items: list[dict]) -> ft.DataTable:
        """Construye la tabla de Glosas agrupadas por servicio (SLNSERPRO)."""
        rows = []
        for item in page_items:
            srv = str(item.get("servicio_glosado") or "")
            pct = float(item.get("participacion_pct") or 0.0)
            rows.append(
                ft.DataRow(
                    cells=[
                        ft.DataCell(
                            ft.Container(
                                content=ft.Text(srv, size=11, weight=ft.FontWeight.W_600, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS),
                                width=420,
                                tooltip=srv,
                            )
                        ),
                        ft.DataCell(ft.Text(str(item.get("cantidad_glosas", 0)), size=11)),
                        ft.DataCell(ft.Text(str(item.get("facturas_afectadas", 0)), size=11)),
                        ft.DataCell(ft.Text(self._format_money(item.get("total_valor_glosado")), size=11, weight=ft.FontWeight.BOLD, color=ft.Colors.RED_700)),
                        ft.DataCell(ft.Text(f"{pct:.1f}%", size=11)),
                    ]
                )
            )
        return ft.DataTable(
            columns=[
                ft.DataColumn(ft.Text("Servicio Glosado", size=11, weight=ft.FontWeight.BOLD)),
                ft.DataColumn(ft.Text("Cantidad Glosas", size=11, weight=ft.FontWeight.BOLD), numeric=True),
                ft.DataColumn(ft.Text("Facturas Afectadas", size=11, weight=ft.FontWeight.BOLD), numeric=True),
                ft.DataColumn(ft.Text("Total Valor Glosado", size=11, weight=ft.FontWeight.BOLD), numeric=True),
                ft.DataColumn(ft.Text("% Valor", size=11, weight=ft.FontWeight.BOLD), numeric=True),
            ],
            rows=rows,
            data_row_min_height=34,
            data_row_max_height=38,
            heading_row_height=36,
            column_spacing=20,
            horizontal_margin=14,
            divider_thickness=0.6,
            heading_row_color=ft.Colors.SURFACE_CONTAINER_HIGHEST,
        )

    def _build_facturadores_table(self, page_items: list[dict]) -> ft.DataTable:
        """Construye la tabla de Glosas agrupadas por usuario facturador."""
        rows = []
        for item in page_items:
            nom = str(item.get("nombre_facturador") or "")
            pct = float(item.get("participacion_pct") or 0.0)
            rows.append(
                ft.DataRow(
                    cells=[
                        ft.DataCell(ft.Text(str(item.get("usuario_facturador") or ""), size=11, weight=ft.FontWeight.BOLD)),
                        ft.DataCell(
                            ft.Container(
                                content=ft.Text(nom, size=11, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS),
                                width=300,
                                tooltip=nom,
                            )
                        ),
                        ft.DataCell(ft.Text(str(item.get("cantidad_items_glosados", 0)), size=11)),
                        ft.DataCell(ft.Text(str(item.get("facturas_glosadas", 0)), size=11)),
                        ft.DataCell(ft.Text(self._format_money(item.get("total_valor_glosado")), size=11, weight=ft.FontWeight.BOLD, color=ft.Colors.RED_700)),
                        ft.DataCell(ft.Text(f"{pct:.1f}%", size=11)),
                    ]
                )
            )
        return ft.DataTable(
            columns=[
                ft.DataColumn(ft.Text("Usuario Facturador", size=11, weight=ft.FontWeight.BOLD)),
                ft.DataColumn(ft.Text("Nombre Facturador", size=11, weight=ft.FontWeight.BOLD)),
                ft.DataColumn(ft.Text("Items Glosados", size=11, weight=ft.FontWeight.BOLD), numeric=True),
                ft.DataColumn(ft.Text("Facturas Glosadas", size=11, weight=ft.FontWeight.BOLD), numeric=True),
                ft.DataColumn(ft.Text("Total Valor Glosado", size=11, weight=ft.FontWeight.BOLD), numeric=True),
                ft.DataColumn(ft.Text("% Valor", size=11, weight=ft.FontWeight.BOLD), numeric=True),
            ],
            rows=rows,
            data_row_min_height=34,
            data_row_max_height=38,
            heading_row_height=36,
            column_spacing=20,
            horizontal_margin=14,
            divider_thickness=0.6,
            heading_row_color=ft.Colors.SURFACE_CONTAINER_HIGHEST,
        )

    def _build_conceptos_table(self, page_items: list[dict]) -> ft.DataTable:
        """Construye la tabla Top de Conceptos de Objecion con clase administrativa/asistencial."""
        rows = []
        for item in page_items:
            nom = str(item.get("nombre_concepto") or "")
            pct = float(item.get("participacion_pct") or 0.0)
            rows.append(
                ft.DataRow(
                    cells=[
                        ft.DataCell(
                            ft.Container(
                                content=ft.Text(str(item.get("codigo_concepto") or ""), size=10.5, weight=ft.FontWeight.BOLD, color=ft.Colors.PRIMARY),
                                bgcolor=ft.Colors.PRIMARY_CONTAINER,
                                padding=ft.padding.symmetric(horizontal=6, vertical=2),
                                border_radius=6,
                            )
                        ),
                        ft.DataCell(
                            ft.Container(
                                content=ft.Text(nom, size=11, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS),
                                width=380,
                                tooltip=nom,
                            )
                        ),
                        ft.DataCell(ft.Text(str(item.get("clase_objecion") or "Ninguno"), size=11)),
                        ft.DataCell(ft.Text(str(item.get("cantidad_glosas", 0)), size=11)),
                        ft.DataCell(ft.Text(str(item.get("facturas_afectadas", 0)), size=11)),
                        ft.DataCell(ft.Text(self._format_money(item.get("total_valor_glosado")), size=11, weight=ft.FontWeight.BOLD, color=ft.Colors.RED_700)),
                        ft.DataCell(ft.Text(f"{pct:.1f}%", size=11)),
                    ]
                )
            )
        return ft.DataTable(
            columns=[
                ft.DataColumn(ft.Text("Codigo", size=11, weight=ft.FontWeight.BOLD)),
                ft.DataColumn(ft.Text("Nombre Concepto", size=11, weight=ft.FontWeight.BOLD)),
                ft.DataColumn(ft.Text("Clase", size=11, weight=ft.FontWeight.BOLD)),
                ft.DataColumn(ft.Text("Cantidad Glosas", size=11, weight=ft.FontWeight.BOLD), numeric=True),
                ft.DataColumn(ft.Text("Facturas", size=11, weight=ft.FontWeight.BOLD), numeric=True),
                ft.DataColumn(ft.Text("Total Valor Glosado", size=11, weight=ft.FontWeight.BOLD), numeric=True),
                ft.DataColumn(ft.Text("% Valor", size=11, weight=ft.FontWeight.BOLD), numeric=True),
            ],
            rows=rows,
            data_row_min_height=34,
            data_row_max_height=38,
            heading_row_height=36,
            column_spacing=18,
            horizontal_margin=14,
            divider_thickness=0.6,
            heading_row_color=ft.Colors.SURFACE_CONTAINER_HIGHEST,
        )

    def _build_detalle_table(self, page_regs: list[dict]) -> ft.DataTable:
        """Construye la tabla detallada de registros individuales de glosa."""
        rows: list[ft.DataRow] = []
        for reg in page_regs:
            concepto_txt = str(reg.get("concepto_glosa") or "")
            servicio_txt = str(reg.get("servicio_glosado") or "")
            cc_txt = str(reg.get("centro_costo") or "")
            ent_txt = str(reg.get("entidad_eps") or "")
            est_txt = str(reg.get("estado_glosa") or "")
            is_conf = est_txt in ("CONFIRMADA", "ACEPTADA", "CONTESTADA")

            rows.append(
                ft.DataRow(
                    cells=[
                        ft.DataCell(ft.Text(reg["id_glosa"], size=11, weight=ft.FontWeight.BOLD)),
                        ft.DataCell(ft.Text(reg["fecha_glosa"], size=11)),
                        ft.DataCell(ft.Text(reg["numero_factura"], size=11)),
                        ft.DataCell(
                            ft.Container(
                                content=ft.Text(
                                    ent_txt,
                                    size=11,
                                    weight=ft.FontWeight.W_600,
                                    max_lines=1,
                                    overflow=ft.TextOverflow.ELLIPSIS,
                                ),
                                width=165,
                                tooltip=ent_txt,
                            )
                        ),
                        ft.DataCell(
                            ft.Container(
                                content=ft.Text(
                                    reg["codigo_glosa"],
                                    size=10.5,
                                    weight=ft.FontWeight.BOLD,
                                    color=ft.Colors.PRIMARY,
                                ),
                                bgcolor=ft.Colors.PRIMARY_CONTAINER,
                                padding=ft.padding.symmetric(horizontal=6, vertical=2),
                                border_radius=6,
                            )
                        ),
                        ft.DataCell(
                            ft.Text(
                                self._format_money(reg["valor_glosado"]),
                                size=11,
                                weight=ft.FontWeight.BOLD,
                                color=ft.Colors.RED_700,
                            )
                        ),
                        ft.DataCell(ft.Text(self._format_money(reg["valor_facturado"]), size=11)),
                        ft.DataCell(
                            ft.Container(
                                content=ft.Text(
                                    concepto_txt,
                                    size=11,
                                    max_lines=1,
                                    overflow=ft.TextOverflow.ELLIPSIS,
                                ),
                                width=240,
                                tooltip=concepto_txt,
                            )
                        ),
                        ft.DataCell(
                            ft.Container(
                                content=ft.Text(
                                    servicio_txt,
                                    size=11,
                                    max_lines=1,
                                    overflow=ft.TextOverflow.ELLIPSIS,
                                ),
                                width=185,
                                tooltip=servicio_txt,
                            )
                        ),
                        ft.DataCell(
                            ft.Container(
                                content=ft.Text(
                                    cc_txt,
                                    size=11,
                                    max_lines=1,
                                    overflow=ft.TextOverflow.ELLIPSIS,
                                ),
                                width=145,
                                tooltip=cc_txt,
                            )
                        ),
                        ft.DataCell(
                            ft.Container(
                                content=ft.Text(
                                    est_txt,
                                    size=10,
                                    weight=ft.FontWeight.W_600,
                                    color=ft.Colors.GREEN_800 if is_conf else ft.Colors.ON_SURFACE_VARIANT,
                                ),
                                bgcolor=ft.Colors.GREEN_50 if is_conf else ft.Colors.SURFACE_CONTAINER_HIGHEST,
                                padding=ft.padding.symmetric(horizontal=7, vertical=2),
                                border_radius=8,
                            )
                        ),
                    ]
                )
            )

        return ft.DataTable(
            columns=[
                ft.DataColumn(ft.Text("ID", size=11, weight=ft.FontWeight.BOLD)),
                ft.DataColumn(ft.Text("Fecha", size=11, weight=ft.FontWeight.BOLD)),
                ft.DataColumn(ft.Text("Factura", size=11, weight=ft.FontWeight.BOLD)),
                ft.DataColumn(ft.Text("Entidad", size=11, weight=ft.FontWeight.BOLD)),
                ft.DataColumn(ft.Text("Codigo", size=11, weight=ft.FontWeight.BOLD)),
                ft.DataColumn(ft.Text("Valor Glosado", size=11, weight=ft.FontWeight.BOLD), numeric=True),
                ft.DataColumn(ft.Text("Valor Facturado", size=11, weight=ft.FontWeight.BOLD), numeric=True),
                ft.DataColumn(ft.Text("Concepto", size=11, weight=ft.FontWeight.BOLD)),
                ft.DataColumn(ft.Text("Servicio", size=11, weight=ft.FontWeight.BOLD)),
                ft.DataColumn(ft.Text("Centro Costo", size=11, weight=ft.FontWeight.BOLD)),
                ft.DataColumn(ft.Text("Estado", size=11, weight=ft.FontWeight.BOLD)),
            ],
            rows=rows,
            data_row_min_height=34,
            data_row_max_height=38,
            heading_row_height=36,
            column_spacing=14,
            horizontal_margin=12,
            divider_thickness=0.6,
            heading_row_color=ft.Colors.SURFACE_CONTAINER_HIGHEST,
        )

    # ==================== HELPERS DE UI Y SO ====================

    def _set_busy(self, busy: bool) -> None:
        """Actualiza estado de carga de botones y barra superior."""
        self._is_busy = busy
        self._progress_bar.visible = busy
        for btn in (self._btn_consultar, self._btn_export_excel, self._btn_export_pdf):
            btn.disabled = busy
        self._safe_page_update()

    def _notify(self, message: str, is_error: bool = False) -> None:
        """Muestra una notificación toast flotante reutilizando ToastNotification."""
        try:
            if is_error:
                self._toast.error(message)
            else:
                self._toast.success(message)
        except Exception:
            pass

    def _safe_page_update(self) -> None:
        """Actualiza la página Flet tolerando mocks o hilos."""
        try:
            self.page.update()
        except Exception:
            pass

    def _open_output_folder(self) -> None:
        """Abre la carpeta de exportación en el explorador del sistema."""
        folder = self.exporter.output_dir
        self._open_file(folder)

    def _open_file(self, path: str) -> None:
        """Abre un archivo o directorio con el programa predeterminado del sistema."""
        if not path:
            return
        try:
            if sys.platform.startswith("win"):
                os.startfile(path)  # type: ignore[attr-defined]
            elif sys.platform.startswith("darwin"):
                subprocess.Popen(["open", path])
            else:
                subprocess.Popen(["xdg-open", path])
        except Exception as ex:
            logger.warning("No se pudo abrir ruta %s: %s", path, ex)
            self._notify(f"No se pudo abrir la ruta: {ex}", is_error=True)

    def _open_sql_config_dialog(self) -> None:
        """Abre diálogo modal para configurar conexión y credenciales de SQL Server."""
        provider = self.sql_provider
        if provider is None:
            self._notify("Proveedor SQL no disponible en este contexto.", is_error=True)
            return

        cfg = provider.get_config(include_password=False)
        server_tf = ft.TextField(label="Servidor SQL", value=cfg.get("server", ""), dense=True, text_size=12)
        db_tf = ft.TextField(label="Base de Datos", value=cfg.get("database", ""), dense=True, text_size=12)
        user_tf = ft.TextField(label="Usuario", value=cfg.get("username", ""), dense=True, text_size=12)
        pwd_tf = ft.TextField(
            label="Contraseña SQL",
            value="",
            password=True,
            can_reveal_password=True,
            dense=True,
            text_size=12,
            hint_text="Clave guardada (dejar vacio para conservar)" if cfg.get("has_password") else "Ingresa la contraseña",
        )
        status_txt = ft.Text(
            "Credencial SQL lista en almacen seguro" if cfg.get("has_password") else "Sin contraseña guardada",
            size=11,
            color=ft.Colors.GREEN_700 if cfg.get("has_password") else ft.Colors.AMBER_700,
        )

        test_btn = ft.OutlinedButton("Probar conexion", icon=ft.Icons.NETWORK_CHECK)
        save_btn = ft.ElevatedButton("Guardar", icon=ft.Icons.SAVE)

        def on_test(ev):
            test_btn.disabled = True
            status_txt.value = "Probando conexion con SQL Server..."
            status_txt.color = ft.Colors.ON_SURFACE_VARIANT
            self._safe_page_update()

            def _worker():
                res = provider.test_connection(
                    server=server_tf.value,
                    database=db_tf.value,
                    username=user_tf.value,
                    password=pwd_tf.value or None,
                )
                status_txt.value = res.get("message", "")
                status_txt.color = ft.Colors.GREEN_700 if res.get("ok") else ft.Colors.ERROR
                test_btn.disabled = False
                self._safe_page_update()

            threading.Thread(target=_worker, daemon=True).start()

        def on_save(ev):
            try:
                ok = provider.save_config(
                    server=server_tf.value or "",
                    database=db_tf.value or "",
                    username=user_tf.value or "",
                    password=pwd_tf.value or "",
                )
                if ok:
                    self.report_service.schema.configure(
                        database_name=(db_tf.value or "").strip() or "DGEMPRES91",
                        table_name="CRNRECOBJC",
                    )
                    self.page.close(dialog)
                    self._notify("Configuracion SQL guardada correctamente.", is_error=False)
                    self.refresh_report()
                else:
                    status_txt.value = "No se pudieron guardar las credenciales."
                    status_txt.color = ft.Colors.ERROR
                    self._safe_page_update()
            except Exception as ex:
                status_txt.value = str(ex)
                status_txt.color = ft.Colors.ERROR
                self._safe_page_update()

        test_btn.on_click = on_test
        save_btn.on_click = on_save

        dialog = ft.AlertDialog(
            modal=True,
            title=ft.Row([
                ft.Icon(ft.Icons.STORAGE_ROUNDED, color=ft.Colors.PRIMARY),
                ft.Text("Configuracion SQL Server (DGH)", size=16, weight=ft.FontWeight.BOLD),
            ], spacing=8),
            content=ft.Container(
                width=420,
                content=ft.Column([
                    server_tf,
                    db_tf,
                    user_tf,
                    pwd_tf,
                    status_txt,
                ], spacing=10, tight=True),
            ),
            actions=[
                ft.TextButton("Cerrar", on_click=lambda e: self.page.close(dialog)),
                test_btn,
                save_btn,
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        self.page.open(dialog)
