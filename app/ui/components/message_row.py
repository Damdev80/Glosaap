"""
Componente de fila de mensaje en lista
Con soporte de temas claro/oscuro
"""
import flet as ft
import os
from app.ui.styles import FONT_SIZES


class MessageRow:
    """Componente que representa una fila de mensaje en la lista"""
    
    def __init__(self, message_data, on_checkbox_change=None):
        self.message_data = message_data
        self.on_checkbox_change = on_checkbox_change
        
        # Checkbox para selección (oculto - ya no es necesario)
        self.checkbox = ft.Checkbox(
            value=False,
            fill_color=ft.Colors.PRIMARY,
            check_color=ft.Colors.SURFACE,
            visible=False,  # Ocultar checkbox
            on_change=self._on_checkbox_change
        )
        
        # Icono de estado (visible)
        self.status_icon = ft.Icon(
            ft.Icons.EMAIL_OUTLINED,
            size=18,
            color=ft.Colors.ON_SURFACE_VARIANT
        )
        
        # Estado de descarga (texto)
        self.status_text = ft.Text("", size=11, color=ft.Colors.ON_SURFACE_VARIANT)
        
        # Construir UI
        self.container = self._build()
    
    def _on_checkbox_change(self, e):
        """Callback interno cuando cambia el checkbox"""
        if self.on_checkbox_change:
            self.on_checkbox_change(self.message_data, self.checkbox.value)
    
    def _build(self):
        """Construye el widget de la fila"""
        subject = self.message_data.get("subject", "(sin asunto)")
        date = self.message_data.get("date", "")
        
        return ft.Container(
            content=ft.Row([
                # Icono de estado
                self.status_icon,
                # Subject y fecha
                ft.Container(
                    content=ft.Column([
                        ft.Text(
                            subject[:80] + "..." if len(subject) > 80 else subject,
                            size=FONT_SIZES["small"],
                            color=ft.Colors.ON_SURFACE,
                            weight=ft.FontWeight.W_400
                        ),
                        ft.Row([
                            ft.Text(
                                str(date) if date else "",
                                size=FONT_SIZES["caption"],
                                color=ft.Colors.ON_SURFACE_VARIANT
                            ),
                            self.status_text
                        ], spacing=10)
                    ], spacing=3),
                    expand=True
                )
            ], spacing=8),
            padding=ft.padding.symmetric(horizontal=10, vertical=10),
            border=ft.border.only(bottom=ft.BorderSide(1, ft.Colors.OUTLINE)),
            bgcolor=ft.Colors.SURFACE
        )
    
    def update_status(self, text, is_error=False):
        """Actualiza el estado visual del mensaje"""
        self.status_text.value = text
        
        if is_error:
            self.status_icon.name = ft.Icons.ERROR_OUTLINE
            self.status_icon.color = ft.Colors.RED
            self.status_text.color = ft.Colors.RED
        elif "✅" in text or "descargado" in text.lower() or "archivo" in text.lower():
            self.status_icon.name = ft.Icons.CHECK_CIRCLE
            self.status_icon.color = ft.Colors.GREEN
            self.status_text.color = ft.Colors.GREEN
        elif "descargando" in text.lower() or "procesando" in text.lower():
            self.status_icon.name = ft.Icons.DOWNLOADING
            self.status_icon.color = ft.Colors.PRIMARY
            self.status_text.color = ft.Colors.PRIMARY
        else:
            self.status_icon.name = ft.Icons.EMAIL_OUTLINED
            self.status_icon.color = ft.Colors.ON_SURFACE_VARIANT
            self.status_text.color = ft.Colors.ON_SURFACE_VARIANT
