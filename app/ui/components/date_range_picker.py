"""
Componente de selector de rango de fechas
"""
import flet as ft
from datetime import datetime
from app.ui.styles import COLORS, FONT_SIZES, SPACING


class DateRangePicker:
    """Componente para seleccionar un rango de fechas"""
    
    def __init__(self, page: ft.Page, on_change=None, on_validation_error=None):
        self.page = page
        self.on_change = on_change
        self.on_validation_error = on_validation_error  # Callback para errores de validación
        
        # Valores seleccionados
        self.date_from = None
        self.date_to = None
        
        # Estado de validación
        self.is_valid = True
        self.validation_error = None
        
        # Textos de display
        self.date_from_text = ft.Text(
            "Seleccionar", 
            size=14, 
            color=COLORS["text_secondary"],
            weight=ft.FontWeight.W_500
        )
        self.date_to_text = ft.Text(
            "Seleccionar", 
            size=14, 
            color=COLORS["text_secondary"],
            weight=ft.FontWeight.W_500
        )
        
        # Texto de error de validación
        self.error_text = ft.Text(
            "",
            size=12,
            color=COLORS["error"],
            text_align=ft.TextAlign.CENTER,
            visible=False
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
            self.date_from_text.weight = ft.FontWeight.W_600
            self._validate_dates()
        self.page.update()
        if self.on_change:
            self.on_change(self.date_from, self.date_to)
    
    def _on_date_to_selected(self, e):
        """Callback cuando se selecciona fecha hasta"""
        if e.control.value:
            self.date_to = e.control.value
            self.date_to_text.value = self.date_to.strftime("%d/%m/%Y")
            self.date_to_text.color = COLORS["text_primary"]
            self.date_to_text.weight = ft.FontWeight.W_600
            self._validate_dates()
        self.page.update()
        if self.on_change:
            self.on_change(self.date_from, self.date_to)
    
    def _validate_dates(self):
        """Valida que el rango de fechas sea correcto"""
        self.is_valid = True
        self.validation_error = None
        self.error_text.visible = False
        
        # Resetear estilos de los botones
        self.btn_from.border = ft.border.all(1, COLORS["border"])
        self.btn_to.border = ft.border.all(1, COLORS["border"])
        
        if self.date_from and self.date_to:
            if self.date_from > self.date_to:
                self.is_valid = False
                self.validation_error = "⚠️ La fecha 'Desde' no puede ser mayor que la fecha 'Hasta'"
                self.error_text.value = self.validation_error
                self.error_text.visible = True
                
                # Resaltar campos con error
                self.btn_from.border = ft.border.all(2, COLORS["error"])
                self.btn_to.border = ft.border.all(2, COLORS["error"])
                
                # Notificar error si hay callback
                if self.on_validation_error:
                    self.on_validation_error(self.validation_error)
        
        return self.is_valid
    
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
        self.date_from_text.weight = ft.FontWeight.W_500
        self.date_to_text.value = "Seleccionar"
        self.date_to_text.color = COLORS["text_secondary"]
        self.date_to_text.weight = ft.FontWeight.W_500
        
        # Limpiar estado de validación
        self.is_valid = True
        self.validation_error = None
        self.error_text.visible = False
        self.btn_from.border = ft.border.all(1, COLORS["border"])
        self.btn_to.border = ft.border.all(1, COLORS["border"])
        
        self.page.update()
        if self.on_change:
            self.on_change(None, None)
    
    def _create_ui(self):
        """Crea la interfaz del componente"""
        
        # Botón de fecha desde
        self.btn_from = ft.Container(
            content=ft.Row([
                ft.Icon(ft.Icons.CALENDAR_TODAY, size=20, color=COLORS["primary"]),
                self.date_from_text
            ], spacing=10),
            padding=ft.padding.symmetric(horizontal=18, vertical=14),
            bgcolor=COLORS["bg_white"],
            border=ft.border.all(1.5, COLORS["border"]),
            border_radius=10,
            on_click=self._open_picker_from,
            ink=True,
            width=180,
            shadow=ft.BoxShadow(
                spread_radius=0,
                blur_radius=4,
                color=ft.Colors.with_opacity(0.05, COLORS["text_primary"]),
                offset=ft.Offset(0, 2)
            )
        )
        
        # Botón de fecha hasta
        self.btn_to = ft.Container(
            content=ft.Row([
                ft.Icon(ft.Icons.CALENDAR_TODAY, size=20, color=COLORS["primary"]),
                self.date_to_text
            ], spacing=10),
            padding=ft.padding.symmetric(horizontal=18, vertical=14),
            bgcolor=COLORS["bg_white"],
            border=ft.border.all(1.5, COLORS["border"]),
            border_radius=10,
            on_click=self._open_picker_to,
            ink=True,
            width=180,
            shadow=ft.BoxShadow(
                spread_radius=0,
                blur_radius=4,
                color=ft.Colors.with_opacity(0.05, COLORS["text_primary"]),
                offset=ft.Offset(0, 2)
            )
        )
        
        # Contenedor principal
        self.container = ft.Container(
            content=ft.Column([
                ft.Row([
                    ft.Column([
                        ft.Text("Desde:", size=13, weight=ft.FontWeight.BOLD, color=COLORS["text_primary"]),
                        ft.Container(height=6),
                        self.btn_from
                    ], horizontal_alignment=ft.CrossAxisAlignment.START, spacing=0),
                    ft.Container(
                        content=ft.Icon(ft.Icons.ARROW_FORWARD, size=24, color=COLORS["primary"]),
                        padding=ft.padding.only(top=26)
                    ),
                    ft.Column([
                        ft.Text("Hasta:", size=13, weight=ft.FontWeight.BOLD, color=COLORS["text_primary"]),
                        ft.Container(height=6),
                        self.btn_to
                    ], horizontal_alignment=ft.CrossAxisAlignment.START, spacing=0),
                    ft.Container(
                        content=ft.IconButton(
                            icon=ft.Icons.CLEAR,
                            icon_size=22,
                            icon_color=COLORS["text_secondary"],
                            tooltip="Limpiar fechas",
                            on_click=self.clear,
                            style=ft.ButtonStyle(
                                overlay_color=ft.Colors.with_opacity(0.1, COLORS["error"])
                            )
                        ),
                        padding=ft.padding.only(top=20)
                    )
                ], alignment=ft.MainAxisAlignment.CENTER, spacing=20),
                # Mensaje de error de validación
                ft.Container(height=4),
                self.error_text,
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
            padding=20,
            bgcolor=COLORS["bg_white"],
            border_radius=16,
            border=ft.border.all(1.5, COLORS["border_light"]),
            shadow=ft.BoxShadow(
                spread_radius=0,
                blur_radius=10,
                color=ft.Colors.with_opacity(0.05, COLORS["text_primary"]),
                offset=ft.Offset(0, 3)
            )
        )
    
    def build(self):
        """Retorna el contenedor construido"""
        return self.container
    
    def get_dates(self):
        """Retorna las fechas seleccionadas"""
        return self.date_from, self.date_to
    
    def is_date_range_valid(self):
        """Verifica si el rango de fechas es válido"""
        return self.is_valid
    
    def get_validation_error(self):
        """Retorna el mensaje de error de validación si existe"""
        return self.validation_error
    
    def get_date_info_text(self):
        """Retorna texto informativo de las fechas seleccionadas"""
        if self.date_from and self.date_to:
            return f"{self.date_from.strftime('%d/%m/%Y')} - {self.date_to.strftime('%d/%m/%Y')}"
        elif self.date_from:
            return f"Desde {self.date_from.strftime('%d/%m/%Y')}"
        elif self.date_to:
            return f"Hasta {self.date_to.strftime('%d/%m/%Y')}"
        return "Sin filtro de fechas"
