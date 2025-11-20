"""
Componente de fila de mensaje en lista
"""
import flet as ft
import os
from ui.styles import COLORS, FONT_SIZES


class MessageRow:
    """Componente que representa una fila de mensaje en la lista"""
    
    def __init__(self, message, index):
        self.message = message
        self.index = index
        
        # Elementos de UI que se actualizarán
        self.download_progress = ft.ProgressBar(
            width=200,
            color=COLORS["success"],
            bgcolor=COLORS["border"],
            visible=False,
            height=3
        )
        
        self.download_status = ft.Text(
            "",
            size=FONT_SIZES["caption"],
            color=COLORS["success"],
            visible=False
        )
        
        self.attachment_count = ft.Text(
            "",
            size=FONT_SIZES["caption"],
            color=COLORS["text_secondary"],
            visible=False
        )
        
        self.status_icon = ft.Icon(
            ft.Icons.PENDING,
            size=20,
            color=COLORS["text_light"]
        )
        
        # Guardar referencias en el mensaje
        message["_progress"] = self.download_progress
        message["_status"] = self.download_status
        message["_count"] = self.attachment_count
        message["_icon"] = self.status_icon
        
    def build(self):
        """Construye el widget de la fila"""
        subject = self.message.get("subject", "(sin asunto)")
        
        return ft.Container(
            content=ft.Row([
                # Número
                ft.Container(
                    content=ft.Text(
                        str(self.index),
                        size=FONT_SIZES["small"],
                        weight=ft.FontWeight.W_500,
                        color=COLORS["text_light"]
                    ),
                    width=40,
                    alignment=ft.alignment.center
                ),
                # Subject y progreso
                ft.Container(
                    content=ft.Column([
                        ft.Text(
                            subject[:90] + "..." if len(subject) > 90 else subject,
                            size=FONT_SIZES["small"],
                            color=COLORS["text_primary"],
                            weight=ft.FontWeight.W_400
                        ),
                        ft.Row([
                            self.download_progress,
                            self.download_status
                        ], spacing=10, visible=False),
                        self.attachment_count
                    ], spacing=3),
                    expand=True
                ),
                # Ícono de estado
                ft.Container(
                    content=self.status_icon,
                    width=40
                )
            ], spacing=10),
            padding=ft.padding.symmetric(horizontal=15, vertical=12),
            border=ft.border.only(bottom=ft.BorderSide(1, COLORS["border_light"])),
            bgcolor=COLORS["bg_white"]
        )
    
    def show_downloading(self):
        """Muestra el estado de descarga"""
        # Mostrar el Row del progreso
        progress_row = self.download_progress.parent
        if progress_row:
            progress_row.visible = True
        
        self.download_progress.visible = True
        self.download_status.visible = True
        self.download_status.value = "Descargando..."
        self.download_status.color = COLORS["primary"]
        self.status_icon.name = ft.Icons.DOWNLOADING
        self.status_icon.color = COLORS["primary"]
    
    def show_success(self, files):
        """Muestra el estado de éxito con archivos descargados"""
        self.download_progress.visible = False
        self.download_status.value = f"✓ {len(files)} archivo(s)"
        self.download_status.color = COLORS["success"]
        
        # Mostrar nombres de archivos
        file_names = [os.path.basename(f) for f in files]
        if len(file_names) <= 2:
            self.attachment_count.value = f"📎 {', '.join(file_names)}"
        else:
            self.attachment_count.value = f"📎 {file_names[0]}, {file_names[1]} y {len(file_names)-2} más"
        
        self.attachment_count.visible = True
        self.status_icon.name = ft.Icons.CHECK_CIRCLE
        self.status_icon.color = COLORS["success"]
    
    def show_no_attachments(self):
        """Muestra que no hay adjuntos"""
        self.download_progress.visible = False
        self.download_status.value = "Sin adjuntos"
        self.download_status.color = COLORS["text_light"]
        self.status_icon.name = ft.Icons.MAIL_OUTLINE
        self.status_icon.color = COLORS["text_light"]
    
    def show_error(self):
        """Muestra un error en la descarga"""
        self.download_progress.visible = False
        self.download_status.value = "⚠ Error"
        self.download_status.color = COLORS["error"]
        self.download_status.visible = True
        self.status_icon.name = ft.Icons.ERROR_OUTLINE
        self.status_icon.color = COLORS["error"]
