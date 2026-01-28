"""
Componente de header con navegación reutilizable
Integrado con NavigationController existente
Con soporte de temas claro/oscuro
"""
import flet as ft
from app.ui.styles import FONT_SIZES, SPACING
from typing import Callable, List, Optional


class NavigationHeader:
    """Header de navegación que usa NavigationController"""
    
    def __init__(self, page: ft.Page, navigation_controller=None):
        self.page = page
        self.nav_controller = navigation_controller
    
    def build(
        self,
        title: str,
        show_back: bool = True,
        back_text: str = "← Atrás",
        custom_back_action: Optional[Callable] = None,
        breadcrumb: Optional[List] = None,
        actions: Optional[List] = None
    ) -> ft.Container:
        """
        Construye header con navegación
        
        Args:
            title: Título de la sección
            show_back: Mostrar botón de regreso
            back_text: Texto del botón atrás
            custom_back_action: Acción personalizada (opcional)
            breadcrumb: Lista de breadcrumbs
            actions: Botones adicionales
        """
        
        content_items = []
        
        # Botón de regreso
        if show_back:
            back_button = self._create_back_button(
                text=back_text,
                custom_action=custom_back_action
            )
            content_items.append(back_button)
            content_items.append(ft.Container(width=SPACING["md"]))
        
        # Título y breadcrumb
        title_column = ft.Column([
            ft.Text(
                title,
                size=FONT_SIZES["heading"],
                weight=ft.FontWeight.BOLD,
                color=ft.Colors.ON_SURFACE
            )
        ], spacing=SPACING["xs"])
        
        if breadcrumb:
            breadcrumb_row = self._create_breadcrumb(breadcrumb)
            title_column.controls.append(breadcrumb_row)
        
        content_items.append(title_column)
        
        # Spacer
        content_items.append(ft.Container(expand=True))
        
        # Acciones adicionales
        if actions:
            action_row = ft.Row(actions, spacing=SPACING["sm"])
            content_items.append(action_row)
        
        return ft.Container(
            content=ft.Row(
                content_items,
                alignment=ft.MainAxisAlignment.START,
                vertical_alignment=ft.CrossAxisAlignment.CENTER
            ),
            padding=ft.padding.all(SPACING["lg"]),
            bgcolor=ft.Colors.SURFACE,
            border=ft.border.only(
                bottom=ft.border.BorderSide(1, ft.Colors.OUTLINE_VARIANT)
            )
        )
    
    def _create_back_button(self, text: str, custom_action: Optional[Callable] = None) -> ft.ElevatedButton:
        """Crea botón de regreso"""
        
        def on_click(e):
            if custom_action:
                custom_action()
            elif self.nav_controller:
                self.nav_controller.go_back()
        
        return ft.ElevatedButton(
            text=text,
            icon=ft.Icons.ARROW_BACK,
            on_click=on_click,
            bgcolor=ft.Colors.SURFACE_CONTAINER_HIGHEST,
            color=ft.Colors.ON_SURFACE,
            elevation=1
        )
    
    def _create_breadcrumb(self, breadcrumb: list) -> ft.Row:
        """Crea breadcrumb navigation"""
        items = []
        
        for i, crumb in enumerate(breadcrumb):
            if i < len(breadcrumb) - 1:  # No es el último
                if crumb.get("action"):
                    # Link clicable
                    link = ft.TextButton(
                        text=crumb["text"],
                        on_click=crumb["action"],
                        style=ft.ButtonStyle(
                            color=ft.Colors.PRIMARY,
                            padding=ft.padding.symmetric(horizontal=4, vertical=2)
                        )
                    )
                    items.append(link)
                else:
                    items.append(
                        ft.Text(crumb["text"], color=ft.Colors.ON_SURFACE_VARIANT, size=FONT_SIZES["small"])
                    )
                
                # Separador
                items.append(
                    ft.Text(" > ", color=ft.Colors.ON_SURFACE_VARIANT, size=FONT_SIZES["small"])
                )
            else:
                # Último elemento (actual)
                items.append(
                    ft.Text(
                        crumb["text"],
                        color=ft.Colors.ON_SURFACE,
                        size=FONT_SIZES["small"],
                        weight=ft.FontWeight.W_500
                    )
                )
        
        return ft.Row(items, spacing=0)
