"""" 
Componente de tarjeta de EPS
Con soporte de temas claro/oscuro
"""
import flet as ft
import os
from app.ui.styles import FONT_SIZES, SPACING


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
        self.container = None
    
    def _handle_click(self, e):
        """Maneja el click en la tarjeta"""
        if self.on_click_callback:
            self.on_click_callback(self.eps_info)
    
    def _on_hover(self, e):
        """Efecto hover suave"""
        is_hovered = e.data == "true"
        if self.container:
            self.container.scale = 1.03 if is_hovered else 1.0
            self.container.shadow = ft.BoxShadow(
                spread_radius=0,
                blur_radius=20 if is_hovered else 10,
                color=ft.Colors.with_opacity(0.15 if is_hovered else 0.06, ft.Colors.PRIMARY if is_hovered else ft.Colors.ON_SURFACE),
                offset=ft.Offset(0, 8 if is_hovered else 3)
            )
            self.container.border = ft.border.all(
                2 if is_hovered else 1.5, 
                ft.Colors.PRIMARY if is_hovered else ft.Colors.OUTLINE_VARIANT
            )
            self.container.update()
    
    def build(self):
        """Construye y retorna la tarjeta"""
        # Decidir si usar imagen o emoji
        image_path = self.eps_info.get("image_path")
        
        if image_path and os.path.exists(image_path):
            # Usar imagen
            visual_element = ft.Container(
                content=ft.Image(
                    src=image_path,
                    width=48,
                    height=48,
                    fit=ft.ImageFit.CONTAIN
                ),
                padding=4,
            )
        else:
            # Usar emoji/icono
            visual_element = ft.Container(
                content=ft.Text(self.eps_info.get("icon", "📋"), size=38),
                padding=4,
            )
        
        self.container = ft.Container(
            content=ft.Column([
                visual_element,
                ft.Text(
                    self.eps_info["name"],
                    size=FONT_SIZES["body"],
                    weight=ft.FontWeight.W_600,
                    color=ft.Colors.ON_SURFACE,
                    text_align=ft.TextAlign.CENTER
                ),
                ft.Text(
                    self.eps_info.get("description", ""),
                    size=FONT_SIZES["caption"],
                    color=ft.Colors.ON_SURFACE_VARIANT,
                    text_align=ft.TextAlign.CENTER,
                    weight=ft.FontWeight.W_400
                )
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=6, tight=True),
            bgcolor=ft.Colors.SURFACE,
            border_radius=14,
            padding=ft.padding.symmetric(horizontal=16, vertical=14),
            width=150,
            height=135,
            ink=True,
            ink_color=ft.Colors.with_opacity(0.1, ft.Colors.PRIMARY),
            on_click=self._handle_click,
            on_hover=self._on_hover,
            shadow=ft.BoxShadow(
                spread_radius=0,
                blur_radius=10,
                color=ft.Colors.with_opacity(0.06, ft.Colors.ON_SURFACE),
                offset=ft.Offset(0, 3)
            ),
            border=ft.border.all(1.5, ft.Colors.OUTLINE_VARIANT),
            animate_scale=ft.Animation(150, ft.AnimationCurve.EASE_OUT),
            animate=ft.Animation(150, ft.AnimationCurve.EASE_OUT),
            scale=1.0
        )
        return self.container
