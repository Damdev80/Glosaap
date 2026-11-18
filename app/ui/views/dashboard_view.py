"""
Vista principal de la aplicacion con Sidebar lateral y Dashboard Analitico integrado.
Diseno profesional tipo SaaS sin emojis, con soporte de temas claro/oscuro.
"""
from __future__ import annotations

import threading
from collections.abc import Callable

import flet as ft

from app.config.settings import APP_VERSION
from app.ui.components.alert_dialog import AlertDialog
from app.ui.components.loading_overlay import LoadingOverlay, ToastNotification
from app.ui.components.settings_dialog import show_settings_dialog
from app.ui.views.analytics_dashboard_view import AnalyticsDashboardView


class DashboardView:
    """Vista principal con Sidebar de navegacion y Dashboard Analitico como inicio."""

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
    ):
        self.page = page
        self.assets_dir = assets_dir
        self.on_card_click = on_card_click
        self.on_tools_click = on_tools_click
        self.on_logout = on_logout
        self.on_web_download = on_web_download
        self.on_guide = on_guide
        self.on_analytics_click = on_analytics_click

        # Componentes de feedback
        self.loading_overlay = LoadingOverlay(page)
        self.toast = ToastNotification(page)

        # Vista analítica embebida como pantalla principal
        self.analytics_view = AnalyticsDashboardView(
            page=page,
            show_back_button=False,
        )

        self.container = self._build()

    # ==================== CONSTRUCCIÓN DE LA VISTA ====================

    def _build(self) -> ft.Container:
        """Construye la estructura con Sidebar y Contenido Principal."""
        # 1. Cabecera del Sidebar
        sidebar_brand = ft.Container(
            content=ft.Row([
                ft.Icon(ft.Icons.LOCAL_HOSPITAL, size=28, color=ft.Colors.PRIMARY),
                ft.Column([
                    ft.Text("Glosaap", size=18, weight=ft.FontWeight.BOLD),
                    ft.Text("Clinica La Concepcion", size=11, color=ft.Colors.ON_SURFACE_VARIANT),
                ], spacing=1),
            ], spacing=10, vertical_alignment=ft.CrossAxisAlignment.CENTER),
            padding=ft.padding.only(left=12, right=12, top=16, bottom=14),
        )

        # 2. Botones de Navegación del Sidebar
        def nav_item(label: str, icon, on_click, is_active: bool = False):
            bg = ft.Colors.PRIMARY_CONTAINER if is_active else None
            fg = ft.Colors.ON_PRIMARY_CONTAINER if is_active else ft.Colors.ON_SURFACE
            weight = ft.FontWeight.W_600 if is_active else ft.FontWeight.W_400
            return ft.Container(
                content=ft.Row([
                    ft.Icon(icon, size=20, color=fg),
                    ft.Text(label, size=13, weight=weight, color=fg),
                ], spacing=12),
                padding=ft.padding.symmetric(horizontal=14, vertical=10),
                border_radius=8,
                bgcolor=bg,
                ink=True,
                on_click=on_click,
            )

        btn_dashboard = nav_item(
            "Dashboard",
            ft.Icons.DASHBOARD_ROUNDED,
            lambda e: self.analytics_view.refresh_data(),
            is_active=True,
        )

        def go_manejar(e):
            if self.on_card_click:
                self.on_card_click("manejar")

        btn_glosas = nav_item(
            "Gestion de Glosas",
            ft.Icons.DESCRIPTION_OUTLINED,
            go_manejar,
        )
        self._manejar_card = ft.Card(content=btn_glosas, elevation=0, color=None)
        self._manejar_nav_btn = btn_glosas

        btn_web = nav_item(
            "Descarga Web",
            ft.Icons.CLOUD_DOWNLOAD_OUTLINED,
            lambda e: self.on_web_download() if self.on_web_download else None,
        )

        btn_tools = nav_item(
            "Herramientas",
            ft.Icons.BUILD_OUTLINED,
            lambda e: self.on_tools_click() if self.on_tools_click else None,
        )

        # 3. Pie del Sidebar
        btn_settings = nav_item(
            "Configuracion",
            ft.Icons.SETTINGS_OUTLINED,
            lambda e: self._open_settings(e),
        )

        btn_guide = nav_item(
            "Guia de uso",
            ft.Icons.HELP_OUTLINE,
            lambda e: self.on_guide() if self.on_guide else None,
        )

        btn_logout = nav_item(
            "Cerrar sesion",
            ft.Icons.LOGOUT_ROUNDED,
            lambda e: self._confirm_logout(e),
        )

        version_label = ft.Container(
            content=ft.TextButton(
                content=ft.Row([
                    ft.Icon(ft.Icons.INFO_OUTLINE, size=12, color=ft.Colors.ON_SURFACE_VARIANT),
                    ft.Text(f"v{APP_VERSION}", size=11, color=ft.Colors.ON_SURFACE_VARIANT),
                ], spacing=4),
                on_click=lambda e: self._check_updates(e),
                tooltip="Buscar actualizaciones",
            ),
            padding=ft.padding.only(left=8, bottom=8),
        )

        # Columna completa del Sidebar
        sidebar_content = ft.Column([
            sidebar_brand,
            ft.Divider(height=1),
            ft.Container(height=4),
            btn_dashboard,
            self._manejar_card,
            btn_web,
            btn_tools,
            ft.Container(expand=True),
            ft.Divider(height=1),
            btn_settings,
            btn_guide,
            btn_logout,
            version_label,
        ], spacing=4, expand=True)

        sidebar_container = ft.Container(
            content=sidebar_content,
            width=230,
            bgcolor=ft.Colors.SURFACE_CONTAINER_LOW if hasattr(ft.Colors, "SURFACE_CONTAINER_LOW") else ft.Colors.SURFACE,
            border=ft.border.only(right=ft.BorderSide(1, ft.Colors.OUTLINE_VARIANT)),
            padding=ft.padding.all(6),
        )

        # 4. Área de contenido principal (Dashboard Analítico)
        # Asegurar que el contenedor interno de la vista analítica sea visible
        self.analytics_view.container.visible = True
        main_content_area = ft.Container(
            content=self.analytics_view.container,
            expand=True,
            bgcolor=ft.Colors.SURFACE,
        )

        # Layout horizontal general
        layout = ft.Row([
            sidebar_container,
            main_content_area,
        ], expand=True, spacing=0)

        return ft.Container(
            content=layout,
            bgcolor=ft.Colors.SURFACE,
            expand=True,
            visible=False,
        )

    # ==================== MÉTODOS DE COMPATIBILIDAD ====================

    def flash_manejar(self, duration=1.4):
        """Resalta la opción Gestión de Glosas (focus de la guía)."""
        card = getattr(self, "_manejar_card", None)
        btn = getattr(self, "_manejar_nav_btn", None)
        prev_color = getattr(card, "color", None) if card else None
        prev_bg = getattr(btn, "bgcolor", None) if btn else None

        def apply():
            if card:
                card.color = ft.Colors.PRIMARY_CONTAINER
            if btn:
                btn.bgcolor = ft.Colors.PRIMARY_CONTAINER

        def revert():
            if card:
                card.color = prev_color
            if btn:
                btn.bgcolor = prev_bg

        try:
            apply()
            self.page.update()
        except Exception:
            return
        timer = threading.Timer(duration, self._end_manejar_flash, args=(revert,))
        timer.daemon = True
        timer.start()

    def _end_manejar_flash(self, revert):
        try:
            revert()
            self.page.update()
        except Exception:
            pass

    def _confirm_logout(self, e):
        """Confirmación antes de cerrar sesión."""
        def do_logout(ev):
            if self.on_logout:
                self.on_logout()

        AlertDialog.show_confirm(
            self.page,
            title="Cerrar sesion",
            message="¿Deseas cerrar la sesion actual?",
            confirm_text="Cerrar sesion",
            cancel_text="Cancelar",
            on_confirm=do_logout,
        )

    def _check_updates(self, e):
        """Abre el diálogo de verificación de actualizaciones."""
        try:
            self.show_loading("Verificando actualizaciones...")
            if hasattr(self.page, 'data') and self.page.data:
                check_fn = self.page.data.get('check_updates')
                if check_fn:
                    check_fn()
                else:
                    self.show_toast("Funcion de actualizacion no disponible", "warning")
            else:
                self.show_toast("No se pudo verificar actualizaciones", "error")
        except Exception as ex:
            self.show_toast(f"Error: {ex}", "error")
        finally:
            self.hide_loading()

    def _open_settings(self, e):
        """Abre el panel de configuración."""
        show_settings_dialog(
            self.page,
            on_api_change=lambda: self.analytics_view.refresh_data(),
        )

    def show_loading(self, message: str = "Cargando..."):
        if self.loading_overlay:
            self.loading_overlay.show(message)

    def hide_loading(self):
        if self.loading_overlay:
            self.loading_overlay.hide()

    def show_toast(self, message: str, message_type: str = "info"):
        if self.toast:
            if message_type == "success":
                self.toast.success(message)
            elif message_type == "error":
                self.toast.error(message)
            elif message_type == "warning":
                self.toast.warning(message)
            else:
                self.toast.info(message)

    def rebuild(self):
        """Reconstruye el layout con el tema actual."""
        was_visible = self.container.visible if self.container else False
        self.container = self._build()
        self.container.visible = was_visible
        try:
            self.page.update()
        except Exception:
            pass

    def show(self):
        """Muestra la vista y actualiza los datos del dashboard."""
        if self.container:
            self.container.visible = True
            # Asegurar que el contenido interno de analytics esté visible y refrescado
            self.analytics_view.container.visible = True
            self.analytics_view.refresh_data()
            try:
                self.page.update()
            except Exception:
                pass

    def hide(self):
        """Oculta la vista."""
        if self.container:
            self.container.visible = False
            try:
                self.page.update()
            except Exception:
                pass
