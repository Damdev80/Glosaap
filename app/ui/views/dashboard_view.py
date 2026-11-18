"""
Vista principal del Dashboard Analitico de Glosaap.
Primer pantalla visible inmediatamente despues del inicio de sesion.
Cero emojis, diseno moderno con tarjetas KPI, telemetria y esqueletos de carga.
"""
from __future__ import annotations

import threading
from collections.abc import Callable

import flet as ft

from app.ui.views.analytics_dashboard_view import AnalyticsDashboardView


class DashboardView:
    """Vista principal con Dashboard Analitico integrado como pantalla de inicio."""

    def __init__(
        self,
        page: ft.Page,
        assets_dir: str,
        on_card_click: Callable | None = None,
        on_tools_click: Callable | None = None,
        on_logout: Callable | None = None,
        on_web_download: Callable | None = None,
        on_guide: Callable | None = None,
        on_analytics_click: Callable | None = None,
        sidebar=None,
    ):
        self.page = page
        self.assets_dir = assets_dir
        self.on_card_click = on_card_click
        self.on_tools_click = on_tools_click
        self.on_logout = on_logout
        self.on_web_download = on_web_download
        self.on_guide = on_guide
        self.on_analytics_click = on_analytics_click
        self.sidebar = sidebar

        # Vista analítica completa como contenido del dashboard de inicio
        self.analytics_view = AnalyticsDashboardView(
            page=page,
            show_back_button=False,  # Dashboard raíz no requiere retroceso
        )
        self.container = self.analytics_view.container

        # Compatibilidad con tests y componentes de guía
        if self.sidebar and hasattr(self.sidebar, "_glosas_card") and self.sidebar._glosas_card:
            self._manejar_card = self.sidebar._glosas_card
        else:
            self._manejar_card = ft.Card(content=ft.Container(), elevation=0)

    def flash_manejar(self, duration: float = 1.4) -> None:
        """Resalta la opción Gestión de Glosas (para el tour guiado y tests)."""
        if self.sidebar and hasattr(self.sidebar, "flash_glosas"):
            self.sidebar.flash_glosas(duration=duration)
            return

        card = getattr(self, "_manejar_card", None)
        if not card:
            return

        prev_color = getattr(card, "color", None)
        card.color = ft.Colors.PRIMARY_CONTAINER
        try:
            self.page.update()
        except Exception:
            return

        def revert():
            card.color = prev_color
            try:
                self.page.update()
            except Exception:
                pass

        timer = threading.Timer(duration, revert)
        timer.daemon = True
        timer.start()

    def show(self) -> None:
        """Muestra el dashboard analítico y actualiza datos."""
        self.container.visible = True
        if hasattr(self.analytics_view, "refresh_data"):
            try:
                self.analytics_view.refresh_data()
            except Exception:
                pass

    def hide(self) -> None:
        """Oculta el contenedor del dashboard."""
        self.container.visible = False
