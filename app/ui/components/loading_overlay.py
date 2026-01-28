"""
Componente de overlay de carga con estados visuales.

Este módulo proporciona componentes reutilizables para mostrar
estados de carga, progreso y feedback visual durante operaciones
asíncronas o de larga duración.

Componentes:
    - LoadingOverlay: Overlay modal con spinner y mensaje
    - LoadingButton: Botón con estado de carga integrado
    - ProgressIndicator: Indicador de progreso con porcentaje
    - ToastNotification: Notificaciones toast no-bloqueantes

Ejemplo de uso:
    ```python
    # Crear overlay
    loading = LoadingOverlay(page)
    
    # Mostrar durante operación
    loading.show("Procesando archivos...")
    await process_files()
    loading.hide()
    
    # O usar con contexto
    with loading.context("Cargando datos..."):
        data = await fetch_data()
    ```

Author: Glosaap Team
Version: 1.0.0
"""
import flet as ft
from typing import Optional, Callable
from contextlib import contextmanager
from app.ui.styles import FONT_SIZES, SPACING
from typing  import Optional, Callable

class LoadingOverlay:
    """
    Overlay de carga modal con spinner animado y mensaje personalizable.
    
    Crea una capa semi-transparente sobre toda la interfaz que bloquea
    la interacción del usuario mientras se ejecuta una operación.
    
    Attributes:
        page (ft.Page): Página de Flet donde se mostrará el overlay.
        _overlay (ft.Container): Contenedor del overlay.
        _message (ft.Text): Texto del mensaje de carga.
        _progress (ft.ProgressRing): Indicador de progreso circular.
        _is_visible (bool): Estado de visibilidad actual.
    
    Example:
        ```python
        loading = LoadingOverlay(page)
        loading.show("Procesando...")
        # ... operación larga ...
        loading.hide()
        ```
    """
    
    def __init__(self, page: ft.Page):
        """
        Inicializa el overlay de carga.
        
        Args:
            page: Instancia de ft.Page donde se renderizará el overlay.
        """
        self.page = page
        self._is_visible = False
        self._message = ft.Text(
            "Cargando...",
            size=FONT_SIZES["body"],
            color=ft.Colors.ON_SURFACE,
            weight=ft.FontWeight.W_500
        )
        self._sub_message = ft.Text(
            "",
            size=FONT_SIZES["small"],
            color=ft.Colors.ON_SURFACE_VARIANT,
        )
        self._progress = ft.ProgressRing(
            width=48,
            height=48,
            stroke_width=4,
            color=ft.Colors.PRIMARY
        )
        self._overlay = self._build_overlay()
    
    def _build_overlay(self) -> ft.Container:
        """
        Construye el contenedor del overlay.
        
        Returns:
            ft.Container: Contenedor configurado con el overlay.
        """
        return ft.Container(
            content=ft.Container(
                content=ft.Column(
                    controls=[
                        self._progress,
                        ft.Container(height=SPACING["md"]),
                        self._message,
                        self._sub_message,
                    ],
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    alignment=ft.MainAxisAlignment.CENTER,
                    spacing=SPACING["xs"],
                ),
                padding=SPACING["xl"],
                bgcolor=ft.Colors.SURFACE,
                border_radius=16,
                shadow=ft.BoxShadow(
                    blur_radius=24,
                    spread_radius=0,
                    color=ft.Colors.with_opacity(0.2, ft.Colors.BLACK),
                    offset=ft.Offset(0, 4)
                ),
            ),
            alignment=ft.alignment.center,
            bgcolor=ft.Colors.with_opacity(0.5, ft.Colors.BLACK),
            expand=True,
            visible=False,
        )
    
    def show(
        self, 
        message: str = "Cargando...", 
        sub_message: str = "",
        determinate: bool = False,
        value: float = 0
    ) -> None:
        """
        Muestra el overlay de carga.
        
        Args:
            message: Mensaje principal a mostrar.
            sub_message: Mensaje secundario opcional (útil para detalles).
            determinate: Si True, muestra progreso determinado.
            value: Valor del progreso (0.0 a 1.0) si determinate=True.
        """
        self._message.value = message
        self._sub_message.value = sub_message
        self._sub_message.visible = bool(sub_message)
        
        if determinate:
            self._progress.value = value
        else:
            self._progress.value = None  # Indeterminado
        
        self._overlay.visible = True
        self._is_visible = True
        
        if self._overlay not in self.page.overlay:
            self.page.overlay.append(self._overlay)
        
        self.page.update()
    
    def update_progress(self, value: float, message: Optional[str] = None, sub_message: Optional[str] = None) -> None:
        """
        Actualiza el progreso del overlay.
        
        Args:
            value: Nuevo valor de progreso (0.0 a 1.0).
            message: Nuevo mensaje principal (opcional).
            sub_message: Nuevo mensaje secundario (opcional).
        """
        self._progress.value = value
        if message:
            self._message.value = message
        if sub_message is not None:
            self._sub_message.value = sub_message
            self._sub_message.visible = bool(sub_message)
        self.page.update()
    
    def hide(self) -> None:
        """Oculta el overlay de carga."""
        self._overlay.visible = False
        self._is_visible = False
        self.page.update()
    
    @property
    def is_visible(self) -> bool:
        """Retorna el estado de visibilidad del overlay."""
        return self._is_visible
    
    @contextmanager
    def context(self, message: str = "Cargando...", sub_message: str = ""):
        """Context manager para mostrar/ocultar loading automáticamente."""
        try:
            self.show(message, sub_message)
            yield
        finally:
            self.hide()


class LoadingButton(ft.ElevatedButton):
    """
    Botón con estado de carga integrado.
    
    Extiende ElevatedButton para agregar funcionalidad de loading
    con spinner y deshabilitación automática durante la carga.
    
    Attributes:
        _original_content: Contenido original del botón.
        _loading_content: Contenido durante la carga.
        _is_loading: Estado de carga actual.
        _on_click: Callback original del click.
    
    Example:
        ```python
        btn = LoadingButton(
            text="Guardar",
            on_click=lambda e: save_data()
        )
        # Durante operación:
        btn.set_loading(True, "Guardando...")
        ```
    """
    
    def __init__(
        self,
        text: str,
        icon: Optional[str] = None,
        on_click: Optional[Callable] = None,
        loading_text: str = "Cargando...",
        **kwargs
    ):
        """
        Inicializa el botón con carga.
        
        Args:
            text: Texto del botón.
            icon: Icono opcional del botón.
            on_click: Callback para el evento click.
            loading_text: Texto a mostrar durante la carga.
            **kwargs: Argumentos adicionales para ElevatedButton.
        """
        self._original_text = text
        self._original_icon = icon
        self._loading_text = loading_text
        self._is_loading = False
        self._on_click_callback = on_click
        
        # Construir contenido inicial
        if icon:
            content = ft.Row(
                controls=[
                    ft.Icon(icon, size=18),
                    ft.Text(text, size=FONT_SIZES["button"]),
                ],
                spacing=SPACING["sm"],
                alignment=ft.MainAxisAlignment.CENTER,
            )
        else:
            content = ft.Text(text, size=FONT_SIZES["button"])
        
        super().__init__(
            content=content,
            on_click=self._handle_click,
            **kwargs
        )
    
    def _handle_click(self, e):
        """Maneja el click con protección de doble-click."""
        if self._is_loading:
            return
        if self._on_click_callback:
            self._on_click_callback(e)
    
    def set_loading(self, loading: bool, text: Optional[str] = None) -> None:
        """
        Establece el estado de carga del botón.
        
        Args:
            loading: True para mostrar estado de carga.
            text: Texto opcional durante la carga.
        """
        self._is_loading = loading
        
        if loading:
            self.content = ft.Row(
                controls=[
                    ft.ProgressRing(width=16, height=16, stroke_width=2, color=ft.Colors.SURFACE),
                    ft.Text(text or self._loading_text, size=FONT_SIZES["button"]),
                ],
                spacing=SPACING["sm"],
                alignment=ft.MainAxisAlignment.CENTER,
            )
            self.disabled = True
        else:
            if self._original_icon:
                self.content = ft.Row(
                    controls=[
                        ft.Icon(self._original_icon, size=18),
                        ft.Text(self._original_text, size=FONT_SIZES["button"]),
                    ],
                    spacing=SPACING["sm"],
                    alignment=ft.MainAxisAlignment.CENTER,
                )
            else:
                self.content = ft.Text(self._original_text, size=FONT_SIZES["button"])
            self.disabled = False
        
        self.update()


class ToastNotification:
    """
    Sistema de notificaciones toast no-bloqueantes.
    
    Muestra notificaciones temporales en la esquina de la pantalla
    que no interrumpen el flujo del usuario.
    
    Attributes:
        page (ft.Page): Página donde se muestran las notificaciones.
        _snack_bar (ft.SnackBar): SnackBar de Flet para mostrar toasts.
    
    Example:
        ```python
        toast = ToastNotification(page)
        toast.success("Archivo guardado correctamente")
        toast.error("Error al procesar")
        toast.info("Procesando 50 archivos...")
        ```
    """
    
    def __init__(self, page: ft.Page):
        """
        Inicializa el sistema de notificaciones.
        
        Args:
            page: Instancia de ft.Page donde se mostrarán los toasts.
        """
        self.page = page
        self._snack_bar = None
    
    def _show(
        self, 
        message: str, 
        icon: str,
        bgcolor: str,
        duration: int = 3000
    ) -> None:
        """
        Muestra una notificación toast.
        
        Args:
            message: Mensaje a mostrar.
            icon: Nombre del icono.
            bgcolor: Color de fondo.
            duration: Duración en milisegundos.
        """
        self._snack_bar = ft.SnackBar(
            content=ft.Row(
                controls=[
                    ft.Icon(icon, color=ft.Colors.SURFACE, size=20),
                    ft.Text(message, color=ft.Colors.SURFACE, size=14),
                ],
                spacing=SPACING["sm"],
            ),
            bgcolor=bgcolor,
            duration=duration,
            behavior=ft.SnackBarBehavior.FLOATING,
            shape=ft.RoundedRectangleBorder(radius=8),
            margin=SPACING["md"],
        )
        self.page.overlay.append(self._snack_bar)
        self._snack_bar.open = True
        self.page.update()
    
    def success(self, message: str, duration: int = 3000) -> None:
        """
        Muestra una notificación de éxito.
        
        Args:
            message: Mensaje a mostrar.
            duration: Duración en milisegundos (default: 3000).
        """
        self._show(message, ft.Icons.CHECK_CIRCLE, ft.Colors.GREEN, duration)
    
    def error(self, message: str, duration: int = 4000) -> None:
        """
        Muestra una notificación de error.
        
        Args:
            message: Mensaje a mostrar.
            duration: Duración en milisegundos (default: 4000).
        """
        self._show(message, ft.Icons.ERROR, ft.Colors.RED, duration)
    
    def warning(self, message: str, duration: int = 3500) -> None:
        """
        Muestra una notificación de advertencia.
        
        Args:
            message: Mensaje a mostrar.
            duration: Duración en milisegundos (default: 3500).
        """
        self._show(message, ft.Icons.WARNING, ft.Colors.ORANGE, duration)
    
    def info(self, message: str, duration: int = 3000) -> None:
        """
        Muestra una notificación informativa.
        
        Args:
            message: Mensaje a mostrar.
            duration: Duración en milisegundos (default: 3000).
        """
        self._show(message, ft.Icons.INFO, ft.Colors.PRIMARY, duration)


class ProgressIndicator(ft.Container):
    """
    Indicador de progreso visual con porcentaje y etapa.
    
    Muestra una barra de progreso con información detallada
    sobre la operación actual, útil para procesos largos.
    
    Attributes:
        _progress_bar: Barra de progreso visual.
        _percentage_text: Texto con el porcentaje.
        _stage_text: Texto con la etapa actual.
        _detail_text: Texto con detalles adicionales.
    
    Example:
        ```python
        progress = ProgressIndicator()
        progress.update(0.5, "Procesando", "Archivo 50 de 100")
        ```
    """
    
    def __init__(self):
        """Inicializa el indicador de progreso."""
        self._progress_bar = ft.ProgressBar(
            value=0,
            width=400,
            height=8,
            color=ft.Colors.PRIMARY,
            bgcolor=ft.Colors.SURFACE_CONTAINER_HIGHEST,
            border_radius=4,
        )
        self._percentage_text = ft.Text(
            "0%",
            size=FONT_SIZES["heading"],
            weight=ft.FontWeight.BOLD,
            color=ft.Colors.PRIMARY,
        )
        self._stage_text = ft.Text(
            "Preparando...",
            size=FONT_SIZES["body"],
            color=ft.Colors.ON_SURFACE,
            weight=ft.FontWeight.W_500,
        )
        self._detail_text = ft.Text(
            "",
            size=FONT_SIZES["small"],
            color=ft.Colors.ON_SURFACE_VARIANT,
        )
        
        super().__init__(
            content=ft.Column(
                controls=[
                    self._percentage_text,
                    ft.Container(height=SPACING["xs"]),
                    self._stage_text,
                    self._detail_text,
                    ft.Container(height=SPACING["sm"]),
                    self._progress_bar,
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=SPACING["xs"],
            ),
            padding=SPACING["lg"],
            bgcolor=ft.Colors.SURFACE,
            border_radius=12,
            border=ft.border.all(1, ft.Colors.OUTLINE_VARIANT),
        )
    
    def update_progress(
        self, 
        value: float, 
        stage: Optional[str] = None, 
        detail: Optional[str] = None
    ) -> None:
        """
        Actualiza el progreso mostrado.
        
        Args:
            value: Valor del progreso (0.0 a 1.0).
            stage: Texto de la etapa actual (opcional).
            detail: Texto con detalles adicionales (opcional).
        """
        self._progress_bar.value = value
        self._percentage_text.value = f"{int(value * 100)}%"
        
        if stage:
            self._stage_text.value = stage
        if detail is not None:
            self._detail_text.value = detail
            self._detail_text.visible = bool(detail)
        
        self.update()
    
    def reset(self) -> None:
        """Resetea el indicador de progreso."""
        self.update_progress(0, "Iniciando...", "")
