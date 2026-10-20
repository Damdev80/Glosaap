"""Diálogo de configuración canónico de Glosaap.

Fuente única del panel de settings (tema + versión). Lo reutilizan
``app.py`` (botón global) y ``dashboard_view`` (botón local). Usa
``page.open``/``page.close`` (sin ``overlay.clear()`` destructivo) y
``ft.Colors.*`` (sin hex fijo).
"""
import flet as ft

from app.ui.styles import ThemeManager, update_colors
from app.config.settings import APP_VERSION


def show_settings_dialog(page: ft.Page, on_theme_change=None):
    """Abre el diálogo de configuración canónico.

    Args:
        page: Página de Flet.
        on_theme_change: Callback opcional tras cambiar el tema.

    Returns:
        El ``ft.AlertDialog`` abierto.
    """
    is_dark = ThemeManager.is_dark()

    def toggle_theme(ev):
        page.close(settings_dialog)
        ThemeManager.toggle_theme()
        update_colors()
        if on_theme_change is not None:
            try:
                on_theme_change()
            except Exception:
                pass

    settings_dialog = ft.AlertDialog(
        modal=True,
        title=ft.Text("⚙️ Configuración", size=18, weight=ft.FontWeight.W_600),
        content=ft.Container(
            content=ft.Column([
                ft.Text("Apariencia", size=14, weight=ft.FontWeight.W_500),
                ft.Container(height=10),
                ft.Row([
                    ft.Icon(
                        ft.Icons.DARK_MODE if is_dark else ft.Icons.LIGHT_MODE,
                        size=20,
                    ),
                    ft.Text("Modo oscuro", size=13),
                    ft.Container(expand=True),
                    ft.Switch(value=is_dark, on_change=toggle_theme),
                ], alignment=ft.MainAxisAlignment.START),
                ft.Divider(height=20),
                ft.Text("Información", size=14, weight=ft.FontWeight.W_500),
                ft.Container(height=10),
                ft.Row([
                    ft.Icon(ft.Icons.INFO_OUTLINE, size=20),
                    ft.Column([
                        ft.Text(f"Versión: {APP_VERSION}", size=12),
                        ft.Text("Glosaap - Gestión de Glosas", size=11),
                    ], spacing=2),
                ], alignment=ft.MainAxisAlignment.START, spacing=10),
            ], spacing=5, tight=True),
            width=320,
            padding=ft.padding.only(top=10),
        ),
        actions=[
            ft.TextButton(
                "Cerrar",
                on_click=lambda e: page.close(settings_dialog),
            )
        ],
        actions_alignment=ft.MainAxisAlignment.END,
    )
    page.open(settings_dialog)
    return settings_dialog


# Alias para compatibilidad de import.
open_settings_dialog = show_settings_dialog
