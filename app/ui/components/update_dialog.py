"""
Componente de diálogo de actualización para Glosaap

Este módulo proporciona un diálogo de actualización integrado
con el sistema de UI de Flet existente.
Con soporte de temas claro/oscuro
"""
import flet as ft
import json
import os
import threading
import time
from functools import partial
from pathlib import Path
from typing import Optional, Callable

from app.ui.styles import FONT_SIZES
from app.service.update_service import (
    UpdateService,
    ReleaseInfo,
    UpdateError,
    UpdateCheckError,
    UpdateDownloadError
)
from app.config.settings import logger


# ==================== ESTADO PERSISTENTE (Fase 3) ====================

# Posponer aviso 24h ("Recordarme mañana")
REMIND_DELAY_SECONDS = 24 * 3600

UPDATE_STATE_DIRNAME = "Glosaap"
UPDATE_STATE_FILENAME = "update_state.json"


def get_update_state_path() -> Path:
    """Ruta de %APPDATA%/Glosaap/update_state.json (con fallback a ~)."""
    try:
        base = os.environ.get("APPDATA") or os.path.expanduser("~")
        return Path(base) / UPDATE_STATE_DIRNAME / UPDATE_STATE_FILENAME
    except Exception:
        return Path(os.path.expanduser("~")) / UPDATE_STATE_DIRNAME / UPDATE_STATE_FILENAME


def load_update_state() -> dict:
    """Lee el state file; retorna defaults si no existe o está corrupto.

    Formato: {"skip_versions": [...], "last_check": <epoch>, "remind_at": <epoch>}
    """
    defaults = {"skip_versions": [], "last_check": 0, "remind_at": 0}
    try:
        path = get_update_state_path()
        if not path.exists():
            return {"skip_versions": [], "last_check": 0, "remind_at": 0}
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            return {"skip_versions": [], "last_check": 0, "remind_at": 0}
        skip = data.get("skip_versions", [])
        if not isinstance(skip, list):
            skip = []
        clean_skip = []
        for v in skip:
            if isinstance(v, str) and v:
                clean_skip.append(v)
            elif isinstance(v, (int, float)):
                clean_skip.append(str(v))
        try:
            last_check = float(data.get("last_check", 0) or 0)
        except (TypeError, ValueError):
            last_check = 0
        try:
            remind_at = float(data.get("remind_at", 0) or 0)
        except (TypeError, ValueError):
            remind_at = 0
        return {"skip_versions": clean_skip, "last_check": last_check, "remind_at": remind_at}
    except Exception as ex:
        try:
            logger.warning("No se pudo leer update_state: %s", ex)
        except Exception:
            pass
        return {"skip_versions": [], "last_check": 0, "remind_at": 0}


def save_update_state(state: dict) -> None:
    """Guarda el state file con escritura atómica tmp+replace (no lanza)."""
    try:
        path = get_update_state_path()
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
        except Exception:
            pass
        skip = state.get("skip_versions", []) if isinstance(state, dict) else []
        if not isinstance(skip, list):
            skip = []
        clean_skip = []
        for v in skip:
            if isinstance(v, str) and v and v not in clean_skip:
                clean_skip.append(v)
            elif isinstance(v, (int, float)):
                sv = str(v)
                if sv not in clean_skip:
                    clean_skip.append(sv)
        try:
            last_check = float(state.get("last_check", 0) or 0) if isinstance(state, dict) else 0
        except (TypeError, ValueError):
            last_check = 0
        try:
            remind_at = float(state.get("remind_at", 0) or 0) if isinstance(state, dict) else 0
        except (TypeError, ValueError):
            remind_at = 0
        payload = {"skip_versions": clean_skip, "last_check": last_check, "remind_at": remind_at}
        tmp_path = path.with_name(path.name + ".tmp")
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        os.replace(str(tmp_path), str(path))
    except Exception as ex:
        try:
            logger.warning("No se pudo guardar update_state: %s", ex)
        except Exception:
            pass


def is_version_skipped(version: str, state: Optional[dict] = None) -> bool:
    """True si la versión está en skip_versions (solo silencia esa versión)."""
    try:
        st = state if isinstance(state, dict) else load_update_state()
        skip = st.get("skip_versions", [])
        return str(version) in [str(v) for v in skip] if isinstance(skip, list) else False
    except Exception:
        return False


def is_remind_active(state: Optional[dict] = None, now: Optional[float] = None) -> bool:
    """True si aún estamos dentro del periodo pospuesto (now < remind_at)."""
    try:
        st = state if isinstance(state, dict) else load_update_state()
        ts = now if now is not None else time.time()
        remind_at = float(st.get("remind_at", 0) or 0)
        return ts < remind_at
    except Exception:
        return False


def mark_check_now() -> dict:
    """Actualiza last_check=ahora preservando skip_versions/remind_at. Retorna state."""
    try:
        state = load_update_state()
    except Exception:
        state = {"skip_versions": [], "last_check": 0, "remind_at": 0}
    state["last_check"] = time.time()
    save_update_state(state)
    return state


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
        self._skip_btn: Optional[ft.TextButton] = None
        self._remind_btn: Optional[ft.TextButton] = None
        
        if auto_check:
            self.check_for_updates_async()

    def _run_on_ui(self, fn: Callable, *args, **kwargs):
        """Programa fn en el hilo principal de Flet (no page.update desde threads).

        Usa page.loop.call_soon_threadsafe cuando hay un loop real; en tests
        (page mockeada) ejecuta directo como fallback.
        """
        try:
            loop = getattr(self.page, "loop", None)
            page_type = type(self.page).__name__
            loop_type = type(loop).__name__ if loop is not None else ""
            mock_names = ("MagicMock", "Mock", "NonCallableMock", "NonCallableMagicMock", "FakePage")
            is_mock = page_type in mock_names or loop_type in mock_names
            if loop is not None and not is_mock and hasattr(loop, "call_soon_threadsafe"):
                try:
                    cb = partial(fn, *args, **kwargs)
                    loop.call_soon_threadsafe(cb)
                    return
                except Exception:
                    pass
        except Exception:
            pass
        try:
            fn(*args, **kwargs)
        except Exception as ex:
            try:
                logger.warning("Error en callback UI de actualización: %s", ex)
            except Exception:
                pass
    
    def check_for_updates_async(self, silent: bool = True):
        """
        Verifica actualizaciones en segundo plano.
        
        Args:
            silent: Si es True, no muestra diálogo si no hay actualización.
                En modo silent se respetan skip_versions y remind_at;
                en modo manual (silent=False) se muestra aunque esté omitida/pospuesta.
        """
        def worker():
            try:
                release = self.update_service.check_for_updates()
                # Persistir last_check en el mismo state file (intervalo real)
                try:
                    mark_check_now()
                except Exception:
                    pass
                if release:
                    if silent:
                        try:
                            state = load_update_state()
                            if is_version_skipped(release.version, state):
                                logger.info(f"Actualización {release.version} omitida por el usuario")
                                return
                            if is_remind_active(state):
                                logger.info("Aviso de actualización pospuesto (recordarme mañana)")
                                return
                        except Exception:
                            pass
                    logger.info(f"Actualización disponible: {release.version}")
                    self._release_info = release
                    self._run_on_ui(self._show_update_available, release)
                elif not silent:
                    self._run_on_ui(self._show_no_updates)
            except UpdateCheckError as e:
                logger.warning(f"Error verificando actualizaciones: {e}")
                # Actualizar last_check también en error para no reintentar en bucle
                try:
                    if silent:
                        mark_check_now()
                except Exception:
                    pass
                if not silent:
                    self._run_on_ui(self._show_error, str(e))
            except Exception as e:
                logger.error(f"Error inesperado verificando actualizaciones: {e}")
                if not silent:
                    self._run_on_ui(self._show_error, "Error inesperado al verificar actualizaciones")
        
        threading.Thread(target=worker, daemon=True).start()
    
    def check_and_show(self):
        """Verifica actualizaciones y muestra resultado (no silencioso)"""
        self.show_checking()
        self.check_for_updates_async(silent=False)
    
    def show_checking(self):
        """Muestra diálogo indicando que se está verificando"""
        self._close_dialog()
        
        content = ft.Column([
            ft.ProgressRing(width=40, height=40, color=ft.Colors.PRIMARY),
            ft.Container(height=16),
            ft.Text(
                "Verificando actualizaciones...",
                size=14,
                color=ft.Colors.ON_SURFACE_VARIANT,
                text_align=ft.TextAlign.CENTER
            ),
            ft.Text(
                f"Versión actual: {self.current_version}",
                size=12,
                color=ft.Colors.ON_SURFACE_VARIANT,
                text_align=ft.TextAlign.CENTER
            )
        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=8)
        
        self._dialog = ft.AlertDialog(
            modal=True,
            title=ft.Row([
                ft.Icon(ft.Icons.SYSTEM_UPDATE, color=ft.Colors.PRIMARY, size=28),
                ft.Text("Actualización", size=18, weight=ft.FontWeight.BOLD, color=ft.Colors.ON_SURFACE)
            ], spacing=10),
            content=ft.Container(content=content, width=300, height=120),
            shape=ft.RoundedRectangleBorder(radius=12),
            bgcolor=ft.Colors.SURFACE
        )
        
        self.page.overlay.append(self._dialog)
        self._dialog.open = True
        self.page.update()

    def _on_skip_version(self, e, release: ReleaseInfo):
        """Omite SOLO esta versión (persiste en skip_versions)."""
        try:
            state = load_update_state()
            skip = state.get("skip_versions", [])
            if not isinstance(skip, list):
                skip = []
            ver = str(release.version)
            if ver not in skip:
                skip.append(ver)
            state["skip_versions"] = skip
            save_update_state(state)
            logger.info(f"Versión {ver} omitida por el usuario")
        except Exception as ex:
            try:
                logger.warning("No se pudo guardar skip_version: %s", ex)
            except Exception:
                pass
        self._close_dialog()

    def _on_remind_tomorrow(self, e):
        """Pospone el aviso 24h (persiste remind_at)."""
        try:
            state = load_update_state()
            state["remind_at"] = time.time() + REMIND_DELAY_SECONDS
            save_update_state(state)
            logger.info("Aviso de actualización pospuesto 24h")
        except Exception as ex:
            try:
                logger.warning("No se pudo guardar remind_at: %s", ex)
            except Exception:
                pass
        self._close_dialog()
    
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
            color=ft.Colors.PRIMARY,
            bgcolor=ft.Colors.SURFACE_CONTAINER_HIGHEST,
            visible=False
        )
        
        self._progress_text = ft.Text(
            "",
            size=12,
            color=ft.Colors.ON_SURFACE_VARIANT,
            visible=False,
            text_align=ft.TextAlign.CENTER
        )

        # Botones Fase 3: omitir solo esta versión / posponer 24h (ft.Colors.*, sin hex)
        self._skip_btn = ft.TextButton(
            "Omitir esta versión",
            on_click=lambda e: self._on_skip_version(e, release),
            style=ft.ButtonStyle(color=ft.Colors.ON_SURFACE_VARIANT)
        )
        self._remind_btn = ft.TextButton(
            "Recordarme mañana",
            on_click=lambda e: self._on_remind_tomorrow(e),
            style=ft.ButtonStyle(color=ft.Colors.ON_SURFACE_VARIANT)
        )
        
        # Contenido del diálogo
        content = ft.Column([
            # Información de versión
            ft.Container(
                content=ft.Column([
                    ft.Row([
                        ft.Text("Nueva versión:", size=13, color=ft.Colors.ON_SURFACE_VARIANT),
                        ft.Text(
                            f"v{release.version}",
                            size=13,
                            weight=ft.FontWeight.BOLD,
                            color=ft.Colors.GREEN
                        )
                    ], spacing=8),
                    ft.Row([
                        ft.Text("Versión actual:", size=13, color=ft.Colors.ON_SURFACE_VARIANT),
                        ft.Text(
                            f"v{self.current_version}",
                            size=13,
                            color=ft.Colors.ON_SURFACE_VARIANT
                        )
                    ], spacing=8),
                    ft.Row([
                        ft.Text("Tamaño:", size=13, color=ft.Colors.ON_SURFACE_VARIANT),
                        ft.Text(
                            f"{release.size_mb:.1f} MB",
                            size=13,
                            color=ft.Colors.ON_SURFACE_VARIANT
                        )
                    ], spacing=8),
                ], spacing=6),
                padding=12,
                bgcolor=ft.Colors.SURFACE_CONTAINER_HIGHEST,
                border_radius=8
            ),
            
            ft.Container(height=8),
            
            # Changelog
            ft.Text(
                "Novedades:",
                size=14,
                weight=ft.FontWeight.W_500,
                color=ft.Colors.ON_SURFACE
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
                bgcolor=ft.Colors.SURFACE_CONTAINER_HIGHEST,
                border_radius=8,
                border=ft.border.all(1, ft.Colors.OUTLINE_VARIANT)
            ),

            ft.Container(height=4),

            # Fase 3: acciones secundarias dentro del contenido (evita overflow de actions)
            ft.Row(
                [self._skip_btn, self._remind_btn],
                alignment=ft.MainAxisAlignment.CENTER,
                spacing=4,
            ),
            
            ft.Container(height=4),
            
            # Progreso de descarga
            self._progress_bar,
            self._progress_text,
            
        ], spacing=8, horizontal_alignment=ft.CrossAxisAlignment.CENTER)
        
        # Botones
        self._download_btn = ft.ElevatedButton(
            "⬇️ Actualizar ahora",
            on_click=lambda e: self._start_download(release),
            bgcolor=ft.Colors.PRIMARY,
            color=ft.Colors.SURFACE,
            style=ft.ButtonStyle(
                shape=ft.RoundedRectangleBorder(radius=8),
                padding=ft.padding.symmetric(horizontal=20, vertical=12)
            )
        )
        
        self._cancel_btn = ft.TextButton(
            "Más tarde",
            on_click=lambda e: self._close_dialog(),
            style=ft.ButtonStyle(color=ft.Colors.ON_SURFACE_VARIANT)
        )
        
        self._dialog = ft.AlertDialog(
            modal=True,
            title=ft.Row([
                ft.Icon(ft.Icons.ROCKET_LAUNCH, color=ft.Colors.GREEN, size=28),
                ft.Text(
                    "¡Actualización disponible!",
                    size=18,
                    weight=ft.FontWeight.BOLD,
                    color=ft.Colors.ON_SURFACE
                )
            ], spacing=10),
            content=ft.Container(content=content, width=380),
            actions=[self._cancel_btn, self._download_btn],
            actions_alignment=ft.MainAxisAlignment.END,
            shape=ft.RoundedRectangleBorder(radius=12),
            bgcolor=ft.Colors.SURFACE
        )
        
        self.page.overlay.append(self._dialog)
        self._dialog.open = True
        self.page.update()
    
    def _show_no_updates(self):
        """Muestra diálogo indicando que no hay actualizaciones"""
        self._close_dialog()
        
        content = ft.Column([
            ft.Icon(ft.Icons.CHECK_CIRCLE, color=ft.Colors.GREEN, size=48),
            ft.Container(height=12),
            ft.Text(
                "Estás al día",
                size=16,
                weight=ft.FontWeight.W_500,
                color=ft.Colors.ON_SURFACE,
                text_align=ft.TextAlign.CENTER
            ),
            ft.Text(
                f"Versión actual: {self.current_version}",
                size=13,
                color=ft.Colors.ON_SURFACE_VARIANT,
                text_align=ft.TextAlign.CENTER
            )
        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=4)
        
        self._dialog = ft.AlertDialog(
            modal=True,
            title=ft.Row([
                ft.Icon(ft.Icons.SYSTEM_UPDATE, color=ft.Colors.PRIMARY, size=28),
                ft.Text("Actualización", size=18, weight=ft.FontWeight.BOLD, color=ft.Colors.ON_SURFACE)
            ], spacing=10),
            content=ft.Container(content=content, width=280, height=140),
            actions=[
                ft.TextButton(
                    "Cerrar",
                    on_click=lambda e: self._close_dialog(),
                    style=ft.ButtonStyle(color=ft.Colors.PRIMARY)
                )
            ],
            actions_alignment=ft.MainAxisAlignment.END,
            shape=ft.RoundedRectangleBorder(radius=12),
            bgcolor=ft.Colors.SURFACE
        )
        
        self.page.overlay.append(self._dialog)
        self._dialog.open = True
        self.page.update()
    
    def _show_error(self, message: str):
        """Muestra diálogo de error"""
        self._close_dialog()
        
        content = ft.Column([
            ft.Icon(ft.Icons.ERROR_OUTLINE, color=ft.Colors.RED, size=48),
            ft.Container(height=12),
            ft.Text(
                message,
                size=14,
                color=ft.Colors.ON_SURFACE_VARIANT,
                text_align=ft.TextAlign.CENTER
            )
        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=4)
        
        self._dialog = ft.AlertDialog(
            modal=True,
            title=ft.Row([
                ft.Icon(ft.Icons.SYSTEM_UPDATE, color=ft.Colors.RED, size=28),
                ft.Text("Error", size=18, weight=ft.FontWeight.BOLD, color=ft.Colors.ON_SURFACE)
            ], spacing=10),
            content=ft.Container(content=content, width=300, height=120),
            actions=[
                ft.TextButton(
                    "Cerrar",
                    on_click=lambda e: self._close_dialog(),
                    style=ft.ButtonStyle(color=ft.Colors.RED)
                )
            ],
            actions_alignment=ft.MainAxisAlignment.END,
            shape=ft.RoundedRectangleBorder(radius=12),
            bgcolor=ft.Colors.SURFACE
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
        
        # Actualizar UI en hilo principal (este método se llama desde click: hilo principal OK)
        self._download_btn.disabled = True  # type: ignore
        self._download_btn.text = "Descargando..."  # type: ignore
        self._cancel_btn.disabled = True  # type: ignore
        if self._skip_btn is not None:
            self._skip_btn.disabled = True
        if self._remind_btn is not None:
            self._remind_btn.disabled = True
        self._progress_bar.visible = True  # type: ignore
        self._progress_bar.value = 0  # type: ignore
        self._progress_text.visible = True  # type: ignore
        self._progress_text.value = "Iniciando descarga..."  # type: ignore
        self.page.update()

        def _apply_progress(downloaded: int, total: int):
            """Aplica progreso en hilo principal."""
            try:
                if total > 0 and self._progress_bar and self._progress_text:
                    progress = downloaded / total
                    self._progress_bar.value = progress
                    mb_downloaded = downloaded / (1024 * 1024)
                    mb_total = total / (1024 * 1024)
                    self._progress_text.value = f"{mb_downloaded:.1f} MB / {mb_total:.1f} MB ({progress*100:.0f}%)"
                    self.page.update()
            except Exception:
                pass

        def _set_text(message: str):
            """Actualiza texto de progreso en hilo principal."""
            try:
                if self._progress_text:
                    self._progress_text.value = message
                    self.page.update()
            except Exception:
                pass

        def _on_complete_ui():
            """Marca descarga completada en hilo principal."""
            try:
                if self._progress_bar and self._progress_text and self._download_btn:
                    self._progress_bar.value = 1.0
                    self._progress_text.value = "Descarga completada. Preparando instalación..."
                    self._download_btn.text = "Instalando..."
                    self.page.update()
            except Exception:
                pass

        def _on_closing_ui():
            """Avisa cierre para actualizar en hilo principal."""
            try:
                if self._progress_text:
                    self._progress_text.value = "Cerrando aplicación para actualizar..."
                    self.page.update()
            except Exception:
                pass
        
        def on_progress(downloaded: int, total: int):
            """Callback de progreso de descarga (viene del worker: reenvía al hilo principal)."""
            self._run_on_ui(_apply_progress, downloaded, total)
        
        def worker():
            try:
                # Descargar (aviso en hilo principal vía callback)
                self._run_on_ui(_set_text, "Descargando actualización...")
                
                downloaded_file = self.update_service.download_update(release, on_progress)
                
                # Descarga completada (hilo principal)
                self._run_on_ui(_on_complete_ui)
                
                # Lanzar updater (I/O, puede ir en worker)
                logger.info("Lanzando actualizador...")
                self.update_service.launch_updater(downloaded_file)
                
                # Notificar que se va a cerrar la app (hilo principal)
                self._run_on_ui(_on_closing_ui)
                
                if self.on_update_complete:
                    try:
                        self._run_on_ui(self.on_update_complete)
                    except Exception:
                        pass
                
                # Cerrar la aplicación después de un breve delay
                time.sleep(1)
                self._run_on_ui(self.page.window.close)
                
            except UpdateDownloadError as e:
                logger.error(f"Error descargando actualización: {e}")
                self._run_on_ui(self._show_download_error, str(e))
            except Exception as e:
                logger.error(f"Error en actualización: {e}")
                self._run_on_ui(self._show_download_error, f"Error inesperado: {str(e)}")
            finally:
                self._is_downloading = False
        
        threading.Thread(target=worker, daemon=True).start()
    
    def _show_download_error(self, message: str):
        """Muestra error durante la descarga (llamar desde hilo principal)."""
        if self._progress_bar:
            self._progress_bar.visible = False
        if self._progress_text:
            self._progress_text.value = f"❌ {message}"
            self._progress_text.color = ft.Colors.RED
        if self._download_btn:
            self._download_btn.disabled = False
            self._download_btn.text = "⬇️ Reintentar"
        if self._cancel_btn:
            self._cancel_btn.disabled = False
        if self._skip_btn is not None:
            self._skip_btn.disabled = False
        if self._remind_btn is not None:
            self._remind_btn.disabled = False
        self.page.update()
    
    def _close_dialog(self):
        """Cierra el diálogo actual (solo el propio; no toca otros overlays)."""
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
    actualización a cualquier vista. Respeta intervalo + skip/remind
    persistidos en %APPDATA%/Glosaap/update_state.json.
    """
    
    def __init__(
        self,
        page: ft.Page,
        current_version: str,
        github_repo: str = "tu-organizacion/glosaap",
        check_interval_hours: float = 24
    ):
        self.page = page
        self.current_version = current_version
        self.github_repo = github_repo
        try:
            interval = float(check_interval_hours)
        except (TypeError, ValueError):
            interval = 24
        if interval <= 0:
            interval = 24
        self.check_interval_hours = interval
        self._update_dialog: Optional[UpdateDialog] = None
    
    def create_menu_item(self) -> ft.PopupMenuItem:
        """Crea un item de menú para verificar actualizaciones"""
        return ft.PopupMenuItem(
            content=ft.Row([
                ft.Icon(ft.Icons.SYSTEM_UPDATE, size=18, color=ft.Colors.ON_SURFACE_VARIANT),
                ft.Text("Buscar actualizaciones", size=13)
            ], spacing=8),
            on_click=lambda e: self.check_updates()
        )
    
    def create_button(self, compact: bool = False) -> ft.Control:
        """Crea un botón para verificar actualizaciones"""
        if compact:
            return ft.IconButton(
                icon=ft.Icons.SYSTEM_UPDATE,
                icon_color=ft.Colors.ON_SURFACE_VARIANT,
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
        """Abre el diálogo de verificación de actualizaciones (manual: ignora intervalo/skip/remind)."""
        self._update_dialog = UpdateDialog(
            page=self.page,
            current_version=self.current_version,
            github_repo=self.github_repo,
            auto_check=False
        )
        self._update_dialog.check_and_show()
    
    def check_updates_silent(self):
        """Verifica actualizaciones silenciosamente (muestra solo si hay actualización).

        Respeta skip_versions y remind_at (no muestra si aplica); el worker
        persiste last_check en el mismo state file.
        """
        self._update_dialog = UpdateDialog(
            page=self.page,
            current_version=self.current_version,
            github_repo=self.github_repo,
            auto_check=True
        )

    def is_due(self, now: Optional[float] = None) -> bool:
        """True si toca verificar: pasó el intervalo y no hay remind activo."""
        try:
            ts = now if now is not None else time.time()
            state = load_update_state()
            try:
                last = float(state.get("last_check", 0) or 0)
            except (TypeError, ValueError):
                last = 0
            if is_remind_active(state, ts):
                return False
            return (ts - last) >= (self.check_interval_hours * 3600)
        except Exception:
            return False

    def maybe_check(self) -> bool:
        """Verifica si toca (intervalo + remind) y dispara check silencioso.

        Pensado para arranque y para llamadas periódicas en sesiones largas
        (p. ej. al volver al dashboard). No bloquea: el chequeo de red va en
        worker y la UI se programa en el hilo principal. Retorna True si
        disparó verificación, False si aún no toca.
        """
        try:
            if not self.is_due():
                return False
            # Toque optimista para no disparar N workers si se llama seguido
            # antes de que el worker persista su propio last_check.
            try:
                state = load_update_state()
                state["last_check"] = time.time()
                save_update_state(state)
            except Exception:
                pass
            self.check_updates_silent()
            return True
        except Exception as ex:
            try:
                logger.warning("maybe_check falló: %s", ex)
            except Exception:
                pass
            return False
