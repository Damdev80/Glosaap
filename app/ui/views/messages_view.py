"""
Vista de mensajes - Muestra y gestiona los correos encontrados
"""
import flet as ft
from app.ui.styles import COLORS, FONT_SIZES, SPACING, WINDOW_SIZES
from app.ui.components.message_row import MessageRow


class MessagesView:
    """Vista para listar y gestionar mensajes de correo"""
    
    def __init__(self, page: ft.Page, on_back, on_refresh, on_download_selected, on_process):
        """
        Inicializa la vista de mensajes
        
        Args:
            page: Página de Flet
            on_back: Callback para volver atrás
            on_refresh: Callback para actualizar mensajes
            on_download_selected: Callback para descargar mensajes seleccionados
            on_process: Callback para procesar mensajes con EPS
        """
        self.page = page
        self.on_back = on_back
        self.on_refresh = on_refresh
        self.on_download_selected = on_download_selected
        self.on_process = on_process
        
        # Estado
        self.selected_messages = set()
        
        # Componentes
        self.messages_list = ft.Column([], scroll=ft.ScrollMode.AUTO, expand=True, spacing=0)
        self.messages_status = ft.Text("", size=FONT_SIZES["small"], color=COLORS["text_secondary"])
        self.loading_bar = ft.ProgressBar(visible=False, color=COLORS["primary"], bgcolor=COLORS["border"])
        self.processing_bar = ft.ProgressBar(visible=False, color=COLORS["success"], bgcolor=COLORS["border"])
        self.processing_status = ft.Text("", size=FONT_SIZES["small"], color=COLORS["text_secondary"])
        self.search_info_text = ft.Text("", size=12, color=COLORS["text_secondary"])
        
        # Botones
        self.process_eps_btn = ft.ElevatedButton(
            "📊 Procesar",
            icon=ft.Icons.TABLE_CHART,
            bgcolor=COLORS["primary"],
            color=COLORS["bg_white"],
            visible=False,
            on_click=lambda e: self.on_process()
        )
        
        self.download_selected_btn = ft.ElevatedButton(
            "📥 Descargar seleccionados",
            icon=ft.Icons.DOWNLOAD,
            bgcolor=COLORS["success"],
            color=COLORS["bg_white"],
            visible=False,
            disabled=True,
            on_click=lambda e: self.on_download_selected()
        )
        
        self.select_all_checkbox = ft.Checkbox(
            label="Seleccionar todos",
            value=False,
            fill_color=COLORS["primary"],
            check_color=COLORS["bg_white"],
            visible=False,  # Ocultar - ya no es necesario
            on_change=self._on_select_all_changed
        )
        
        self.selected_count_text = ft.Text(
            "0 seleccionados",
            size=12,
            color=COLORS["text_secondary"]
        )
        
        # Crear vista
        self.container = self._create_view()
    
    def _create_view(self):
        """Crea el contenedor de la vista"""
        back_btn = ft.IconButton(
            icon=ft.Icons.ARROW_BACK,
            icon_color=COLORS["text_secondary"],
            tooltip="Volver",
            on_click=lambda e: self.on_back()
        )
        
        refresh_btn = ft.IconButton(
            icon=ft.Icons.REFRESH,
            icon_color=COLORS["primary"],
            tooltip="Actualizar",
            on_click=lambda e: self.on_refresh()
        )
        
        return ft.Column([
            # Header
            ft.Container(
                content=ft.Row([
                    ft.Row([
                        back_btn,
                        ft.Text("Correos con 'glosa'", size=FONT_SIZES["heading"], 
                               weight=ft.FontWeight.W_400, color=COLORS["text_primary"]),
                    ], spacing=0),
                    refresh_btn
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                bgcolor=COLORS["bg_white"],
                padding=SPACING["lg"],
                border=ft.border.only(bottom=ft.BorderSide(1, COLORS["border"]))
            ),
            # Info de búsqueda
            ft.Container(
                content=ft.Row([
                    ft.Icon(ft.Icons.INFO_OUTLINE, size=14, color=COLORS["primary"]),
                    self.search_info_text
                ], spacing=8, alignment=ft.MainAxisAlignment.CENTER),
                padding=ft.padding.symmetric(horizontal=SPACING["md"], vertical=8),
                bgcolor=COLORS["bg_input"]
            ),
            self.loading_bar,
            ft.Container(
                content=self.messages_list,
                expand=True,
                padding=0,
                bgcolor=COLORS["bg_light"]
            ),
            # Barra de selección y descarga manual
            ft.Container(
                content=ft.Row([
                    self.select_all_checkbox,
                    self.selected_count_text,
                    ft.Container(expand=True),
                    self.download_selected_btn
                ], spacing=15, alignment=ft.MainAxisAlignment.START),
                padding=ft.padding.symmetric(horizontal=15, vertical=10),
                bgcolor=COLORS["bg_input"],
                border=ft.border.only(top=ft.BorderSide(1, COLORS["border"]))
            ),
            # Procesamiento
            ft.Container(
                content=ft.Column([
                    ft.Row([self.process_eps_btn], spacing=SPACING["md"], 
                          alignment=ft.MainAxisAlignment.CENTER),
                    self.processing_bar,
                    self.processing_status
                ], spacing=SPACING["sm"]),
                padding=SPACING["md"],
                bgcolor=COLORS["bg_white"],
                border=ft.border.only(top=ft.BorderSide(1, COLORS["border"]))
            ),
            ft.Container(
                content=self.messages_status,
                padding=SPACING["md"],
                bgcolor=COLORS["bg_white"]
            )
        ], expand=True, spacing=0, visible=False)
    
    def _on_select_all_changed(self, e):
        """Maneja el cambio del checkbox de seleccionar todos"""
        is_checked = e.control.value
        
        # Actualizar todas las filas de mensajes
        for row in self.messages_list.controls:
            if isinstance(row, MessageRow):
                row.checkbox.value = is_checked
                msg_id = row.message_data.get("id")
                if is_checked:
                    self.selected_messages.add(msg_id)
                else:
                    self.selected_messages.discard(msg_id)
        
        self._update_selection_ui()
    
    def _on_message_checkbox_changed(self, message_data, is_checked):
        """Maneja el cambio de checkbox individual de mensaje"""
        msg_id = message_data.get("id")
        
        if is_checked:
            self.selected_messages.add(msg_id)
        else:
            self.selected_messages.discard(msg_id)
        
        self._update_selection_ui()
    
    def _update_selection_ui(self):
        """Actualiza la UI según los mensajes seleccionados"""
        count = len(self.selected_messages)
        self.selected_count_text.value = f"{count} seleccionado{'s' if count != 1 else ''}"
        self.download_selected_btn.disabled = count == 0
        
        # Actualizar checkbox "seleccionar todos"
        total_messages = len([c for c in self.messages_list.controls if isinstance(c, MessageRow)])
        self.select_all_checkbox.value = count > 0 and count == total_messages
        
        self.page.update()
    
    def show_messages(self, messages, search_info=""):
        """
        Muestra una lista de mensajes
        
        Args:
            messages: Lista de diccionarios con info de mensajes
            search_info: Texto informativo de la búsqueda
        """
        self.messages_list.controls.clear()
        self.selected_messages.clear()
        self.select_all_checkbox.value = False
        
        if not messages:
            self.messages_list.controls.append(
                ft.Container(
                    content=ft.Column([
                        ft.Icon(ft.Icons.INBOX, size=64, color=COLORS["border"]),
                        ft.Text("No se encontraron mensajes", 
                               size=FONT_SIZES["body"], 
                               color=COLORS["text_secondary"])
                    ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=SPACING["md"]),
                    padding=SPACING["xxl"],
                    alignment=ft.alignment.center
                )
            )
        else:
            for msg in messages:
                row = MessageRow(msg, on_checkbox_change=self._on_message_checkbox_changed)
                self.messages_list.controls.append(row.container)
        
        self.search_info_text.value = search_info
        self._update_selection_ui()
        self.page.update()
    
    def set_loading(self, is_loading, status_text=""):
        """Muestra/oculta el indicador de carga"""
        self.loading_bar.visible = is_loading
        self.messages_status.value = status_text
        self.page.update()
    
    def set_processing(self, is_processing, status_text=""):
        """Muestra/oculta el indicador de procesamiento"""
        self.processing_bar.visible = is_processing
        self.processing_status.value = status_text
        self.page.update()
    
    def show_process_button(self, visible=True):
        """Muestra/oculta el botón de procesar EPS"""
        self.process_eps_btn.visible = visible
        self.page.update()
    
    def show_download_controls(self, visible=True):
        """Muestra/oculta los controles de descarga manual"""
        self.download_selected_btn.visible = visible
        self.page.update()
    
    def show(self):
        """Muestra la vista"""
        self.container.visible = True
        self.page.update()
    
    def hide(self):
        """Oculta la vista"""
        self.container.visible = False
        self.page.update()
    
    def get_selected_messages(self):
        """Retorna los IDs de mensajes seleccionados"""
        return self.selected_messages
    
    def update_message_status(self, message_id, status_text, is_error=False):
        """
        Actualiza el estado de un mensaje específico
        
        Args:
            message_id: ID del mensaje
            status_text: Texto de estado
            is_error: Si es True, muestra en rojo
        """
        for control in self.messages_list.controls:
            if isinstance(control, MessageRow):
                if control.message_data.get("id") == message_id:
                    control.update_status(status_text, is_error)
                    break
        self.page.update()
