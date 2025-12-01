"""
Vista de Herramientas
"""
import flet as ft
import os
from app.ui.styles import COLORS, FONT_SIZES


class ToolsView:
    """Vista del menú de herramientas"""
    
    def __init__(self, page: ft.Page, assets_dir: str, on_back=None):
        self.page = page
        self.assets_dir = assets_dir
        self.on_back = on_back
        self.container = self.build()
        
    def _create_tool_card(self, icon, title, description, color, on_click_action):
        """Crea una card de herramienta"""
        def on_hover(e):
            tool_card.scale = 1.02 if e.data == "true" else 1.0
            self.page.update()
        
        tool_card = ft.Container(
            content=ft.Row([
                ft.Container(
                    content=ft.Icon(icon, size=30, color=COLORS["bg_white"]),
                    width=60,
                    height=60,
                    border_radius=12,
                    bgcolor=color,
                    alignment=ft.alignment.center
                ),
                ft.Container(width=15),
                ft.Column([
                    ft.Text(title, size=16, weight=ft.FontWeight.W_600, color=COLORS["text_primary"]),
                    ft.Text(description, size=12, color=COLORS["text_secondary"])
                ], spacing=2, alignment=ft.MainAxisAlignment.CENTER)
            ]),
            padding=20,
            bgcolor=COLORS["bg_white"],
            border_radius=12,
            border=ft.border.all(1, COLORS["border"]),
            animate_scale=ft.Animation(150, ft.AnimationCurve.EASE_OUT),
            scale=1.0,
            on_hover=on_hover,
            on_click=on_click_action,
            ink=True,
            width=350
        )
        return tool_card
    
    def build(self):
        """Construye la vista de herramientas"""
        self.container = ft.Container(
            content=ft.Column([
                # Header
                ft.Container(
                    content=ft.Row([
                        ft.IconButton(
                            icon=ft.Icons.ARROW_BACK,
                            icon_color=COLORS["text_secondary"],
                            on_click=lambda e: self.on_back() if self.on_back else None
                        ),
                        ft.Image(
                            src=os.path.join(self.assets_dir, "icons", "utils.png"),
                            width=30,
                            height=30,
                            fit=ft.ImageFit.CONTAIN
                        ),
                        ft.Text("Herramientas", size=24, weight=ft.FontWeight.W_500, color=COLORS["text_primary"]),
                    ], spacing=10),
                    padding=20,
                    bgcolor=COLORS["bg_white"],
                    border=ft.border.only(bottom=ft.BorderSide(1, COLORS["border"]))
                ),
                # Grid de herramientas
                ft.Container(
                    content=ft.Column([
                        ft.Row([
                            self._create_tool_card(
                                ft.Icons.FOLDER_OPEN,
                                "Visor de Archivos",
                                "Cargar y visualizar archivos Excel/CSV",
                                "#2196F3",
                                lambda e: print("Visor de archivos - TODO")
                            ),
                            self._create_tool_card(
                                ft.Icons.SYNC_ALT,
                                "Homologador Manual",
                                "Buscar códigos en tablas de homologación",
                                "#4CAF50",
                                lambda e: print("Homologador - TODO")
                            ),
                        ], spacing=20, alignment=ft.MainAxisAlignment.CENTER),
                        ft.Container(height=15),
                        ft.Row([
                            self._create_tool_card(
                                ft.Icons.BAR_CHART,
                                "Reportes",
                                "Generar reportes de glosas procesadas",
                                "#FF9800",
                                lambda e: print("Reportes - TODO")
                            ),
                            self._create_tool_card(
                                ft.Icons.SETTINGS,
                                "Configuración",
                                "Ajustes de la aplicación",
                                "#9C27B0",
                                lambda e: print("Configuración - TODO")
                            ),
                        ], spacing=20, alignment=ft.MainAxisAlignment.CENTER),
                    ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                    padding=30,
                    expand=True
                )
            ], spacing=0),
            bgcolor=COLORS["bg_light"],
            expand=True,
            visible=False
        )
        
        return self.container
    
    def show(self):
        """Muestra la vista"""
        if self.container:
            self.container.visible = True
            self.page.update()
    
    def hide(self):
        """Oculta la vista"""
        if self.container:
            self.container.visible = False
            self.page.update()
