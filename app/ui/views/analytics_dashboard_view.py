"""
Vista del Dashboard Analítico y Trazabilidad de Glosas
Consume la API REST de Glosaap (servidor mercurio / BD glosapp).
Soporta temas claro y oscuro respetando Glosa Flet Theme.
"""
from __future__ import annotations

import threading
from datetime import date, timedelta
from typing import Any

import flet as ft

from app.service.glosapp_api_client import api_client
from app.ui.components.settings_dialog import (
    get_stored_api_credentials,
    show_settings_dialog,
)
from app.ui.styles import SPACING


class AnalyticsDashboardView:
    """Pantalla interactiva de métricas, trazabilidad de glosas y telemetría."""

    def __init__(self, page: ft.Page, on_back=None):
        self.page = page
        self.on_back = on_back
        self.navigation_controller = None

        # Estado local de datos
        self._lotes_data: list[dict[str, Any]] = []
        self._metricas_data: list[dict[str, Any]] = []
        self._eps_list: list[dict[str, Any]] = []
        self._is_loading = False
        self._selected_eps = "TODAS"
        self._selected_rango = "30"  # días por defecto

        # Controles principales
        self._status_badge = ft.Container(
            content=ft.Row([
                ft.Icon(ft.Icons.CIRCLE, size=10, color=ft.Colors.GREY_500),
                ft.Text("Verificando...", size=12, weight=ft.FontWeight.W_500),
            ], spacing=6),
            padding=ft.padding.symmetric(horizontal=10, vertical=4),
            border_radius=12,
            bgcolor=ft.Colors.SURFACE_CONTAINER_HIGHEST,
        )

        self._banner_container = ft.Container(visible=False)
        self._loading_ring = ft.ProgressRing(width=28, height=28, stroke_width=3, visible=False)

        # Contenedores de contenido
        self._kpi_row = ft.Row(spacing=15, wrap=True, alignment=ft.MainAxisAlignment.CENTER)
        self._eps_breakdown_row = ft.Row(spacing=12, wrap=True, alignment=ft.MainAxisAlignment.CENTER)
        self._lotes_table_container = ft.Container()
        self._metricas_container = ft.Container()

        # Selector de pestañas
        self._tabs = ft.Tabs(
            selected_index=0,
            animation_duration=200,
            tabs=[
                ft.Tab(text="📊 Trazabilidad de Glosas", icon=ft.Icons.TABLE_CHART_OUTLINED),
                ft.Tab(text="⚡ Rendimiento y Telemetría", icon=ft.Icons.SPEED_OUTLINED),
            ],
            on_change=self._on_tab_change,
        )
        self._tab_content_area = ft.Container(expand=True)

        self.container = self._build()

    # ==================== CONSTRUCCIÓN DE LA VISTA ====================

    def _build(self) -> ft.Container:
        """Construye la jerarquía visual de la pantalla."""
        # Header superior
        header = ft.Container(
            content=ft.Row([
                ft.IconButton(
                    icon=ft.Icons.ARROW_BACK,
                    tooltip="Volver al menú principal",
                    on_click=lambda e: self._handle_back(),
                ),
                ft.Column([
                    ft.Row([
                        ft.Text("Dashboard Analítico", size=22, weight=ft.FontWeight.BOLD),
                        self._status_badge,
                    ], spacing=10, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                    ft.Text(
                        "Trazabilidad de glosas, facturas y telemetría de procesamiento en tiempo real",
                        size=12,
                        color=ft.Colors.ON_SURFACE_VARIANT,
                    ),
                ], spacing=2, expand=True),
                self._loading_ring,
                ft.ElevatedButton(
                    content=ft.Row([
                        ft.Icon(ft.Icons.REFRESH, size=16),
                        ft.Text("Actualizar", size=12),
                    ], spacing=4),
                    on_click=lambda e: self.refresh_data(),
                ),
                ft.OutlinedButton(
                    content=ft.Row([
                        ft.Icon(ft.Icons.KEY, size=16),
                        ft.Text("Configurar API", size=12),
                    ], spacing=4),
                    on_click=lambda e: self._open_api_settings(),
                ),
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN, vertical_alignment=ft.CrossAxisAlignment.CENTER),
            padding=ft.padding.symmetric(horizontal=SPACING["md"], vertical=8),
        )

        # Barra de filtros
        self._eps_dropdown = ft.Dropdown(
            label="EPS",
            value="TODAS",
            options=[ft.dropdown.Option("TODAS", "Todas las EPS")],
            dense=True,
            width=200,
            text_size=12,
            on_change=self._on_filter_changed,
        )

        self._rango_dropdown = ft.Dropdown(
            label="Periodo",
            value="30",
            options=[
                ft.dropdown.Option("7", "Últimos 7 días"),
                ft.dropdown.Option("15", "Últimos 15 días"),
                ft.dropdown.Option("30", "Últimos 30 días"),
                ft.dropdown.Option("90", "Últimos 3 meses"),
                ft.dropdown.Option("ALL", "Todo el histórico"),
            ],
            dense=True,
            width=180,
            text_size=12,
            on_change=self._on_filter_changed,
        )

        filters_bar = ft.Container(
            content=ft.Row([
                ft.Icon(ft.Icons.FILTER_LIST, size=18, color=ft.Colors.PRIMARY),
                ft.Text("Filtros:", size=13, weight=ft.FontWeight.W_600),
                self._eps_dropdown,
                self._rango_dropdown,
                ft.Container(expand=True),
            ], spacing=12, vertical_alignment=ft.CrossAxisAlignment.CENTER),
            padding=ft.padding.symmetric(horizontal=SPACING["md"], vertical=6),
            bgcolor=ft.Colors.SURFACE_CONTAINER_HIGHEST,
            border_radius=10,
        )

        body = ft.Column([
            header,
            ft.Divider(height=1),
            self._banner_container,
            filters_bar,
            ft.Container(height=8),
            self._kpi_row,
            ft.Container(height=12),
            self._tabs,
            ft.Container(height=8),
            self._tab_content_area,
        ], expand=True, spacing=6, scroll=ft.ScrollMode.AUTO)

        return ft.Container(
            content=body,
            bgcolor=ft.Colors.SURFACE,
            expand=True,
            padding=SPACING["md"],
            visible=False,
        )

    # ==================== MANEJO DE ESTADO Y DATOS ====================

    def show(self):
        """Muestra la vista y refresca datos automáticamente."""
        self.container.visible = True
        url, key = get_stored_api_credentials(self.page)
        api_client.update_credentials(base_url=url, api_key=key)
        self.refresh_data()
        try:
            self.page.update()
        except Exception:
            pass

    def hide(self):
        """Oculta la vista."""
        self.container.visible = False
        try:
            self.page.update()
        except Exception:
            pass

    def _handle_back(self):
        """Retrocede al dashboard vía NavigationController o callback."""
        if self.navigation_controller is not None:
            self.navigation_controller.go_to("dashboard")
        elif callable(self.on_back):
            self.on_back()

    def _open_api_settings(self):
        """Abre el modal de configuración de la API."""
        show_settings_dialog(
            self.page,
            on_api_change=lambda: self.refresh_data(),
        )

    def _on_filter_changed(self, e):
        """Maneja el cambio de filtros sin recargar de la red si no es necesario."""
        self._selected_eps = str(self._eps_dropdown.value or "TODAS")
        self._selected_rango = str(self._rango_dropdown.value or "30")
        self.refresh_data()

    def _on_tab_change(self, e):
        """Cambia entre la pestaña de Glosas y la de Rendimiento."""
        self._render_active_tab()
        try:
            self.page.update()
        except Exception:
            pass

    def refresh_data(self):
        """Inicia la carga de datos en segundo plano sin congelar la UI."""
        if self._is_loading:
            return
        self._is_loading = True
        self._loading_ring.visible = True
        try:
            self.page.update()
        except Exception:
            pass

        threading.Thread(target=self._fetch_data_worker, daemon=True).start()

    def _fetch_data_worker(self):
        """Hilo de fondo que consulta la API REST."""
        url, key = get_stored_api_credentials(self.page)
        api_client.update_credentials(base_url=url, api_key=key)

        # 1. Comprobar salud y validez de clave
        if not key:
            status_kind = "no_key"
            error_msg = "No has configurado tu X-API-Key todavía."
            lotes_res = {"items": []}
            metricas_res = []
            eps_res = []
        else:
            val = api_client.validate_key()
            if not val.get("valid"):
                status_kind = "auth_error" if val.get("status_code") == 401 else "error"
                error_msg = val.get("message", "Error de conexión con la API")
                lotes_res = {"items": []}
                metricas_res = []
                eps_res = []
            else:
                status_kind = "ok"
                error_msg = ""
                # Calcular rango de fechas
                desde_str = None
                hasta_str = date.today().isoformat()
                if self._selected_rango.isdigit():
                    dias = int(self._selected_rango)
                    desde_str = (date.today() - timedelta(days=dias)).isoformat()

                eps_filter = None if self._selected_eps == "TODAS" else self._selected_eps

                # Consultar en paralelo o secuencial
                eps_res = api_client.get_eps(activo=None)
                lotes_res = api_client.get_lotes(
                    limit=200,
                    desde=desde_str,
                    hasta=hasta_str,
                    codigo_eps=eps_filter,
                )
                metricas_res = api_client.get_metricas_resumen(desde=desde_str, hasta=hasta_str)

        # Actualizar datos en memoria
        self._eps_list = eps_res or []
        self._lotes_data = lotes_res.get("items", [])
        self._metricas_data = metricas_res or []

        # Enviar resultados al hilo principal
        self._apply_data_to_ui(status_kind, error_msg)

    def _apply_data_to_ui(self, status_kind: str, error_msg: str):
        """Actualiza todos los componentes de Flet en el hilo seguro."""
        self._is_loading = False
        self._loading_ring.visible = False

        # Actualizar opciones del dropdown de EPS si llegaron nuevas
        if self._eps_list:
            options = [ft.dropdown.Option("TODAS", "Todas las EPS")]
            for eps in self._eps_list:
                cod = str(eps.get("codigo_eps") or "").upper()
                nom = eps.get("nombre_eps") or cod
                options.append(ft.dropdown.Option(cod, f"{cod} — {nom}"))
            self._eps_dropdown.options = options

        # 1. Status badge
        if status_kind == "ok":
            self._status_badge.content = ft.Row([
                ft.Icon(ft.Icons.CHECK_CIRCLE, size=12, color=ft.Colors.GREEN_600),
                ft.Text("Conectado (10.10.10.18:8081)", size=12, color=ft.Colors.GREEN_700, weight=ft.FontWeight.W_600),
            ], spacing=6)
            self._status_badge.bgcolor = ft.Colors.GREEN_50
            self._banner_container.visible = False
        elif status_kind == "no_key":
            self._status_badge.content = ft.Row([
                ft.Icon(ft.Icons.KEY_OFF, size=12, color=ft.Colors.AMBER_800),
                ft.Text("Sin API Key", size=12, color=ft.Colors.AMBER_900, weight=ft.FontWeight.W_600),
            ], spacing=6)
            self._status_badge.bgcolor = ft.Colors.AMBER_50
            self._show_banner(
                "🔑 Configuración requerida: Ingresa tu X-API-Key para conectarte a la base de datos de Glosaap.",
                is_key_prompt=True,
            )
        else:
            self._status_badge.content = ft.Row([
                ft.Icon(ft.Icons.ERROR, size=12, color=ft.Colors.ERROR),
                ft.Text("Desconectado", size=12, color=ft.Colors.ERROR, weight=ft.FontWeight.W_600),
            ], spacing=6)
            self._status_badge.bgcolor = ft.Colors.RED_50
            self._show_banner(f"⚠️ {error_msg}. Verifica que estés conectado a la red interna de la clínica.")

        # 2. Renderizar KPIs y pestañas
        self._render_kpis()
        self._render_active_tab()

        try:
            self.page.update()
        except Exception:
            pass

    def _show_banner(self, message: str, is_key_prompt: bool = False):
        """Muestra un banner amigable arriba del contenido."""
        actions = []
        if is_key_prompt:
            actions.append(
                ft.ElevatedButton(
                    "Ingresar API-Key ahora",
                    icon=ft.Icons.KEY,
                    on_click=lambda e: self._open_api_settings(),
                )
            )

        self._banner_container.content = ft.Container(
            content=ft.Row([
                ft.Icon(ft.Icons.INFO_OUTLINE, color=ft.Colors.PRIMARY, size=24),
                ft.Text(message, size=13, expand=True),
                *actions,
            ], spacing=12, vertical_alignment=ft.CrossAxisAlignment.CENTER),
            padding=ft.padding.symmetric(horizontal=16, vertical=12),
            bgcolor=ft.Colors.SURFACE_CONTAINER_HIGHEST,
            border_radius=10,
            border=ft.border.all(1, ft.Colors.OUTLINE_VARIANT),
        )
        self._banner_container.visible = True

    # ==================== RENDERIZADO DE COMPONENTES ====================

    def _format_money(self, val: float | int | None) -> str:
        """Formatea cifras en pesos colombianos con separador de miles."""
        try:
            num = float(val or 0.0)
            return f"${num:,.0f}".replace(",", ".")
        except Exception:
            return "$0"

    def _render_kpis(self):
        """Calcula y muestra las 5 tarjetas de KPI consolidadas."""
        total_lotes = len(self._lotes_data)
        total_facturas = sum(int(lote.get("total_facturas") or 0) for lote in self._lotes_data)
        total_glosado = sum(float(lote.get("valor_total_objetado") or 0.0) for lote in self._lotes_data)
        total_facturado = sum(float(lote.get("valor_total_facturado") or 0.0) for lote in self._lotes_data)

        # Tasa de homologación ponderada
        tasas = [float(lote.get("tasa_homologacion_pct") or 0.0) for lote in self._lotes_data if lote.get("tasa_homologacion_pct") is not None]
        prom_homologacion = (sum(tasas) / len(tasas)) if tasas else 0.0

        def kpi_card(title: str, value: str, subtitle: str, icon, color=None):
            return ft.Card(
                content=ft.Container(
                    content=ft.Column([
                        ft.Row([
                            ft.Text(title, size=12, color=ft.Colors.ON_SURFACE_VARIANT, weight=ft.FontWeight.W_500),
                            ft.Icon(icon, size=18, color=color or ft.Colors.PRIMARY),
                        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                        ft.Container(height=4),
                        ft.Text(value, size=20, weight=ft.FontWeight.BOLD, color=ft.Colors.ON_SURFACE),
                        ft.Text(subtitle, size=11, color=ft.Colors.ON_SURFACE_VARIANT),
                    ], spacing=2, tight=True),
                    padding=14,
                    width=190,
                ),
                elevation=2,
            )

        pct_glosado = (total_glosado / total_facturado * 100) if total_facturado > 0 else 0.0

        self._kpi_row.controls = [
            kpi_card("Lotes Procesados", str(total_lotes), "Corridas registradas", ft.Icons.ALL_INBOX, ft.Colors.BLUE_600),
            kpi_card("Facturas Auditadas", f"{total_facturas:,}".replace(",", "."), "Cuentas médicas", ft.Icons.RECEIPT_LONG, ft.Colors.INDIGO_600),
            kpi_card("Total Facturado", self._format_money(total_facturado), "Base de facturación", ft.Icons.ATTACH_MONEY, ft.Colors.TEAL_600),
            kpi_card("Total Objetado", self._format_money(total_glosado), f"{pct_glosado:.1f}% del total facturado", ft.Icons.MONEY_OFF, ft.Colors.RED_600),
            kpi_card("Homologación DGH", f"{prom_homologacion:.1f}%", "Efectividad de cruce", ft.Icons.TASK_ALT, ft.Colors.GREEN_600),
        ]

    def _render_active_tab(self):
        """Renderiza la pestaña seleccionada."""
        idx = self._tabs.selected_index
        if idx == 0:
            self._tab_content_area.content = self._render_glosas_tab()
        else:
            self._tab_content_area.content = self._render_metricas_tab()

    def _render_glosas_tab(self) -> ft.Control:
        """Pestaña 1: Resumen por EPS y tabla de lotes."""
        # 1. Resumen por EPS
        eps_stats: dict[str, dict[str, Any]] = {}
        for lote in self._lotes_data:
            cod = str(lote.get("codigo_eps") or "OTRA").upper()
            if cod not in eps_stats:
                eps_stats[cod] = {"lotes": 0, "facturas": 0, "objetado": 0.0, "facturado": 0.0}
            eps_stats[cod]["lotes"] += 1
            eps_stats[cod]["facturas"] += int(lote.get("total_facturas") or 0)
            eps_stats[cod]["objetado"] += float(lote.get("valor_total_objetado") or 0.0)
            eps_stats[cod]["facturado"] += float(lote.get("valor_total_facturado") or 0.0)

        eps_cards = []
        for cod, st in eps_stats.items():
            eps_cards.append(
                ft.Container(
                    content=ft.Column([
                        ft.Row([
                            ft.Text(cod, size=14, weight=ft.FontWeight.BOLD, color=ft.Colors.PRIMARY),
                            ft.Text(f"{st['lotes']} lotes", size=11, color=ft.Colors.ON_SURFACE_VARIANT),
                        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                        ft.Container(height=4),
                        ft.Text(f"Objetado: {self._format_money(st['objetado'])}", size=13, weight=ft.FontWeight.W_600),
                        ft.Text(f"Facturas: {st['facturas']}", size=11, color=ft.Colors.ON_SURFACE_VARIANT),
                    ], spacing=2, tight=True),
                    padding=12,
                    border_radius=10,
                    bgcolor=ft.Colors.SURFACE_CONTAINER_HIGHEST,
                    border=ft.border.all(1, ft.Colors.OUTLINE_VARIANT),
                    width=210,
                )
            )

        eps_section = ft.Column([
            ft.Text("Distribución por Entidad (EPS)", size=14, weight=ft.FontWeight.W_600),
            ft.Row(eps_cards, wrap=True, spacing=10) if eps_cards else ft.Text("No hay datos para mostrar", size=12, italic=True),
        ], spacing=8)

        # 2. Tabla de lotes
        rows = []
        for lote in self._lotes_data[:50]:  # Mostrar los primeros 50
            f_ingesta = str(lote.get("fecha_ingesta") or "")[:16].replace("T", " ")
            cod_eps = str(lote.get("codigo_eps") or "")
            origen = str(lote.get("origen") or "")
            facts = str(lote.get("total_facturas") or 0)
            glosado = self._format_money(lote.get("valor_total_objetado"))
            homol = f"{float(lote.get('tasa_homologacion_pct') or 0):.1f}%"
            archivo = str(lote.get("nombre_archivo_objeciones") or "N/A")

            rows.append(
                ft.DataRow(
                    cells=[
                        ft.DataCell(ft.Text(str(lote.get("id_lote")), weight=ft.FontWeight.BOLD, size=11)),
                        ft.DataCell(ft.Text(f_ingesta, size=11)),
                        ft.DataCell(ft.Text(cod_eps, weight=ft.FontWeight.W_600, size=11)),
                        ft.DataCell(ft.Text(origen, size=11)),
                        ft.DataCell(ft.Text(facts, size=11)),
                        ft.DataCell(ft.Text(glosado, weight=ft.FontWeight.W_600, size=11)),
                        ft.DataCell(ft.Text(homol, size=11)),
                        ft.DataCell(ft.Text(archivo, size=11, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS)),
                    ]
                )
            )

        table = ft.DataTable(
            columns=[
                ft.DataColumn(ft.Text("ID", size=12, weight=ft.FontWeight.BOLD)),
                ft.DataColumn(ft.Text("Fecha/Hora", size=12, weight=ft.FontWeight.BOLD)),
                ft.DataColumn(ft.Text("EPS", size=12, weight=ft.FontWeight.BOLD)),
                ft.DataColumn(ft.Text("Origen", size=12, weight=ft.FontWeight.BOLD)),
                ft.DataColumn(ft.Text("Facturas", size=12, weight=ft.FontWeight.BOLD)),
                ft.DataColumn(ft.Text("Total Objetado", size=12, weight=ft.FontWeight.BOLD)),
                ft.DataColumn(ft.Text("Homologado", size=12, weight=ft.FontWeight.BOLD)),
                ft.DataColumn(ft.Text("Archivo Objeciones", size=12, weight=ft.FontWeight.BOLD)),
            ],
            rows=rows,
            border_radius=8,
            heading_row_color=ft.Colors.SURFACE_CONTAINER_HIGHEST,
        )

        lotes_section = ft.Column([
            ft.Row([
                ft.Text("Historial de Lotes Procesados", size=14, weight=ft.FontWeight.W_600),
                ft.Text(f"Mostrando {len(rows)} de {len(self._lotes_data)} lotes", size=11, color=ft.Colors.ON_SURFACE_VARIANT),
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            ft.Container(
                content=ft.Row([table], scroll=ft.ScrollMode.AUTO),
                border=ft.border.all(1, ft.Colors.OUTLINE_VARIANT),
                border_radius=10,
                padding=8,
            ) if rows else ft.Container(
                content=ft.Text("No se encontraron lotes registrados para los filtros actuales.", size=12, italic=True),
                padding=20,
            ),
        ], spacing=8)

        return ft.Column([
            eps_section,
            ft.Container(height=10),
            lotes_section,
        ], spacing=12)

    def _render_metricas_tab(self) -> ft.Control:
        """Pestaña 2: Rendimiento y telemetría de tiempos."""
        if not self._metricas_data:
            return ft.Container(
                content=ft.Column([
                    ft.Icon(ft.Icons.SPEED, size=40, color=ft.Colors.ON_SURFACE_VARIANT),
                    ft.Text("No hay mediciones de rendimiento registradas en este periodo.", size=13),
                    ft.Text("A medida que proceses glosas o descargues correos, los tiempos de ejecución aparecerán aquí.", size=11, color=ft.Colors.ON_SURFACE_VARIANT),
                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=6),
                alignment=ft.alignment.center,
                padding=30,
            )

        rows = []
        for m in self._metricas_data:
            mod = str(m.get("modulo") or "")
            fase = str(m.get("fase_operacion") or "")
            meds = str(m.get("mediciones") or 0)
            fallidas = str(m.get("fallidas") or 0)
            dur_prom = f"{float(m.get('duracion_promedio_seg') or 0.0):.2f}s"
            dur_max = f"{float(m.get('duracion_maxima_seg') or 0.0):.2f}s"
            ms_item = f"{float(m.get('ms_por_item_promedio') or 0.0):.1f} ms"

            rows.append(
                ft.DataRow(
                    cells=[
                        ft.DataCell(ft.Text(mod, weight=ft.FontWeight.W_600, size=11)),
                        ft.DataCell(ft.Text(fase, size=11)),
                        ft.DataCell(ft.Text(meds, size=11)),
                        ft.DataCell(ft.Text(fallidas, size=11, color=ft.Colors.ERROR if int(fallidas) > 0 else None)),
                        ft.DataCell(ft.Text(dur_prom, size=11, weight=ft.FontWeight.W_600)),
                        ft.DataCell(ft.Text(dur_max, size=11)),
                        ft.DataCell(ft.Text(ms_item, size=11)),
                    ]
                )
            )

        table = ft.DataTable(
            columns=[
                ft.DataColumn(ft.Text("Módulo", size=12, weight=ft.FontWeight.BOLD)),
                ft.DataColumn(ft.Text("Fase Operativa", size=12, weight=ft.FontWeight.BOLD)),
                ft.DataColumn(ft.Text("Mediciones", size=12, weight=ft.FontWeight.BOLD)),
                ft.DataColumn(ft.Text("Fallidas", size=12, weight=ft.FontWeight.BOLD)),
                ft.DataColumn(ft.Text("Duración Promedio", size=12, weight=ft.FontWeight.BOLD)),
                ft.DataColumn(ft.Text("Duración Máxima", size=12, weight=ft.FontWeight.BOLD)),
                ft.DataColumn(ft.Text("ms / Ítem Promedio", size=12, weight=ft.FontWeight.BOLD)),
            ],
            rows=rows,
            border_radius=8,
            heading_row_color=ft.Colors.SURFACE_CONTAINER_HIGHEST,
        )

        return ft.Column([
            ft.Text("Telemetría de Rendimiento por Módulo y Fase Operativa", size=14, weight=ft.FontWeight.W_600),
            ft.Container(
                content=ft.Row([table], scroll=ft.ScrollMode.AUTO),
                border=ft.border.all(1, ft.Colors.OUTLINE_VARIANT),
                border_radius=10,
                padding=8,
            ),
        ], spacing=8)
