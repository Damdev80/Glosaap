"""
Componente de fila de mensaje en lista
"""
import flet as ft
import os
from app.ui.styles import COLORS, FONT_SIZES


class MessageRow:
    """Componente que representa una fila de mensaje en la lista"""
    
    def __init__(self, message_data, on_checkbox_change=None):
        self.message_data = message_data
        self.on_checkbox_change = on_checkbox_change
        
        # Checkbox para selección
        self.checkbox = ft.Checkbox(
            value=False,
            fill_color=COLORS["primary"],
            check_color=COLORS["bg_white"],
            on_change=self._on_checkbox_change
        )
        
        # Estado de descarga
        self.status_text = ft.Text("", size=11, color=COLORS["text_secondary"])
        
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
                # Checkbox para selección
                self.checkbox,
                # Subject y fecha
                ft.Container(
                    content=ft.Column([
                        ft.Text(
                            subject[:80] + "..." if len(subject) > 80 else subject,
                            size=FONT_SIZES["small"],
                            color=COLORS["text_primary"],
                            weight=ft.FontWeight.W_400
                        ),
                        ft.Row([
                            ft.Text(
                                str(date) if date else "",
                                size=FONT_SIZES["caption"],
                                color=COLORS["text_secondary"]
                            ),
                            self.status_text
                        ], spacing=10)
                    ], spacing=3),
                    expand=True
                )
            ], spacing=8),
            padding=ft.padding.symmetric(horizontal=10, vertical=10),
            border=ft.border.only(bottom=ft.BorderSide(1, COLORS["border"])),
            bgcolor=COLORS["bg_white"]
        )
    
    def update_status(self, text, is_error=False):
        """Actualiza el texto de estado"""
        self.status_text.value = text
        self.status_text.color = COLORS["error"] if is_error else COLORS["success"]
