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
    
    def __init__(self, page: ft.Page, on_back, on_refresh, on_download_selected, on_process, navigation_controller=None):
        """
        Inicializa la vista de mensajes
        
        Args:
            page: Página de Flet
            on_back: Callback para volver atrás (messages -> eps)
            on_refresh: Callback para actualizar mensajes
            on_download_selected: Callback para descargar mensajes seleccionados
            on_process: Callback para procesar mensajes con EPS
            navigation_controller: Canal único de navegación (breadcrumb a dashboard)
        """
        self.page = page
        self.on_back = on_back
        self.on_refresh = on_refresh
        self.on_download_selected = on_download_selected
        self.on_process = on_process
        self.navigation_controller = navigation_controller
        
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

        # Filtro por texto (en memoria: asunto/remitente) + paginación 50/página
        self._all_messages = []
        self._filtered_messages = []
        self._filter_text = ""
        self._current_page = 1
        self._page_size = 50
        self.filter_field = ft.TextField(
            hint_text="Filtrar por asunto o remitente...",
            prefix_icon=ft.Icons.SEARCH,
            expand=True,
            dense=True,
            on_change=self._on_filter_changed,
        )
        self.prev_btn = ft.IconButton(
            icon=ft.Icons.CHEVRON_LEFT,
            tooltip="Anterior",
            on_click=self._on_prev_page,
        )
        self.next_btn = ft.IconButton(
            icon=ft.Icons.CHEVRON_RIGHT,
            tooltip="Siguiente",
            on_click=self._on_next_page,
        )
        self.page_label = ft.Text("Página 1 de 1", size=12)
        
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
        
        # Breadcrumb navigation (usa NavigationController; sin page.data)
        breadcrumb = ft.Row([
            ft.TextButton(
                "Dashboard",
                style=ft.ButtonStyle(color=ft.Colors.BLUE),
                on_click=lambda e: self._go_to_dashboard()
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
                # Filtro + paginación (50 por página)
                ft.Container(
                    content=ft.Row([
                        self.filter_field,
                        self.prev_btn,
                        self.page_label,
                        self.next_btn,
                    ], spacing=8, alignment=ft.MainAxisAlignment.CENTER,
                       vertical_alignment=ft.CrossAxisAlignment.CENTER),
                    padding=ft.padding.symmetric(horizontal=SPACING["md"], vertical=6),
                ),
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
    
    def _on_filter_changed(self, e):
        """Filtra asunto/remitente en memoria y vuelve a la página 1."""
        self._filter_text = (e.control.value or "").strip().lower()
        self._current_page = 1
        self._apply_filter()
        self._render_page()

    def _apply_filter(self):
        """Aplica el filtro de texto sobre los mensajes en memoria."""
        if not self._filter_text:
            self._filtered_messages = list(self._all_messages)
            return
        query = self._filter_text
        filtered = []
        for msg in self._all_messages:
            subject = str(msg.get("subject") or "").lower()
            sender = str(
                msg.get("from") or msg.get("sender") or msg.get("remitente") or ""
            ).lower()
            if query in subject or query in sender:
                filtered.append(msg)
        self._filtered_messages = filtered

    def _total_pages(self):
        """Total de páginas (50 por página, mínimo 1)."""
        if not self._filtered_messages:
            return 1
        return max(1, (len(self._filtered_messages) + self._page_size - 1) // self._page_size)

    def _refresh_pagination_ui(self):
        """Actualiza etiqueta y estado de Anterior/Siguiente."""
        total_pages = self._total_pages()
        self._current_page = min(max(self._current_page, 1), total_pages)
        self.page_label.value = f"Página {self._current_page} de {total_pages}"
        self.prev_btn.disabled = self._current_page <= 1
        self.next_btn.disabled = self._current_page >= total_pages

    def _on_prev_page(self, e):
        """Página anterior (hilo principal: page.update OK)."""
        if self._current_page > 1:
            self._current_page -= 1
            self._render_page()

    def _on_next_page(self, e):
        """Página siguiente (hilo principal: page.update OK)."""
        if self._current_page < self._total_pages():
            self._current_page += 1
            self._render_page()

    def _render_page(self):
        """Renderiza la página actual desde los mensajes filtrados."""
        self.messages_list.controls.clear()
        if not self._filtered_messages:
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
            start = (self._current_page - 1) * self._page_size
            end = start + self._page_size
            for msg in self._filtered_messages[start:end]:
                msg_id = msg.get("id")
                row = self.message_rows.get(msg_id) if msg_id else None
                if row is None:
                    row = MessageRow(msg, on_checkbox_change=self._on_message_checkbox_changed)
                    if msg_id:
                        self.message_rows[msg_id] = row
                else:
                    # Restaurar selección al paginar
                    row.checkbox.value = msg_id in self.selected_messages
                self.messages_list.controls.append(row.container)
        self._refresh_pagination_ui()
        self._update_selection_ui(publish=False)
        self.page.update()

    def _go_to_dashboard(self):
        """Breadcrumb a dashboard vía NavigationController (sin page.data)."""
        if self.navigation_controller is not None:
            self.navigation_controller.go_to_dashboard()

    def _on_select_all_changed(self, e):
        """Maneja el cambio del checkbox de seleccionar todos (sobre filtrados)"""
        is_checked = e.control.value

        for msg in self._filtered_messages:
            msg_id = msg.get("id")
            if msg_id is None:
                continue
            if is_checked:
                self.selected_messages.add(msg_id)
            else:
                self.selected_messages.discard(msg_id)
            row = self.message_rows.get(msg_id)
            if row is not None:
                row.checkbox.value = is_checked

        self._update_selection_ui()
    
    def _on_message_checkbox_changed(self, message_data, is_checked):
        """Maneja el cambio de checkbox individual de mensaje"""
        msg_id = message_data.get("id")
        
        if is_checked:
            self.selected_messages.add(msg_id)
        else:
            self.selected_messages.discard(msg_id)
        
        self._update_selection_ui()
    
    def _update_selection_ui(self, publish=True):
        """Actualiza la UI según los mensajes seleccionados"""
        count = len(self.selected_messages)
        self.selected_count_text.value = f"{count} seleccionado{'s' if count != 1 else ''}"
        self.download_selected_btn.disabled = count == 0

        # Total sobre mensajes filtrados (no solo la página visible)
        total_messages = len(self._filtered_messages) if self._all_messages else 0
        self.select_all_checkbox.value = count > 0 and count == total_messages

        if publish:
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
        Muestra una lista de mensajes (con filtro en memoria y paginación 50/página)

        Args:
            messages: Lista de diccionarios con info de mensajes
            search_info: Texto informativo de la búsqueda
        """
        self._all_messages = list(messages or [])
        self.selected_messages.clear()
        self.message_rows.clear()  # Limpiar referencias
        self.select_all_checkbox.value = False
        self._current_page = 1

        for msg in self._all_messages:
            row = MessageRow(msg, on_checkbox_change=self._on_message_checkbox_changed)
            msg_id = msg.get("id")
            if msg_id:
                self.message_rows[msg_id] = row

        self._apply_filter()
        self._render_page()
        self.search_info_text.value = search_info
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
