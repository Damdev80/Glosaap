"""
Dialogos personalizados elegantes para Glosaap
"""
import flet as ft
from app.ui.styles import COLORS, SPACING
from typing import Optional


class FeatureInDevelopmentDialog:
    """Dialogo simple para funcionalidades en desarrollo."""
    
    @staticmethod
    def show(page: ft.Page, feature_name: str, description: Optional[str] = None):
        """Muestra el dialogo de funcionalidad en desarrollo"""
        dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text("En Desarrollo"),
            content=ft.Text(description or f"'{feature_name}' estara disponible proximamente."),
            actions=[ft.TextButton("OK", on_click=lambda e: FeatureInDevelopmentDialog._close(page, dialog))]
        )
        
        page.overlay.append(dialog)
        dialog.open = True
        page.update()
    
    @staticmethod
    def _close(page: ft.Page, dialog: ft.AlertDialog):
        """Cierra el dialogo"""
        dialog.open = False
        try:
            page.overlay.clear()
        except:
            pass
        page.update()


class SettingsPanel:
    """Panel de configuracion simple."""
    
    def __init__(self, page: ft.Page):
        self.page = page
        self.dialog = None
        
    def show(self):
        """Muestra el panel de configuracion"""
        try:
            from app.config.settings import APP_VERSION
        except:
            APP_VERSION = "1.0.0"
        
        self.dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text("Configuracion", size=18, weight=ft.FontWeight.W_600),
            content=ft.Container(
                content=ft.Column([
                    ft.Text("Apariencia", size=14, weight=ft.FontWeight.W_500, color=COLORS["text_secondary"]),
                    ft.Container(height=10),
                    ft.Row([
                        ft.Icon(ft.Icons.DARK_MODE, size=20, color=COLORS["text_secondary"]),
                        ft.Text("Tema oscuro", size=13),
                        ft.Container(expand=True),
                        ft.Switch(
                            value=self.page.theme_mode == ft.ThemeMode.DARK,
                            on_change=lambda e: self._toggle_theme(e),
                            active_color=COLORS["primary"]
                        )
                    ]),
                    ft.Divider(height=20),
                    ft.Text("Informacion", size=14, weight=ft.FontWeight.W_500, color=COLORS["text_secondary"]),
                    ft.Container(height=10),
                    ft.Row([
                        ft.Icon(ft.Icons.INFO_OUTLINE, size=20, color=COLORS["text_secondary"]),
                        ft.Column([
                            ft.Text(f"Version: {APP_VERSION}", size=12),
                            ft.Text("Glosaap Team", size=11, color=COLORS["text_light"]),
                        ], spacing=2)
                    ], spacing=10),
                ], spacing=5),
                width=300,
                padding=ft.padding.only(top=10)
            ),
            actions=[ft.TextButton("Cerrar", on_click=lambda e: self._close())],
            actions_alignment=ft.MainAxisAlignment.END
        )
        
        self.page.overlay.append(self.dialog)
        self.dialog.open = True
        self.page.update()
    
    def _close(self):
        """Cierra el dialogo"""
        if self.dialog:
            self.dialog.open = False
            try:
                self.page.overlay.clear()
            except:
                pass
            self.page.update()
    
    def _toggle_theme(self, e):
        """Cambia el tema"""
        if e.control.value:
            self.page.theme_mode = ft.ThemeMode.DARK
        else:
            self.page.theme_mode = ft.ThemeMode.LIGHT
        self.page.update()
