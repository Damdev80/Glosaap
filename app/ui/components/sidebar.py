"""
Barra lateral de navegación persistente (Sidebar) de Glosaap.
Permanece visible en todo momento tras el inicio de sesión.
Diseño moderno tipo SaaS, cero emojis, soporte de temas claro/oscuro y Material 3.
"""
from __future__ import annotations

import threading
from collections.abc import Callable

import flet as ft

from app.config.settings import APP_VERSION
from app.ui.components.alert_dialog import AlertDialog


class AppSidebar:
    """Sidebar de navegación persistente en toda la aplicación."""

    def __init__(
        self,
        page: ft.Page,
        on_dashboard_click: Callable | None = None,
        on_glosas_click: Callable | None = None,
        on_web_download_click: Callable | None = None,
        on_tools_click: Callable | None = None,
        on_settings_click: Callable | None = None,
        on_guide_click: Callable | None = None,
        on_logout_click: Callable | None = None,
        on_check_updates_click: Callable | None = None,
    ):
        self.page = page
        self.on_dashboard_click = on_dashboard_click
        self.on_glosas_click = on_glosas_click
        self.on_web_download_click = on_web_download_click
        self.on_tools_click = on_tools_click
        self.on_settings_click = on_settings_click
        self.on_guide_click = on_guide_click
        self.on_logout_click = on_logout_click
        self.on_check_updates_click = on_check_updates_click

        self.current_active_key = "dashboard"

        # Referencias de controles para actualización de estado activo
        self._nav_items: dict[str, ft.Container] = {}
        self._nav_icons: dict[str, ft.Icon] = {}
        self._nav_texts: dict[str, ft.Text] = {}

        # Botón / Card de Glosas (para flash de guía)
        self._glosas_card: ft.Card | None = None
        self._glosas_btn: ft.Container | None = None

        self.container = self._build()

    def _create_nav_item(
        self,
        key: str,
        label: str,
        icon,
        on_click: Callable | None,
        is_active: bool = False,
    ) -> ft.Container:
        """Crea un elemento interactivo de navegación para el sidebar."""
        fg = ft.Colors.ON_PRIMARY_CONTAINER if is_active else ft.Colors.ON_SURFACE
        bg = ft.Colors.PRIMARY_CONTAINER if is_active else None
        weight = ft.FontWeight.W_600 if is_active else ft.FontWeight.W_400

        icon_ctrl = ft.Icon(icon, size=20, color=fg)
        text_ctrl = ft.Text(label, size=13, weight=weight, color=fg)

        self._nav_icons[key] = icon_ctrl
        self._nav_texts[key] = text_ctrl

        def _handle_click(e):
            if on_click:
                on_click()

        item = ft.Container(
            content=ft.Row([
                icon_ctrl,
                text_ctrl,
            ], spacing=12, vertical_alignment=ft.CrossAxisAlignment.CENTER),
            padding=ft.padding.symmetric(horizontal=14, vertical=10),
            border_radius=8,
            bgcolor=bg,
            ink=True,
            on_click=_handle_click,
        )

        self._nav_items[key] = item
        return item

    def _build(self) -> ft.Container:
        """Construye la estructura completa del sidebar."""
        # 1. Cabecera institucional
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

        # 2. Ítems principales de navegación
        btn_dashboard = self._create_nav_item(
            key="dashboard",
            label="Dashboard",
            icon=ft.Icons.DASHBOARD_ROUNDED,
            on_click=self.on_dashboard_click,
            is_active=True,
        )

        btn_glosas = self._create_nav_item(
            key="glosas",
            label="Gestion de Glosas",
            icon=ft.Icons.DESCRIPTION_OUTLINED,
            on_click=self.on_glosas_click,
        )
        self._glosas_btn = btn_glosas
        self._glosas_card = ft.Card(content=btn_glosas, elevation=0, color=None)

        btn_web = self._create_nav_item(
            key="web",
            label="Descarga Web",
            icon=ft.Icons.CLOUD_DOWNLOAD_OUTLINED,
            on_click=self.on_web_download_click,
        )

        btn_tools = self._create_nav_item(
            key="tools",
            label="Herramientas",
            icon=ft.Icons.BUILD_OUTLINED,
            on_click=self.on_tools_click,
        )

        # 3. Acciones inferiores
        btn_settings = self._create_nav_item(
            key="settings",
            label="Configuracion",
            icon=ft.Icons.SETTINGS_OUTLINED,
            on_click=self.on_settings_click,
        )

        btn_guide = self._create_nav_item(
            key="guide",
            label="Guia de uso",
            icon=ft.Icons.HELP_OUTLINE,
            on_click=self.on_guide_click,
        )

        btn_logout = self._create_nav_item(
            key="logout",
            label="Cerrar sesion",
            icon=ft.Icons.LOGOUT_ROUNDED,
            on_click=lambda: self._confirm_logout(),
        )

        version_label = ft.Container(
            content=ft.TextButton(
                content=ft.Row([
                    ft.Icon(ft.Icons.INFO_OUTLINE, size=12, color=ft.Colors.ON_SURFACE_VARIANT),
                    ft.Text(f"v{APP_VERSION}", size=11, color=ft.Colors.ON_SURFACE_VARIANT),
                ], spacing=4),
                on_click=lambda e: self._check_updates(),
                tooltip="Buscar actualizaciones",
            ),
            padding=ft.padding.only(left=8, bottom=8),
        )

        sidebar_content = ft.Column([
            sidebar_brand,
            ft.Divider(height=1),
            ft.Container(height=4),
            btn_dashboard,
            self._glosas_card,
            btn_web,
            btn_tools,
            ft.Container(expand=True),
            ft.Divider(height=1),
            btn_settings,
            btn_guide,
            btn_logout,
            version_label,
        ], spacing=4, expand=True)

        return ft.Container(
            content=sidebar_content,
            width=230,
            bgcolor=ft.Colors.SURFACE_CONTAINER_LOW if hasattr(ft.Colors, "SURFACE_CONTAINER_LOW") else ft.Colors.SURFACE,
            border=ft.border.only(right=ft.BorderSide(1, ft.Colors.OUTLINE_VARIANT)),
            padding=ft.padding.all(6),
        )

    def set_active(self, view_name: str) -> None:
        """Actualiza visualmente el botón activo del sidebar."""
        mapping = {
            "dashboard": "dashboard",
            "analytics": "dashboard",
            "eps": "glosas",
            "messages": "glosas",
            "web_download": "web",
            "tools": "tools",
            "homologacion": "tools",
            "mix_excel": "tools",
            "homologador_manual": "tools",
        }
        target_key = mapping.get(view_name, "dashboard")
        self.current_active_key = target_key

        for key, item in self._nav_items.items():
            is_active = (key == target_key)
            fg = ft.Colors.ON_PRIMARY_CONTAINER if is_active else ft.Colors.ON_SURFACE
            bg = ft.Colors.PRIMARY_CONTAINER if is_active else None
            weight = ft.FontWeight.W_600 if is_active else ft.FontWeight.W_400

            item.bgcolor = bg
            if key in self._nav_icons:
                self._nav_icons[key].color = fg
            if key in self._nav_texts:
                self._nav_texts[key].color = fg
                self._nav_texts[key].weight = weight

        try:
            self.page.update()
        except Exception:
            pass

    def flash_glosas(self, duration: float = 1.4) -> None:
        """Efecto flash en 'Gestion de Glosas' para el tour interactivo."""
        card = self._glosas_card
        btn = self._glosas_btn
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

        timer = threading.Timer(duration, self._end_flash, args=(revert,))
        timer.daemon = True
        timer.start()

    def _end_flash(self, revert) -> None:
        try:
            revert()
            self.page.update()
        except Exception:
            pass

    def _confirm_logout(self) -> None:
        """Confirmación de diálogo antes de cerrar sesión."""
        def do_logout(ev):
            if self.on_logout_click:
                self.on_logout_click()

        AlertDialog.show_confirm(
            self.page,
            title="Cerrar sesion",
            message="¿Deseas cerrar la sesion actual?",
            confirm_text="Cerrar sesion",
            cancel_text="Cancelar",
            on_confirm=do_logout,
        )

    def _check_updates(self) -> None:
        """Lanza la verificación de actualizaciones."""
        if self.on_check_updates_click:
            self.on_check_updates_click()
