"""
Vista de Herramientas
"""
import flet as ft
import os
from app.ui.styles import COLORS, FONT_SIZES


class ToolsView:
    """Vista del menú de herramientas"""
    
    def __init__(self, page: ft.Page, assets_dir: str, on_back=None, on_homologacion=None, on_mix_excel=None, on_homologador_manual=None):
        self.page = page
        self.assets_dir = assets_dir
        self.on_back = on_back
        self.on_homologacion = on_homologacion
        self.on_mix_excel = on_mix_excel
        self.on_homologador_manual = on_homologador_manual
        self.container = self.build()
        
    def _create_tool_card(self, icon, title, description, color, on_click_action, image_src=None):
        """Crea una card de herramienta"""
        def on_hover(e):
            tool_card.scale = 1.02 if e.data == "true" else 1.0
            self.page.update()
        
        # Contenido del icono: imagen o icono
        if image_src:
            icon_content = ft.Image(src=image_src, width=36, height=36, fit=ft.ImageFit.CONTAIN)
        else:
            icon_content = ft.Icon(icon, size=30, color=COLORS["bg_white"])
        
        tool_card = ft.Container(
            content=ft.Row([
                ft.Container(
                    content=icon_content,
                    width=60,
                    height=60,
                    border_radius=12,
                    bgcolor=color if not image_src else COLORS["bg_light"],
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
                                ft.Icons.SYNC_ALT,
                                "Gestión Homologación",
                                "Agregar/editar códigos de homologación",
                                "#4CAF50",
                                lambda e: self.on_homologacion() if self.on_homologacion else None,
                                image_src=os.path.join(self.assets_dir, "img", "homologar.png")
                            ),
                            self._create_tool_card(
                                ft.Icons.COMPARE_ARROWS,
                                "Mix Excel",
                                "Transferir datos entre archivos Excel",
                                "#2196F3",
                                lambda e: self.on_mix_excel() if self.on_mix_excel else None,
                                image_src=os.path.join(self.assets_dir, "img", "mix_excel.png")
                            ),
                        ], spacing=20, alignment=ft.MainAxisAlignment.CENTER),
                        ft.Container(height=15),
                        ft.Row([
                            self._create_tool_card(
                                ft.Icons.TRANSFORM,
                                "Homologador Manual",
                                "Homologar archivos Excel por EPS",
                                "#FF9800",
                                lambda e: self.on_homologador_manual() if self.on_homologador_manual else None,
                                image_src=os.path.join(self.assets_dir, "img", "homologador_manual.png")
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
