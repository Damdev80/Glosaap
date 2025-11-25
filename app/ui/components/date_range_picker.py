"""
Componente de selector de rango de fechas
"""
import flet as ft
from datetime import datetime
from ui.styles import COLORS, FONT_SIZES, SPACING


class DateRangePicker:
    """Componente para seleccionar un rango de fechas"""
    
    def __init__(self, page: ft.Page, on_change=None):
        self.page = page
        self.on_change = on_change
        
        # Valores seleccionados
        self.date_from = None
        self.date_to = None
        
        # Textos de display
        self.date_from_text = ft.Text(
            "Seleccionar", 
            size=13, 
            color=COLORS["text_secondary"],
            weight=ft.FontWeight.W_400
        )
        self.date_to_text = ft.Text(
            "Seleccionar", 
            size=13, 
            color=COLORS["text_secondary"],
            weight=ft.FontWeight.W_400
        )
        
        # Crear controles
        self._create_pickers()
        self._create_ui()
    
    def _create_pickers(self):
        """Crea los DatePickers"""
        self.picker_from = ft.DatePicker(
            first_date=datetime(2020, 1, 1),
            last_date=datetime(2030, 12, 31),
            on_change=self._on_date_from_selected,
            on_dismiss=lambda e: None
        )
        
        self.picker_to = ft.DatePicker(
            first_date=datetime(2020, 1, 1),
            last_date=datetime(2030, 12, 31),
            on_change=self._on_date_to_selected,
            on_dismiss=lambda e: None
        )
        
        # Agregar a overlay de la página
        self.page.overlay.append(self.picker_from)
        self.page.overlay.append(self.picker_to)
    
    def _on_date_from_selected(self, e):
        """Callback cuando se selecciona fecha desde"""
        if e.control.value:
            self.date_from = e.control.value
            self.date_from_text.value = self.date_from.strftime("%d/%m/%Y")
            self.date_from_text.color = COLORS["text_primary"]
        self.page.update()
        if self.on_change:
            self.on_change(self.date_from, self.date_to)
    
    def _on_date_to_selected(self, e):
        """Callback cuando se selecciona fecha hasta"""
        if e.control.value:
            self.date_to = e.control.value
            self.date_to_text.value = self.date_to.strftime("%d/%m/%Y")
            self.date_to_text.color = COLORS["text_primary"]
        self.page.update()
        if self.on_change:
            self.on_change(self.date_from, self.date_to)
    
    def _open_picker_from(self, e):
        """Abre el picker de fecha desde"""
        self.picker_from.open = True
        self.page.update()
    
    def _open_picker_to(self, e):
        """Abre el picker de fecha hasta"""
        self.picker_to.open = True
        self.page.update()
    
    def clear(self, e=None):
        """Limpia las fechas seleccionadas"""
        self.date_from = None
        self.date_to = None
        self.date_from_text.value = "Seleccionar"
        self.date_from_text.color = COLORS["text_secondary"]
        self.date_to_text.value = "Seleccionar"
        self.date_to_text.color = COLORS["text_secondary"]
        self.page.update()
        if self.on_change:
            self.on_change(None, None)
    
    def _create_ui(self):
        """Crea la interfaz del componente"""
        
        # Botón de fecha desde
        self.btn_from = ft.Container(
            content=ft.Row([
                ft.Icon(ft.Icons.CALENDAR_TODAY, size=18, color=COLORS["primary"]),
                self.date_from_text
            ], spacing=8),
            padding=ft.padding.symmetric(horizontal=16, vertical=12),
            bgcolor=COLORS["bg_white"],
            border=ft.border.all(1, COLORS["border"]),
            border_radius=8,
            on_click=self._open_picker_from,
            ink=True
        )
        
        # Botón de fecha hasta
        self.btn_to = ft.Container(
            content=ft.Row([
                ft.Icon(ft.Icons.CALENDAR_TODAY, size=18, color=COLORS["primary"]),
                self.date_to_text
            ], spacing=8),
            padding=ft.padding.symmetric(horizontal=16, vertical=12),
            bgcolor=COLORS["bg_white"],
            border=ft.border.all(1, COLORS["border"]),
            border_radius=8,
            on_click=self._open_picker_to,
            ink=True
        )
        
        # Contenedor principal
        self.container = ft.Container(
            content=ft.Column([
                ft.Text(
                    "📅 Rango de fechas para buscar correos",
                    size=FONT_SIZES["body"],
                    weight=ft.FontWeight.W_500,
                    color=COLORS["text_primary"],
                    text_align=ft.TextAlign.CENTER
                ),
                ft.Container(height=12),
                ft.Row([
                    ft.Column([
                        ft.Text("Desde:", size=12, color=COLORS["text_secondary"]),
                        self.btn_from
                    ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=4),
                    ft.Container(
                        content=ft.Icon(ft.Icons.ARROW_FORWARD, size=20, color=COLORS["text_light"]),
                        padding=ft.padding.only(top=20)
                    ),
                    ft.Column([
                        ft.Text("Hasta:", size=12, color=COLORS["text_secondary"]),
                        self.btn_to
                    ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=4),
                    ft.Container(
                        content=ft.IconButton(
                            icon=ft.Icons.CLEAR,
                            icon_size=20,
                            icon_color=COLORS["text_secondary"],
                            tooltip="Limpiar fechas",
                            on_click=self.clear
                        ),
                        padding=ft.padding.only(top=16)
                    )
                ], alignment=ft.MainAxisAlignment.CENTER, spacing=16),
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
            padding=SPACING["lg"],
            bgcolor=COLORS["bg_white"],
            border_radius=12,
            border=ft.border.all(1, COLORS["border"])
        )
    
    def build(self):
        """Retorna el contenedor construido"""
        return self.container
    
    def get_dates(self):
        """Retorna las fechas seleccionadas"""
        return self.date_from, self.date_to
    
    def get_date_info_text(self):
        """Retorna texto informativo de las fechas seleccionadas"""
        if self.date_from and self.date_to:
            return f"{self.date_from.strftime('%d/%m/%Y')} - {self.date_to.strftime('%d/%m/%Y')}"
        elif self.date_from:
            return f"Desde {self.date_from.strftime('%d/%m/%Y')}"
        elif self.date_to:
            return f"Hasta {self.date_to.strftime('%d/%m/%Y')}"
        return "Sin filtro de fechas"
