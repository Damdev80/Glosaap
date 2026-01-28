"""
Vista de mensajes - Muestra y gestiona los correos encontrados
Soporte completo de temas claro/oscuro
"""
import flet as ft
from app.ui.styles import FONT_SIZES, SPACING, WINDOW_SIZES
from app.ui.components.message_row import MessageRow
from app.ui.components.loading_overlay import LoadingOverlay, ToastNotification, LoadingButton


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
        self.message_rows = {}  # Diccionario para acceder a MessageRow por ID
        
        # Componentes de loading y feedback
        self.loading_overlay = LoadingOverlay(page)
        self.toast_notification = ToastNotification(page)
        
        # Componentes - sin colores hardcodeados para soporte de temas
        self.messages_list = ft.Column([], scroll=ft.ScrollMode.AUTO, expand=True, spacing=0)
        self.messages_status = ft.Text("", size=FONT_SIZES["small"])
        self.loading_bar = ft.ProgressBar(visible=False)
        
        # Barra de progreso mejorada
        self.processing_progress = ft.ProgressBar(
            value=None  # None = indeterminado
        )
        self.processing_percentage = ft.Text(
            "", 
            size=12, 
            weight=ft.FontWeight.W_500
        )
        self.processing_spinner = ft.ProgressRing(
            width=18, 
            height=18, 
            stroke_width=2
        )
        self.processing_status = ft.Text("", size=FONT_SIZES["small"])
        
        # Contenedor de progreso (se muestra/oculta completo)
        self.processing_container = ft.Container(
            content=ft.Column([
                ft.Row([
                    self.processing_spinner,
                    self.processing_status,
                    ft.Container(expand=True),
                    self.processing_percentage,
                ], spacing=8, alignment=ft.MainAxisAlignment.START),
                self.processing_progress,
            ], spacing=6, tight=True),
            visible=False,
            padding=ft.padding.only(top=10)
        )
        
        self.search_info_text = ft.Text("", size=12)
        
        # Botones con colores visibles en ambos temas
        self.process_eps_btn = ft.ElevatedButton(
            "📊 Procesar",
            icon=ft.Icons.TABLE_CHART,
            visible=False,
            on_click=lambda e: self.on_process(),
            style=ft.ButtonStyle(
                color=ft.Colors.WHITE,
                bgcolor=ft.Colors.PRIMARY,
            )
        )
        
        self.download_selected_btn = ft.ElevatedButton(
            "📥 Descargar seleccionados",
            icon=ft.Icons.DOWNLOAD,
            visible=False,
            disabled=True,
            on_click=lambda e: self.on_download_selected(),
            style=ft.ButtonStyle(
                color=ft.Colors.WHITE,
                bgcolor=ft.Colors.SECONDARY,
            )
        )
        
        self.select_all_checkbox = ft.Checkbox(
            label="Seleccionar todos",
            value=False,
            visible=False,  # Ocultar - ya no es necesario
            on_change=self._on_select_all_changed
        )
        
        self.selected_count_text = ft.Text(
            "0 seleccionados",
            size=12,
        )
        
        # Crear vista
        self.container = self._create_view()
    
    def _create_view(self):
        """Crea el contenedor de la vista"""
        back_btn = ft.IconButton(
            icon=ft.Icons.ARROW_BACK,
            tooltip="Volver (ESC)",
            on_click=lambda e: self.on_back()
        )
        
        refresh_btn = ft.IconButton(
            icon=ft.Icons.REFRESH,
            tooltip="Actualizar (F5)",
            on_click=lambda e: self.on_refresh()
        )
        
        # Breadcrumb navigation
        breadcrumb = ft.Row([
            ft.TextButton(
                "Dashboard",
                style=ft.ButtonStyle(color=ft.Colors.BLUE),
                on_click=lambda e: self.page.data.get('navigation_controller', {}).get('go_to_dashboard', lambda: None)() if hasattr(self.page, 'data') and self.page.data else None
            ),
            ft.Text(" > ", color=ft.Colors.GREY),
            ft.TextButton(
                "Selección EPS",
                style=ft.ButtonStyle(color=ft.Colors.BLUE),
                on_click=lambda e: self.on_back()
            ),
            ft.Text(" > ", color=ft.Colors.GREY),
            ft.Text("Mensajes", weight=ft.FontWeight.BOLD),
        ], spacing=0)
        
        # Usar Card para el header - soporte de temas automático
        return ft.Container(
            content=ft.Column([
                # Header
                ft.Card(
                    content=ft.Container(
                        content=ft.Column([
                            ft.Row([
                                ft.Row([
                                    back_btn,
                                    ft.Text("Correos con 'glosa'", size=FONT_SIZES["heading"], 
                                           weight=ft.FontWeight.W_400),
                                ], spacing=0),
                                refresh_btn
                            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                            # Breadcrumb
                            ft.Container(
                                content=breadcrumb,
                                padding=ft.padding.only(left=45, top=5)
                            )
                        ], spacing=5),
                        padding=SPACING["md"],
                    ),
                    elevation=0,
                    margin=0,
                ),
                # Info de búsqueda
                ft.Container(
                    content=ft.Row([
                        ft.Icon(ft.Icons.INFO_OUTLINE, size=14),
                        self.search_info_text
                    ], spacing=8, alignment=ft.MainAxisAlignment.CENTER),
                    padding=ft.padding.symmetric(horizontal=SPACING["md"], vertical=8),
                ),
                self.loading_bar,
                ft.Container(
                    content=self.messages_list,
                    expand=True,
                    padding=0,
                ),
                # Barra de selección y descarga manual
                ft.Card(
                    content=ft.Container(
                        content=ft.Row([
                            self.select_all_checkbox,
                            self.selected_count_text,
                            ft.Container(expand=True),
                            self.download_selected_btn
                        ], spacing=15, alignment=ft.MainAxisAlignment.START),
                        padding=ft.padding.symmetric(horizontal=15, vertical=10),
                    ),
                    elevation=0,
                    margin=0,
                ),
                # Procesamiento
                ft.Card(
                    content=ft.Container(
                        content=ft.Column([
                            ft.Row([self.process_eps_btn], spacing=SPACING["md"], 
                                  alignment=ft.MainAxisAlignment.CENTER),
                            # Indicador de progreso mejorado
                            self.processing_container,
                        ], spacing=SPACING["sm"]),
                        padding=SPACING["md"],
                    ),
                    elevation=0,
                    margin=0,
                ),
                ft.Container(
                    content=self.messages_status,
                    padding=SPACING["md"],
                )
            ], expand=True, spacing=0),
            bgcolor=ft.Colors.SURFACE,  # Fondo sólido para cubrir vistas detrás
            expand=True,
            visible=False
        )
    
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
    
    # ==================== MÉTODOS DE LOADING Y FEEDBACK ====================
    
    def show_loading(self, message: str):
        """Muestra overlay de carga con mensaje"""
        self.loading_overlay.show(message)
    
    def hide_loading(self):
        """Oculta overlay de carga"""
        self.loading_overlay.hide()
    
    def show_toast(self, message: str, is_success: bool = True):
        """Muestra notificación toast"""
        if is_success:
            self.toast_notification.success(message)
        else:
            self.toast_notification.error(message)
    
    def set_loading_progress(self, current: int, total: int, message: str = ""):
        """Actualiza progreso de carga"""
        if total > 0:
            progress = current / total
            self.processing_progress.value = progress
            self.processing_percentage.value = f"{int(progress * 100)}%"
        
        if message:
            self.processing_status.value = message
        
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
        self.message_rows.clear()  # Limpiar referencias
        self.select_all_checkbox.value = False
        
        if not messages:
            self.messages_list.controls.append(
                ft.Container(
                    content=ft.Column([
                        ft.Icon(ft.Icons.INBOX, size=64, color=ft.Colors.OUTLINE),
                        ft.Text("No se encontraron mensajes", 
                               size=FONT_SIZES["body"])
                    ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=SPACING["md"]),
                    padding=SPACING["xxl"],
                    alignment=ft.alignment.center
                )
            )
        else:
            for msg in messages:
                row = MessageRow(msg, on_checkbox_change=self._on_message_checkbox_changed)
                self.messages_list.controls.append(row.container)
                # Guardar referencia para actualizar estados
                msg_id = msg.get("id")
                if msg_id:
                    self.message_rows[msg_id] = row
        
        self.search_info_text.value = search_info
        self._update_selection_ui()
        self.page.update()
    
    def set_loading(self, is_loading, status_text=""):
        """Muestra/oculta el indicador de carga"""
        self.loading_bar.visible = is_loading
        self.messages_status.value = status_text
        self.page.update()
    
    def set_processing(self, is_processing, status_text="", progress=None):
        """
        Muestra/oculta el indicador de procesamiento
        
        Args:
            is_processing: Si está procesando
            status_text: Texto de estado
            progress: Valor de progreso (0.0 a 1.0) o None para indeterminado
        """
        # Mostrar/ocultar el contenedor de progreso completo
        self.processing_container.visible = is_processing
        self.processing_status.value = status_text
        
        if is_processing:
            if progress is not None:
                self.processing_progress.value = progress
                self.processing_percentage.value = f"{int(progress * 100)}%"
            else:
                self.processing_progress.value = None  # Indeterminado (animación)
                self.processing_percentage.value = ""
        else:
            self.processing_percentage.value = ""
        
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
        if message_id in self.message_rows:
            self.message_rows[message_id].update_status(status_text, is_error)
            self.page.update()
