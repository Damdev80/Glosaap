"""
Botón de configuración global para la aplicación
Se puede usar en cualquier pantalla
"""
import flet as ft
from app.ui.styles import ThemeManager, get_colors, update_colors
from app.config.settings import APP_VERSION


def create_settings_fab(page: ft.Page, on_theme_change=None) -> ft.Container:
    """
    Crea un FAB (Floating Action Button) de configuración posicionado
    
    Args:
        page: Página de Flet
        on_theme_change: Callback cuando cambia el tema
    
    Returns:
        Container con el botón de configuración
    """
    
    def open_settings(e):
        theme_switch = ft.Switch(
            value=ThemeManager.is_dark(),
            on_change=lambda ev: toggle_and_close(ev),
        )
        
        def toggle_and_close(ev):
            ThemeManager.toggle_theme()
            update_colors()
            page.close(settings_dialog)
            if on_theme_change:
                on_theme_change()
        
        settings_dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text("⚙️ Configuración", size=18, weight=ft.FontWeight.W_600),
            content=ft.Container(
                content=ft.Column([
                    ft.Text("Apariencia", size=14, weight=ft.FontWeight.W_500),
                    ft.Container(height=10),
                    ft.Row([
                        ft.Icon(
                            ft.Icons.DARK_MODE if ThemeManager.is_dark() else ft.Icons.LIGHT_MODE, 
                            size=20
                        ),
                        ft.Text("Modo oscuro", size=13),
                        ft.Container(expand=True),
                        theme_switch
                    ], alignment=ft.MainAxisAlignment.START),
                    ft.Divider(height=20),
                    ft.Text("Información", size=14, weight=ft.FontWeight.W_500),
                    ft.Container(height=10),
                    ft.Row([
                        ft.Icon(ft.Icons.INFO_OUTLINE, size=20),
                        ft.Column([
                            ft.Text(f"Versión: {APP_VERSION}", size=12),
                            ft.Text("Glosaap - Gestión de Glosas", size=11),
                        ], spacing=2)
                    ], alignment=ft.MainAxisAlignment.START, spacing=10),
                ], spacing=5, tight=True),
                width=320,
                padding=ft.padding.only(top=10)
            ),
            actions=[
                ft.TextButton("Cerrar", on_click=lambda e: page.close(settings_dialog))
            ],
            actions_alignment=ft.MainAxisAlignment.END
        )
        
        page.open(settings_dialog)
    
    return ft.Container(
        content=ft.IconButton(
            icon=ft.Icons.SETTINGS,
            icon_size=22,
            tooltip="Configuración",
            on_click=open_settings,
            style=ft.ButtonStyle(
                shape=ft.CircleBorder(),
            )
        ),
        right=15,
        bottom=10,
    )
