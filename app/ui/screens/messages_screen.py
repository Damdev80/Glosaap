import flet as ft
import threading
import os
from app.ui.styles import COLORS, FONT_SIZES, SPACING


class MessagesScreen:
    """
    Pantalla de listado de correos con 'glosa' en el asunto.
    
    Busca y muestra todos los correos que contienen la palabra 'glosa'
    en el asunto, permitiendo descargar sus adjuntos.
    """
    
    def __init__(self, page: ft.Page, imap_client, on_logout=None):
        """
        Inicializa la pantalla de mensajes.
        
        Args:
            page: Referencia a la página principal de Flet
            imap_client: Cliente IMAP ya autenticado
            on_logout: Callback opcional para cerrar sesión
        """
        self.page = page
        self.client = imap_client
        self.on_logout = on_logout
        self._is_loading = False
        
        # Componentes de la interfaz de usuario
        self.messages_column = ft.Column(
            scroll=ft.ScrollMode.AUTO,
            expand=True,
            spacing=SPACING["sm"],
        )
        
        # Loading indicator
        self.loading_indicator = ft.Column(
            [
                ft.ProgressRing(width=40, height=40, stroke_width=3, color=COLORS["primary"]),
                ft.Container(height=SPACING["sm"]),
                ft.Text("Buscando correos...", size=FONT_SIZES["body"], color=COLORS["text_secondary"]),
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            alignment=ft.MainAxisAlignment.CENTER,
            visible=False,
        )
        
        # Status bar
        self.status = ft.Text("", size=FONT_SIZES["small"], color=COLORS["text_secondary"])
        self.status_icon = ft.Icon(ft.Icons.INFO_OUTLINE, size=16, color=COLORS["info"], visible=False)
        
    def show_status(self, msg: str, icon: str = None, color: str = None):
        """Actualiza el mensaje de estado."""
        self.status.value = msg
        self.status.color = color or COLORS["text_secondary"]
        if icon:
            self.status_icon.visible = True
            self.status_icon.name = icon
            self.status_icon.color = color or COLORS["info"]
        else:
            self.status_icon.visible = False
        self.page.update()
    
    def _download_attachments_worker(self, msg_id, msg_subject, btn: ft.ElevatedButton):
        """Thread worker que descarga adjuntos de un mensaje específico."""
        try:
            btn.disabled = True
            btn.text = "Descargando..."
            self.page.update()
            
            self.show_status(f"Descargando adjuntos de '{msg_subject}'...", ft.Icons.DOWNLOADING, COLORS["info"])
            
            saved = self.client.download_attachments(msg_id)
            
            if saved:
                self.show_status(
                    f"✓ {len(saved)} archivo(s) descargados", 
                    ft.Icons.CHECK_CIRCLE, 
                    COLORS["success"]
                )
            else:
                self.show_status("Sin adjuntos en este correo", ft.Icons.INFO_OUTLINE, COLORS["warning"])
                
        except Exception as e:
            self.show_status(f"Error: {e}", ft.Icons.ERROR_OUTLINE, COLORS["error"])
        finally:
            btn.disabled = False
            btn.text = "Descargar"
            self.page.update()
    
    def _on_download_click(self, msg_id, msg_subject, btn):
        """Maneja el evento de click en el botón de descarga."""
        threading.Thread(
            target=self._download_attachments_worker,
            args=(msg_id, msg_subject, btn),
            daemon=True
        ).start()
    
    def _build_message_tile(self, msg, index: int):
        """Construye una tarjeta visual para un mensaje individual."""
        has_attachments = msg.get("has_attachments", False)
        
        download_btn = ft.ElevatedButton(
            "Descargar",
            icon=ft.Icons.DOWNLOAD_ROUNDED,
            disabled=not has_attachments,
            style=ft.ButtonStyle(
                bgcolor={
                    ft.ControlState.DEFAULT: COLORS["primary"],
                    ft.ControlState.HOVERED: COLORS["primary_hover"],
                    ft.ControlState.DISABLED: COLORS["text_muted"],
                },
                color=COLORS["bg_white"],
                shape=ft.RoundedRectangleBorder(radius=8),
                padding=ft.padding.symmetric(horizontal=16, vertical=8),
            ),
        )
        
        # Asignar callback con referencia al botón
        download_btn.on_click = lambda e, mid=msg["id"], subj=msg.get("subject"), b=download_btn: self._on_download_click(mid, subj, b)
        
        # Badge de adjuntos
        attachment_badge = ft.Container(
            content=ft.Row(
                [
                    ft.Icon(ft.Icons.ATTACH_FILE_ROUNDED, size=14, color=COLORS["success"] if has_attachments else COLORS["text_light"]),
                    ft.Text(
                        "Adjuntos" if has_attachments else "Sin adjuntos",
                        size=FONT_SIZES["caption"],
                        color=COLORS["success"] if has_attachments else COLORS["text_light"],
                    ),
                ],
                spacing=4,
                tight=True,
            ),
            padding=ft.padding.symmetric(horizontal=8, vertical=4),
            border_radius=12,
            bgcolor=COLORS["success_light"] if has_attachments else COLORS["bg_input"],
        )
        
        return ft.Container(
            content=ft.Row(
                [
                    # Número de mensaje
                    ft.Container(
                        content=ft.Text(str(index + 1), size=FONT_SIZES["small"], color=COLORS["text_light"]),
                        width=32,
                        alignment=ft.alignment.center,
                    ),
                    # Contenido del mensaje
                    ft.Container(
                        content=ft.Column(
                            [
                                ft.Text(
                                    msg.get("subject") or "(sin asunto)",
                                    weight=ft.FontWeight.W_600,
                                    size=FONT_SIZES["body"],
                                    color=COLORS["text_primary"],
                                    max_lines=1,
                                    overflow=ft.TextOverflow.ELLIPSIS,
                                ),
                                ft.Row(
                                    [
                                        ft.Icon(ft.Icons.PERSON_OUTLINE, size=14, color=COLORS["text_light"]),
                                        ft.Text(
                                            msg.get('from', 'Desconocido'),
                                            size=FONT_SIZES["caption"],
                                            color=COLORS["text_secondary"],
                                            max_lines=1,
                                            overflow=ft.TextOverflow.ELLIPSIS,
                                        ),
                                        ft.Container(width=SPACING["md"]),
                                        ft.Icon(ft.Icons.CALENDAR_TODAY, size=14, color=COLORS["text_light"]),
                                        ft.Text(
                                            msg.get('date', ''),
                                            size=FONT_SIZES["caption"],
                                            color=COLORS["text_secondary"],
                                        ),
                                    ],
                                    spacing=4,
                                ),
                            ],
                            spacing=4,
                            tight=True,
                        ),
                        expand=True,
                    ),
                    # Badge y botón
                    attachment_badge,
                    download_btn,
                ],
                spacing=SPACING["md"],
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            padding=ft.padding.symmetric(horizontal=SPACING["md"], vertical=SPACING["sm"]),
            bgcolor=COLORS["bg_white"],
            border_radius=10,
            border=ft.border.all(1, COLORS["border_light"]),
            animate=ft.Animation(150, ft.AnimationCurve.EASE_OUT),
        )
    
    def _load_messages_worker(self):
        """Thread worker que busca y carga mensajes con 'glosa' en el asunto."""
        if self._is_loading:
            return
            
        self._is_loading = True
        try:
            self.loading_indicator.visible = True
            self.messages_column.controls.clear()
            self.page.update()
            
            msgs = self.client.search_by_subject("glosa", limit=1000)
            
            self.loading_indicator.visible = False
            
            if not msgs:
                self.messages_column.controls.append(
                    ft.Container(
                        content=ft.Column(
                            [
                                ft.Icon(ft.Icons.INBOX_OUTLINED, size=64, color=COLORS["text_light"]),
                                ft.Container(height=SPACING["md"]),
                                ft.Text(
                                    "No se encontraron correos",
                                    size=FONT_SIZES["subheading"],
                                    color=COLORS["text_secondary"],
                                    weight=ft.FontWeight.W_500,
                                ),
                                ft.Text(
                                    "No hay correos con 'glosa' en el asunto",
                                    size=FONT_SIZES["body"],
                                    color=COLORS["text_light"],
                                ),
                            ],
                            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        ),
                        alignment=ft.alignment.center,
                        padding=SPACING["xxl"],
                    )
                )
            else:
                for i, msg in enumerate(msgs):
                    self.messages_column.controls.append(self._build_message_tile(msg, i))
            
            self.show_status(f"{len(msgs)} correo(s) encontrados", ft.Icons.CHECK_CIRCLE, COLORS["success"])
            self.page.update()
            
        except Exception as ex:
            self.loading_indicator.visible = False
            self.show_status(f"Error: {ex}", ft.Icons.ERROR_OUTLINE, COLORS["error"])
            self.page.update()
        finally:
            self._is_loading = False
    
    def load_messages(self):
        """Inicia la carga de mensajes en segundo plano."""
        threading.Thread(target=self._load_messages_worker, daemon=True).start()
    
    def _on_refresh_click(self, e):
        """Maneja el evento de click en el botón de refrescar."""
        self.load_messages()
    
    def build(self):
        """Construye y retorna el árbol de componentes de la pantalla."""
        # Header moderno
        header = ft.Container(
            content=ft.Row(
                [
                    ft.Row(
                        [
                            ft.Icon(ft.Icons.EMAIL_OUTLINED, size=24, color=COLORS["primary"]),
                            ft.Text(
                                "Correos con 'glosa'",
                                size=FONT_SIZES["heading"],
                                weight=ft.FontWeight.BOLD,
                                color=COLORS["text_primary"],
                            ),
                        ],
                        spacing=SPACING["sm"],
                    ),
                    ft.IconButton(
                        ft.Icons.REFRESH_ROUNDED,
                        on_click=self._on_refresh_click,
                        tooltip="Recargar mensajes",
                        icon_color=COLORS["primary"],
                        style=ft.ButtonStyle(
                            bgcolor={ft.ControlState.HOVERED: COLORS["primary_light"]},
                            shape=ft.CircleBorder(),
                        ),
                    ),
                ],
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            ),
            padding=ft.padding.symmetric(horizontal=SPACING["lg"], vertical=SPACING["md"]),
            bgcolor=COLORS["bg_white"],
            border=ft.border.only(bottom=ft.BorderSide(1, COLORS["border_light"])),
        )
        
        # Status bar
        status_bar = ft.Container(
            content=ft.Row(
                [self.status_icon, self.status],
                spacing=SPACING["xs"],
            ),
            padding=ft.padding.symmetric(horizontal=SPACING["lg"], vertical=SPACING["sm"]),
            bgcolor=COLORS["bg_light"],
            border=ft.border.only(top=ft.BorderSide(1, COLORS["border_light"])),
        )
        
        return ft.Column(
            [
                header,
                ft.Container(
                    content=ft.Stack(
                        [
                            self.messages_column,
                            ft.Container(
                                content=self.loading_indicator,
                                alignment=ft.alignment.center,
                                expand=True,
                            ),
                        ]
                    ),
                    expand=True,
                    padding=SPACING["md"],
                    bgcolor=COLORS["bg_light"],
                ),
                status_bar,
            ],
            expand=True,
            spacing=0,
        )
