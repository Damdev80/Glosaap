"""
Pantalla de selección de EPS y rango de fechas
"""
import flet as ft
from ui.styles import COLORS, FONT_SIZES, SPACING
from ui.components.date_range_picker import DateRangePicker
from ui.components.eps_card import EpsCard


class EpsScreen:
    """Pantalla para seleccionar EPS y rango de fechas"""
    
    # Lista de EPS disponibles
    EPS_LIST = [
        {"name": "Todas las EPS", "icon": "🏥", "description": "Sin filtro", "filter": None, "filter_type": None},
        {"name": "Mutualser", "icon": "🔵", "description": "Mutualser EPS", "filter": "mutualser", "filter_type": "subject_exact_pattern", "subject_pattern": "objeciones de glosa factura fc"},
        {"name": "Sanitas", "icon": "🟢", "description": "Sanitas EPS", "filter": "sanitas", "filter_type": "keyword"},
        {"name": "Nueva EPS", "icon": "🟠", "description": "Nueva EPS", "filter": "nuevaeps", "filter_type": "keyword"},
        {"name": "Compensar", "icon": "🟡", "description": "Compensar EPS", "filter": "compensar", "filter_type": "keyword"},
        {"name": "Famisanar", "icon": "🟣", "description": "Famisanar EPS", "filter": "famisanar", "filter_type": "keyword"},
        {"name": "Cosalud", "icon": "🔴", "description": "Cosalud EPS", "filter": "cosalud", "filter_type": "keyword"}
    ]
    
    def __init__(self, page: ft.Page, on_eps_selected=None, on_logout=None):
        """
        Args:
            page: Página de Flet
            on_eps_selected: Callback(eps_info, date_from, date_to) al seleccionar EPS
            on_logout: Callback al cerrar sesión
        """
        self.page = page
        self.on_eps_selected = on_eps_selected
        self.on_logout = on_logout
        
        # Componente de fechas
        self.date_picker = DateRangePicker(page)
        
        # Estado de validación
        self.dates_selected = False
        self.warning_text = ft.Text(
            "",
            size=12,
            color=COLORS["error"],
            text_align=ft.TextAlign.CENTER,
            visible=False
        )
        
        # Crear vista
        self._create_view()
    
    def _on_eps_click(self, eps_info):
        """Maneja el click en una tarjeta de EPS"""
        date_from, date_to = self.date_picker.get_dates()
        
        # Validar que se hayan seleccionado fechas (opcional pero recomendado)
        if not date_from and not date_to:
            self.warning_text.value = "⚠️ Tip: Selecciona un rango de fechas para una búsqueda más eficiente"
            self.warning_text.visible = True
            self.page.update()
        
        # Llamar callback con la info
        if self.on_eps_selected:
            self.on_eps_selected(eps_info, date_from, date_to)
    
    def _handle_logout(self, e):
        """Maneja el cierre de sesión"""
        if self.on_logout:
            self.on_logout()
    
    def _create_view(self):
        """Crea la vista de la pantalla"""
        
        # Grid de tarjetas de EPS
        eps_cards = ft.Row(
            controls=[EpsCard(eps, on_click=self._on_eps_click).build() for eps in self.EPS_LIST],
            wrap=True,
            spacing=SPACING["md"],
            run_spacing=SPACING["md"],
            alignment=ft.MainAxisAlignment.CENTER
        )
        
        # Contenedor principal
        self.view = ft.Container(
            content=ft.Column([
                ft.Container(height=SPACING["md"]),
                
                # Título
                ft.Text(
                    "Gestor de Glosas",
                    size=FONT_SIZES["title"],
                    weight=ft.FontWeight.W_300,
                    color=COLORS["text_primary"],
                    text_align=ft.TextAlign.CENTER
                ),
                ft.Text(
                    "Busca y procesa notificaciones de glosas por EPS",
                    size=FONT_SIZES["small"],
                    color=COLORS["text_secondary"],
                    text_align=ft.TextAlign.CENTER
                ),
                
                ft.Container(height=SPACING["lg"]),
                
                # Paso 1: Selector de fechas
                ft.Container(
                    content=ft.Column([
                        ft.Row([
                            ft.Container(
                                content=ft.Text("1", size=14, weight=ft.FontWeight.BOLD, color=COLORS["bg_white"]),
                                width=28,
                                height=28,
                                border_radius=14,
                                bgcolor=COLORS["primary"],
                                alignment=ft.alignment.center
                            ),
                            ft.Text(
                                "Selecciona el rango de fechas",
                                size=FONT_SIZES["body"],
                                weight=ft.FontWeight.W_500,
                                color=COLORS["text_primary"]
                            )
                        ], spacing=10, alignment=ft.MainAxisAlignment.CENTER),
                        ft.Container(height=8),
                        self.date_picker.build()
                    ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                ),
                
                ft.Container(height=SPACING["lg"]),
                
                # Paso 2: Selector de EPS
                ft.Container(
                    content=ft.Column([
                        ft.Row([
                            ft.Container(
                                content=ft.Text("2", size=14, weight=ft.FontWeight.BOLD, color=COLORS["bg_white"]),
                                width=28,
                                height=28,
                                border_radius=14,
                                bgcolor=COLORS["primary"],
                                alignment=ft.alignment.center
                            ),
                            ft.Text(
                                "Selecciona una EPS para buscar",
                                size=FONT_SIZES["body"],
                                weight=ft.FontWeight.W_500,
                                color=COLORS["text_primary"]
                            )
                        ], spacing=10, alignment=ft.MainAxisAlignment.CENTER),
                        ft.Container(height=12),
                        self.warning_text,
                        ft.Container(
                            content=eps_cards,
                            padding=SPACING["md"],
                            bgcolor=COLORS["bg_light"],
                            border_radius=12
                        )
                    ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                ),
                
                ft.Container(height=SPACING["md"]),
                
                # Botón de cerrar sesión
                ft.TextButton(
                    "← Cerrar sesión",
                    icon=ft.Icons.LOGOUT,
                    on_click=self._handle_logout,
                    style=ft.ButtonStyle(color=COLORS["text_secondary"])
                )
                
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, scroll=ft.ScrollMode.AUTO),
            padding=ft.padding.all(SPACING["lg"]),
            bgcolor=COLORS["bg_light"],
            alignment=ft.alignment.top_center,
            expand=True,
            visible=False
        )
    
    def build(self):
        """Retorna la vista construida"""
        return self.view
    
    def show(self):
        """Muestra la pantalla"""
        self.view.visible = True
        self.warning_text.visible = False
        self.page.update()
    
    def hide(self):
        """Oculta la pantalla"""
        self.view.visible = False
        self.page.update()
    
    def get_date_range(self):
        """Retorna el rango de fechas seleccionado"""
        return self.date_picker.get_dates()
