"""" 
Componente de tarjeta de EPS
"""
import flet as ft
import os
from app.ui.styles import COLORS, FONT_SIZES, SPACING


class EpsCard:
    """Tarjeta visual para seleccionar una EPS"""
    
    def __init__(self, eps_info: dict, on_click=None):
        """
        Args:
            eps_info: Dict con name, icon, description, filter, filter_type, subject_pattern, image_path
            on_click: Callback al hacer click
        """
        self.eps_info = eps_info
        self.on_click_callback = on_click
    
    def _handle_click(self, e):
        """Maneja el click en la tarjeta"""
        if self.on_click_callback:
            self.on_click_callback(self.eps_info)
    
    def build(self):
        """Construye y retorna la tarjeta"""
        # Decidir si usar imagen o emoji
        image_path = self.eps_info.get("image_path")
        
        if image_path and os.path.exists(image_path):
            # Usar imagen
            visual_element = ft.Image(
                src=image_path,
                width=50,
                height=50,
                fit=ft.ImageFit.CONTAIN
            )
        else:
            # Usar emoji/icono
            visual_element = ft.Text(self.eps_info.get("icon", "📋"), size=36)
        
        return ft.Container(
            content=ft.Column([
                visual_element,
                ft.Text(
                    self.eps_info["name"],
                    size=FONT_SIZES["body"],
                    weight=ft.FontWeight.W_500,
                    color=COLORS["text_primary"],
                    text_align=ft.TextAlign.CENTER
                ),
                ft.Text(
                    self.eps_info.get("description", ""),
                    size=FONT_SIZES["small"],
                    color=COLORS["text_secondary"],
                    text_align=ft.TextAlign.CENTER
                )
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=6),
            bgcolor=COLORS["bg_white"],
            border_radius=12,
            padding=SPACING["md"],
            width=145,
            height=130,
            ink=True,
            on_click=self._handle_click,
            shadow=ft.BoxShadow(
                spread_radius=0,
                blur_radius=8,
                color=ft.Colors.with_opacity(0.08, COLORS["text_primary"]),
                offset=ft.Offset(0, 2)
            ),
            border=ft.border.all(1, COLORS["border"])
        )