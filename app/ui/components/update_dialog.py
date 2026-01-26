"""
Componente de diálogo de actualización para Glosaap

Este módulo proporciona un diálogo de actualización integrado
con el sistema de UI de Flet existente.
"""
import flet as ft
import threading
from typing import Optional, Callable

from app.ui.styles import COLORS, FONT_SIZES
from app.service.update_service import (
    UpdateService,
    ReleaseInfo,
    UpdateError,
    UpdateCheckError,
    UpdateDownloadError
)
from app.config.settings import logger


class UpdateDialog:
    """
    Diálogo de actualización que sigue el estilo visual de Glosaap.
    
    Uso:
        dialog = UpdateDialog(page, current_version="1.0.0")
        dialog.check_for_updates()  # Verifica en segundo plano
        # O para verificación manual:
        dialog.show_checking()
        dialog.check_and_show()
    """
    
    def __init__(
        self,
        page: ft.Page,
        current_version: str,
        github_repo: str = "Damdev80/Glosaap",
        on_update_complete: Optional[Callable] = None,
        auto_check: bool = True
    ):
        """
        Inicializa el diálogo de actualización.
        
        Args:
            page: Página de Flet
            current_version: Versión actual de la aplicación
            github_repo: Repositorio de GitHub
            on_update_complete: Callback cuando se va a iniciar la actualización
            auto_check: Si es True, verifica automáticamente al inicio
        """
        self.page = page
        self.current_version = current_version
        self.github_repo = github_repo
        self.on_update_complete = on_update_complete
        
        self.update_service = UpdateService(current_version, github_repo)
        self._dialog: Optional[ft.AlertDialog] = None
        self._release_info: Optional[ReleaseInfo] = None
        self._is_downloading = False
        
        # Componentes UI
        self._progress_bar: Optional[ft.ProgressBar] = None
        self._progress_text: Optional[ft.Text] = None
        self._download_btn: Optional[ft.ElevatedButton] = None
        self._cancel_btn: Optional[ft.TextButton] = None
        
        if auto_check:
            self.check_for_updates_async()
    
    def check_for_updates_async(self, silent: bool = True):
        """
        Verifica actualizaciones en segundo plano.
        
        Args:
            silent: Si es True, no muestra diálogo si no hay actualización
        """
        def worker():
            try:
                release = self.update_service.check_for_updates()
                if release:
                    logger.info(f"Actualización disponible: {release.version}")
                    self._release_info = release
                    self._show_update_available(release)
                elif not silent:
                    self._show_no_updates()
            except UpdateCheckError as e:
                logger.warning(f"Error verificando actualizaciones: {e}")
                if not silent:
                    self._show_error(str(e))
            except Exception as e:
                logger.error(f"Error inesperado verificando actualizaciones: {e}")
                if not silent:
                    self._show_error("Error inesperado al verificar actualizaciones")
        
        threading.Thread(target=worker, daemon=True).start()
    
    def check_and_show(self):
        """Verifica actualizaciones y muestra resultado (no silencioso)"""
        self.show_checking()
        self.check_for_updates_async(silent=False)
    
    def show_checking(self):
        """Muestra diálogo indicando que se está verificando"""
        self._close_dialog()
        
        content = ft.Column([
            ft.ProgressRing(width=40, height=40, color=COLORS["primary"]),
            ft.Container(height=16),
            ft.Text(
                "Verificando actualizaciones...",
                size=14,
                color=COLORS["text_secondary"],
                text_align=ft.TextAlign.CENTER
            ),
            ft.Text(
                f"Versión actual: {self.current_version}",
                size=12,
                color=COLORS["text_light"],
                text_align=ft.TextAlign.CENTER
            )
        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=8)
        
        self._dialog = ft.AlertDialog(
            modal=True,
            title=ft.Row([
                ft.Icon(ft.Icons.SYSTEM_UPDATE, color=COLORS["primary"], size=28),
                ft.Text("Actualización", size=18, weight=ft.FontWeight.BOLD, color=COLORS["text_primary"])
            ], spacing=10),
            content=ft.Container(content=content, width=300, height=120),
            shape=ft.RoundedRectangleBorder(radius=12),
            bgcolor=COLORS["bg_white"]
        )
        
        self.page.overlay.append(self._dialog)
        self._dialog.open = True
        self.page.update()
    
    def _show_update_available(self, release: ReleaseInfo):
        """Muestra diálogo con información de la actualización disponible"""
        self._close_dialog()
        
        # Formatear changelog (limitar longitud y parsear markdown básico)
        changelog = release.changelog
        if len(changelog) > 500:
            changelog = changelog[:500] + "..."
        
        # Barra de progreso (oculta inicialmente)
        self._progress_bar = ft.ProgressBar(
            width=350,
            value=0,
            color=COLORS["primary"],
            bgcolor=COLORS["bg_input"],
            visible=False
        )
        
        self._progress_text = ft.Text(
            "",
            size=12,
            color=COLORS["text_secondary"],
            visible=False,
            text_align=ft.TextAlign.CENTER
        )
        
        # Contenido del diálogo
        content = ft.Column([
            # Información de versión
            ft.Container(
                content=ft.Column([
                    ft.Row([
                        ft.Text("Nueva versión:", size=13, color=COLORS["text_secondary"]),
                        ft.Text(
                            f"v{release.version}",
                            size=13,
                            weight=ft.FontWeight.BOLD,
                            color=COLORS["success"]
                        )
                    ], spacing=8),
                    ft.Row([
                        ft.Text("Versión actual:", size=13, color=COLORS["text_secondary"]),
                        ft.Text(
                            f"v{self.current_version}",
                            size=13,
                            color=COLORS["text_light"]
                        )
                    ], spacing=8),
                    ft.Row([
                        ft.Text("Tamaño:", size=13, color=COLORS["text_secondary"]),
                        ft.Text(
                            f"{release.size_mb:.1f} MB",
                            size=13,
                            color=COLORS["text_light"]
                        )
                    ], spacing=8),
                ], spacing=6),
                padding=12,
                bgcolor=COLORS["bg_light"],
                border_radius=8
            ),
            
            ft.Container(height=8),
            
            # Changelog
            ft.Text(
                "Novedades:",
                size=14,
                weight=ft.FontWeight.W_500,
                color=COLORS["text_primary"]
            ),
            ft.Container(
                content=ft.Column([
                    ft.Markdown(
                        changelog,
                        selectable=True,
                        extension_set=ft.MarkdownExtensionSet.GITHUB_WEB,
                        on_tap_link=lambda e: self.page.launch_url(e.data) if e.data else None
                    )
                ], scroll=ft.ScrollMode.AUTO),
                height=150,
                width=350,
                padding=10,
                bgcolor=COLORS["bg_input"],
                border_radius=8,
                border=ft.border.all(1, COLORS["border_light"])
            ),
            
            ft.Container(height=8),
            
            # Progreso de descarga
            self._progress_bar,
            self._progress_text,
            
        ], spacing=8, horizontal_alignment=ft.CrossAxisAlignment.CENTER)
        
        # Botones
        self._download_btn = ft.ElevatedButton(
            "⬇️ Actualizar ahora",
            on_click=lambda e: self._start_download(release),
            bgcolor=COLORS["primary"],
            color=COLORS["bg_white"],
            style=ft.ButtonStyle(
                shape=ft.RoundedRectangleBorder(radius=8),
                padding=ft.padding.symmetric(horizontal=20, vertical=12)
            )
        )
        
        self._cancel_btn = ft.TextButton(
            "Más tarde",
            on_click=lambda e: self._close_dialog(),
            style=ft.ButtonStyle(color=COLORS["text_secondary"])
        )
        
        self._dialog = ft.AlertDialog(
            modal=True,
            title=ft.Row([
                ft.Icon(ft.Icons.ROCKET_LAUNCH, color=COLORS["success"], size=28),
                ft.Text(
                    "¡Actualización disponible!",
                    size=18,
                    weight=ft.FontWeight.BOLD,
                    color=COLORS["text_primary"]
                )
            ], spacing=10),
            content=ft.Container(content=content, width=380),
            actions=[self._cancel_btn, self._download_btn],
            actions_alignment=ft.MainAxisAlignment.END,
            shape=ft.RoundedRectangleBorder(radius=12),
            bgcolor=COLORS["bg_white"]
        )
        
        self.page.overlay.append(self._dialog)
        self._dialog.open = True
        self.page.update()
    
    def _show_no_updates(self):
        """Muestra diálogo indicando que no hay actualizaciones"""
        self._close_dialog()
        
        content = ft.Column([
            ft.Icon(ft.Icons.CHECK_CIRCLE, color=COLORS["success"], size=48),
            ft.Container(height=12),
            ft.Text(
                "Estás al día",
                size=16,
                weight=ft.FontWeight.W_500,
                color=COLORS["text_primary"],
                text_align=ft.TextAlign.CENTER
            ),
            ft.Text(
                f"Versión actual: {self.current_version}",
                size=13,
                color=COLORS["text_secondary"],
                text_align=ft.TextAlign.CENTER
            )
        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=4)
        
        self._dialog = ft.AlertDialog(
            modal=True,
            title=ft.Row([
                ft.Icon(ft.Icons.SYSTEM_UPDATE, color=COLORS["primary"], size=28),
                ft.Text("Actualización", size=18, weight=ft.FontWeight.BOLD, color=COLORS["text_primary"])
            ], spacing=10),
            content=ft.Container(content=content, width=280, height=140),
            actions=[
                ft.TextButton(
                    "Cerrar",
                    on_click=lambda e: self._close_dialog(),
                    style=ft.ButtonStyle(color=COLORS["primary"])
                )
            ],
            actions_alignment=ft.MainAxisAlignment.END,
            shape=ft.RoundedRectangleBorder(radius=12),
            bgcolor=COLORS["bg_white"]
        )
        
        self.page.overlay.append(self._dialog)
        self._dialog.open = True
        self.page.update()
    
    def _show_error(self, message: str):
        """Muestra diálogo de error"""
        self._close_dialog()
        
        content = ft.Column([
            ft.Icon(ft.Icons.ERROR_OUTLINE, color=COLORS["error"], size=48),
            ft.Container(height=12),
            ft.Text(
                message,
                size=14,
                color=COLORS["text_secondary"],
                text_align=ft.TextAlign.CENTER
            )
        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=4)
        
        self._dialog = ft.AlertDialog(
            modal=True,
            title=ft.Row([
                ft.Icon(ft.Icons.SYSTEM_UPDATE, color=COLORS["error"], size=28),
                ft.Text("Error", size=18, weight=ft.FontWeight.BOLD, color=COLORS["text_primary"])
            ], spacing=10),
            content=ft.Container(content=content, width=300, height=120),
            actions=[
                ft.TextButton(
                    "Cerrar",
                    on_click=lambda e: self._close_dialog(),
                    style=ft.ButtonStyle(color=COLORS["error"])
                )
            ],
            actions_alignment=ft.MainAxisAlignment.END,
            shape=ft.RoundedRectangleBorder(radius=12),
            bgcolor=COLORS["bg_white"]
        )
        
        self.page.overlay.append(self._dialog)
        self._dialog.open = True
        self.page.update()
    
    def _start_download(self, release: ReleaseInfo):
        """Inicia la descarga de la actualización"""
        if self._is_downloading:
            return
        
        # Verificar que los componentes de UI existen
        if not all([self._download_btn, self._cancel_btn, self._progress_bar, self._progress_text]):
            logger.error("Componentes de UI no inicializados")
            return
        
        self._is_downloading = True
        
        # Actualizar UI (type: ignore para silenciar warnings de Pyright)
        self._download_btn.disabled = True  # type: ignore
        self._download_btn.text = "Descargando..."  # type: ignore
        self._cancel_btn.disabled = True  # type: ignore
        self._progress_bar.visible = True  # type: ignore
        self._progress_bar.value = 0  # type: ignore
        self._progress_text.visible = True  # type: ignore
        self._progress_text.value = "Iniciando descarga..."  # type: ignore
        self.page.update()
        
        def on_progress(downloaded: int, total: int):
            """Callback de progreso de descarga"""
            if total > 0 and self._progress_bar and self._progress_text:
                progress = downloaded / total
                self._progress_bar.value = progress
                mb_downloaded = downloaded / (1024 * 1024)
                mb_total = total / (1024 * 1024)
                self._progress_text.value = f"{mb_downloaded:.1f} MB / {mb_total:.1f} MB ({progress*100:.0f}%)"
                self.page.update()
        
        def worker():
            try:
                # Descargar
                if self._progress_text:
                    self._progress_text.value = "Descargando actualización..."
                    self.page.update()
                
                downloaded_file = self.update_service.download_update(release, on_progress)
                
                # Descarga completada
                if self._progress_bar and self._progress_text and self._download_btn:
                    self._progress_bar.value = 1.0
                    self._progress_text.value = "Descarga completada. Preparando instalación..."
                    self._download_btn.text = "Instalando..."
                    self.page.update()
                
                # Lanzar updater
                logger.info("Lanzando actualizador...")
                self.update_service.launch_updater(downloaded_file)
                
                # Notificar que se va a cerrar la app
                if self._progress_text:
                    self._progress_text.value = "Cerrando aplicación para actualizar..."
                    self.page.update()
                
                if self.on_update_complete:
                    self.on_update_complete()
                
                # Cerrar la aplicación después de un breve delay
                import time
                time.sleep(1)
                self.page.window.close()
                
            except UpdateDownloadError as e:
                logger.error(f"Error descargando actualización: {e}")
                self._show_download_error(str(e))
            except Exception as e:
                logger.error(f"Error en actualización: {e}")
                self._show_download_error(f"Error inesperado: {str(e)}")
            finally:
                self._is_downloading = False
        
        threading.Thread(target=worker, daemon=True).start()
    
    def _show_download_error(self, message: str):
        """Muestra error durante la descarga"""
        if self._progress_bar:
            self._progress_bar.visible = False
        if self._progress_text:
            self._progress_text.value = f"❌ {message}"
            self._progress_text.color = COLORS["error"]
        if self._download_btn:
            self._download_btn.disabled = False
            self._download_btn.text = "⬇️ Reintentar"
        if self._cancel_btn:
            self._cancel_btn.disabled = False
        self.page.update()
    
    def _close_dialog(self):
        """Cierra el diálogo actual"""
        if self._dialog:
            try:
                self._dialog.open = False
                self.page.update()
                if self._dialog in self.page.overlay:
                    self.page.overlay.remove(self._dialog)
            except Exception:
                pass
            self._dialog = None


class UpdateChecker:
    """
    Verificador de actualizaciones que se integra en el menú de la aplicación.
    
    Proporciona un método simple para agregar la funcionalidad de
    actualización a cualquier vista.
    """
    
    def __init__(
        self,
        page: ft.Page,
        current_version: str,
        github_repo: str = "tu-organizacion/glosaap"
    ):
        self.page = page
        self.current_version = current_version
        self.github_repo = github_repo
        self._update_dialog: Optional[UpdateDialog] = None
    
    def create_menu_item(self) -> ft.PopupMenuItem:
        """Crea un item de menú para verificar actualizaciones"""
        return ft.PopupMenuItem(
            content=ft.Row([
                ft.Icon(ft.Icons.SYSTEM_UPDATE, size=18, color=COLORS["text_secondary"]),
                ft.Text("Buscar actualizaciones", size=13)
            ], spacing=8),
            on_click=lambda e: self.check_updates()
        )
    
    def create_button(self, compact: bool = False) -> ft.Control:
        """Crea un botón para verificar actualizaciones"""
        if compact:
            return ft.IconButton(
                icon=ft.Icons.SYSTEM_UPDATE,
                icon_color=COLORS["text_secondary"],
                tooltip="Buscar actualizaciones",
                on_click=lambda e: self.check_updates()
            )
        else:
            return ft.TextButton(
                content=ft.Row([
                    ft.Icon(ft.Icons.SYSTEM_UPDATE, size=16),
                    ft.Text(f"v{self.current_version}", size=12)
                ], spacing=4),
                tooltip="Buscar actualizaciones",
                on_click=lambda e: self.check_updates()
            )
    
    def check_updates(self):
        """Abre el diálogo de verificación de actualizaciones"""
        self._update_dialog = UpdateDialog(
            page=self.page,
            current_version=self.current_version,
            github_repo=self.github_repo,
            auto_check=False
        )
        self._update_dialog.check_and_show()
    
    def check_updates_silent(self):
        """Verifica actualizaciones silenciosamente (muestra solo si hay actualización)"""
        self._update_dialog = UpdateDialog(
            page=self.page,
            current_version=self.current_version,
            github_repo=self.github_repo,
            auto_check=True
        )
