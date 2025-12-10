"""
Pantalla de selección de EPS y rango de fechas
"""
import flet as ft
from app.ui.styles import COLORS, FONT_SIZES, SPACING
from app.ui.components.date_range_picker import DateRangePicker
from app.ui.components.eps_card import EpsCard
from app.config.eps_config import get_eps_list


class EpsScreen:
    """Pantalla para seleccionar EPS y rango de fechas"""
    
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
        
        # Cargar lista de EPS desde configuración
        self.eps_list = get_eps_list()
        
        # Componente de fechas con callback de validación
        self.date_picker = DateRangePicker(
            page, 
            on_validation_error=self._on_date_validation_error
        )
        
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
    
    def _on_date_validation_error(self, error_message):
        """Callback cuando hay un error de validación de fechas"""
        # El error ya se muestra en el DateRangePicker
        # Aquí podríamos agregar lógica adicional si fuera necesario
        pass
    
    def _on_eps_click(self, eps_info):
        """Maneja el click en una tarjeta de EPS"""
        date_from, date_to = self.date_picker.get_dates()
        
        # Validar que se hayan seleccionado AMBAS fechas (obligatorio)
        if not date_from or not date_to:
            self._show_dates_required_dialog()
            return
        
        # Validar rango de fechas (desde <= hasta)
        if not self.date_picker.is_date_range_valid():
            self._show_date_error_dialog()
            return
        
        # Llamar callback con la info
        if self.on_eps_selected:
            self.on_eps_selected(eps_info, date_from, date_to)
    
    def _show_dates_required_dialog(self):
        """Muestra un diálogo indicando que las fechas son obligatorias"""
        def close_dialog(e):
            dialog.open = False
            self.page.update()
        
        dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text("📅 Fechas requeridas"),
            content=ft.Text(
                "Debes seleccionar un rango de fechas antes de elegir una EPS.\n\n"
                "Por favor, selecciona la fecha 'Desde' y 'Hasta' para continuar.",
                size=14
            ),
            actions=[
                ft.TextButton("Entendido", on_click=close_dialog),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        
        self.page.overlay.append(dialog)
        dialog.open = True
        self.page.update()
    
    def _show_date_error_dialog(self):
        """Muestra un diálogo de alerta cuando las fechas son incompatibles"""
        def close_dialog(e):
            dialog.open = False
            self.page.update()
        
        dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text("⚠️ Rango de fechas inválido"),
            content=ft.Text(
                "La fecha 'Desde' no puede ser mayor que la fecha 'Hasta'.\n\n"
                "Por favor, corrige el rango de fechas antes de continuar.",
                size=14
            ),
            actions=[
                ft.TextButton("Entendido", on_click=close_dialog),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        
        self.page.overlay.append(dialog)
        dialog.open = True
        self.page.update()
    
    def _handle_logout(self, e):
        """Maneja el cierre de sesión"""
        if self.on_logout:
            self.on_logout()
    
    def _create_view(self):
        """Crea la vista de la pantalla"""
        
        # Grid de tarjetas de EPS (usa la lista cargada desde config)
        eps_cards = ft.Row(
            controls=[EpsCard(eps, on_click=self._on_eps_click).build() for eps in self.eps_list],
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
                    size=38,
                    weight=ft.FontWeight.BOLD,
                    color=COLORS["text_primary"],
                    text_align=ft.TextAlign.CENTER
                ),
                ft.Container(height=4),
                ft.Text(
                    "Busca y procesa notificaciones de glosas por EPS",
                    size=15,
                    color=COLORS["text_secondary"],
                    text_align=ft.TextAlign.CENTER,
                    weight=ft.FontWeight.W_400
                ),
                
                ft.Container(height=SPACING["lg"]),
                
                # Paso 1: Selector de fechas
                ft.Container(
                    content=ft.Column([
                        ft.Row([
                            ft.Container(
                                content=ft.Text("1", size=15, weight=ft.FontWeight.BOLD, color=COLORS["bg_white"]),
                                width=32,
                                height=32,
                                border_radius=16,
                                bgcolor=COLORS["primary"],
                                alignment=ft.alignment.center,
                                shadow=ft.BoxShadow(
                                    spread_radius=0,
                                    blur_radius=8,
                                    color=ft.Colors.with_opacity(0.3, COLORS["primary"]),
                                    offset=ft.Offset(0, 2)
                                )
                            ),
                            ft.Text(
                                "Selecciona el rango de fechas",
                                size=16,
                                weight=ft.FontWeight.BOLD,
                                color=COLORS["text_primary"]
                            )
                        ], spacing=12, alignment=ft.MainAxisAlignment.CENTER),
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
                                content=ft.Text("2", size=15, weight=ft.FontWeight.BOLD, color=COLORS["bg_white"]),
                                width=32,
                                height=32,
                                border_radius=16,
                                bgcolor=COLORS["primary"],
                                alignment=ft.alignment.center,
                                shadow=ft.BoxShadow(
                                    spread_radius=0,
                                    blur_radius=8,
                                    color=ft.Colors.with_opacity(0.3, COLORS["primary"]),
                                    offset=ft.Offset(0, 2)
                                )
                            ),
                            ft.Text(
                                "Selecciona una EPS para buscar",
                                size=16,
                                weight=ft.FontWeight.BOLD,
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
                
                # Botón de volver al dashboard
                ft.TextButton(
                    "← Volver al menú",
                    icon=ft.Icons.ARROW_BACK,
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
