"""
Aplicación Glosaap - Cliente IMAP con Flet (REFACTORIZADO)
Con soporte completo de temas claro/oscuro.

Bootstrap + inyección: crea servicios, estado (AppState) y vistas, y
delega TODA la navegación al NavigationController (canal único).
"""
import flet as ft
import os
import sys
import threading
from datetime import datetime as _dt
from typing import Optional, List

# Configurar path para imports - agregar el directorio raíz del proyecto
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# Importar settings (configura Playwright automáticamente)
from app.config.settings import PLAYWRIGHT_BROWSERS_PATH

from app.service.email_service import EmailService
from app.ui.styles import (
    WINDOW_SIZES,
    ThemeManager,
    update_colors,
    get_colors,
    get_window_size_for_view,
    resolve_window_size,
    save_window_size,
)
from app.ui.screens.eps_screen import EpsScreen
from app.ui.views import DashboardView, LoginView, ToolsView, MessagesView
from app.ui.views.homologacion_view import HomologacionView
from app.ui.views.mix_excel_view import MixExcelView
from app.ui.views.homologador_manual_view import HomologadorManualView
from app.ui.views.web_download_view import WebDownloadView
from app.ui.views.method_selection_view import MethodSelectionView
from app.ui.components.alert_dialog import AlertDialog
from app.ui.components.settings_dialog import show_settings_dialog
from app.ui.components.update_dialog import UpdateChecker
from app.ui.navigation import NavigationController
from app.ui.app_state import AppState
from app.ui.business_logic import MessageFilter
from app.config.settings import APP_VERSION, GITHUB_REPO, AUTO_UPDATE_CONFIG, logger, get_homologador_path, get_output_dir, ensure_dir

# Ruta de assets (carpeta con imágenes)
ASSETS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "assets"))


def _parse_email_date(msg_date):
    """Parsea la fecha de un correo a datetime (múltiples formatos) o None."""
    if msg_date is None:
        return None
    try:
        if isinstance(msg_date, str):
            for fmt in (
                '%a, %d %b %Y %H:%M:%S %z',
                '%a, %d %b %Y %H:%M:%S',
                '%d %b %Y %H:%M:%S %z',
                '%d %b %Y %H:%M:%S',
                '%Y-%m-%d %H:%M:%S',
                '%d/%m/%Y %H:%M:%S',
            ):
                try:
                    return _dt.strptime(msg_date.strip(), fmt)
                except ValueError:
                    continue
            return None
        if hasattr(msg_date, 'strftime'):
            return msg_date
    except Exception:
        return None
    return None


def _latest_email_date_str(messages):
    """Retorna la fecha del correo más reciente como 'YYYY-MM-DD HH:MM:SS'."""
    dates = []
    for msg in messages or []:
        parsed = _parse_email_date((msg or {}).get('date'))
        if parsed is not None:
            dates.append(parsed)
    if not dates:
        return None
    return max(dates).strftime('%Y-%m-%d %H:%M:%S')


def _open_folder_in_explorer(folder_path):
    """Abre una carpeta en el explorador (único punto; las vistas no llaman subprocess).

    Delega al servicio de SO en la capa bootstrap, no desde vistas.
    """
    if not folder_path:
        return
    try:
        if sys.platform.startswith("win"):
            try:
                os.startfile(folder_path)  # type: ignore[attr-defined]
                return
            except Exception:
                pass
        import subprocess as _sp
        _sp.Popen(f'explorer "{folder_path}"')
    except Exception as ex:
        logger.warning("No se pudo abrir carpeta %s: %s", folder_path, ex)


def _open_file_default(file_path):
    """Abre un archivo con la app por defecto (único punto; las vistas no llaman subprocess).

    Usado por el botón "Ver no homologados" del resumen post-procesado.
    """
    if not file_path:
        return False
    try:
        if sys.platform.startswith("win"):
            try:
                os.startfile(file_path)  # type: ignore[attr-defined]
                return True
            except Exception:
                pass
        import subprocess as _sp
        if sys.platform.startswith("darwin"):
            _sp.Popen(["open", file_path])
        else:
            _sp.Popen(["xdg-open", file_path])
        return True
    except Exception as ex:
        logger.warning("No se pudo abrir archivo %s: %s", file_path, ex)
        return False


def main(page: ft.Page):
    """Función principal de la aplicación (bootstrap + inyección)"""

    # ==================== CONFIGURACIÓN INICIAL ====================
    page.title = "Glosaap"
    # Restaura el tamaño manual guardado (clave glosaap_window) si existe;
    # si no, usa el tamaño consistente de WINDOW_SIZES para login.
    try:
        _init_width, _init_height = resolve_window_size(page, "login")
    except Exception:
        _init_width, _init_height = get_window_size_for_view("login")
    page.window.width = _init_width
    page.window.height = _init_height
    # Nota: Flet no soporta window_min_width/height directamente
    # El tamaño mínimo lo gestiona NavigationController por vista.

    # Estado global único (fuente de verdad para NavigationController)
    ui_state = AppState()

    # Rastrea si un TextField tiene el foco (para no robar ESC mientras
    # el usuario escribe). Se actualiza encadenando on_focus/on_blur de
    # los campos conocidos tras crear las vistas (sin tocar las vistas).
    focus_state = {"textfield_focused": False}

    def _has_open_dialog():
        """True si hay algún diálogo/control modal abierto en overlay.

        Revisa page.overlay (en Flet 0.27.6 es el offstage donde
        page.open() coloca los AlertDialog/FilePicker/DatePicker).
        Cierra solo su diálogo el llamador; aquí solo se detecta.
        """
        try:
            overlay = getattr(page, "overlay", None) or []
            for control in list(overlay):
                try:
                    if getattr(control, "open", False):
                        return True
                except Exception:
                    continue
        except Exception:
            pass
        return False

    def _persist_window_size(view_name=None, width=None, height=None):
        """Guarda el tamaño actual en client_storage (nunca lanza)."""
        try:
            name = view_name or getattr(ui_state, "current_view", None) or "login"
            w = width
            h = height
            if w is None or h is None:
                try:
                    w = page.window.width
                    h = page.window.height
                except Exception:
                    return False
            return save_window_size(page, name, w, h)
        except Exception:
            return False

    def _on_window_resized(e):
        """Guarda el tamaño manual al redimensionar (hilo principal)."""
        try:
            width = getattr(e, "width", None)
            height = getattr(e, "height", None)
            if width is None or height is None:
                width = page.window.width
                height = page.window.height
            _persist_window_size(width=width, height=height)
        except Exception:
            pass

    def _on_page_close(e):
        """Guarda el tamaño final al cerrar (hilo principal)."""
        try:
            _persist_window_size()
        except Exception:
            pass

    try:
        page.on_resized = _on_window_resized
    except Exception:
        pass
    try:
        page.on_close = _on_page_close
    except Exception:
        pass
    try:
        _prev_window_handler = getattr(page.window, "on_event", None)

        def _window_event_handler(e):
            try:
                etype = str(getattr(e, "type", "") or "").upper()
                if "RESIZ" in etype or "MOVE" in etype:
                    _persist_window_size()
                elif "CLOSE" in etype:
                    _persist_window_size()
            except Exception:
                pass
            try:
                if callable(_prev_window_handler):
                    _prev_window_handler(e)
            except Exception:
                pass

        page.window.on_event = _window_event_handler
    except Exception:
        pass

    # Atajos de teclado: F5 refresca la vista actual, ESC vuelve atrás.
    def handle_keyboard(e):
        """Maneja los atajos de teclado (hilo principal: page.update OK)."""
        try:
            key = getattr(e, "key", "")
            if key == "F5":
                try:
                    refresh_current_view()
                except Exception:
                    pass
                return
            if key == "Escape":
                # No robar ESC a diálogos modales ni a campos de texto.
                try:
                    if _has_open_dialog():
                        return
                except Exception:
                    pass
                try:
                    if focus_state.get("textfield_focused"):
                        return
                except Exception:
                    pass
                try:
                    go_back()
                except Exception:
                    pass
        except Exception:
            pass

    page.on_keyboard_event = handle_keyboard

    # Inicializar el sistema de temas
    ThemeManager.init(page)
    update_colors()  # Actualizar diccionario COLORS global

    page.padding = 0
    # Icono de la ventana (ruta absoluta)
    icon_path = os.path.join(ASSETS_DIR, "icons", "app_logo.png")
    if os.path.exists(icon_path):
        page.window.icon = icon_path

    # ==================== SERVICIOS ====================
    email_service = EmailService()

    # ==================== NAVEGACIÓN (canal único) ====================
    # El controlador se crea tras las vistas; los wrappers resuelven tarde
    # (late binding) para que los callbacks de las vistas siempre pasen por él.
    nav_holder = {"controller": None}
    # Holder del verificador de updates (se inyecta tras crearlo; permite
    # re-verificar en sesiones largas sin acoplar navegación <-> updates).
    update_holder = {"checker": None}

    def _nav():
        return nav_holder["controller"]

    def go_to_login(logout=False):
        """Navega a login vía NavigationController."""
        ctl = _nav()
        if ctl is None:
            return
        ctl.go_to_login(logout=logout)

    def go_to_method_selection():
        """Navega a selección de método vía NavigationController."""
        ctl = _nav()
        if ctl is None:
            return
        ctl.go_to_method_selection()

    def go_to_dashboard():
        """Navega al dashboard vía NavigationController."""
        ctl = _nav()
        if ctl is None:
            return
        ctl.go_to_dashboard()
        # Sesiones largas: re-verifica actualización cuando toca (no bloquea).
        try:
            _chk = update_holder.get("checker")
            if _chk is not None and hasattr(_chk, "maybe_check"):
                _chk.maybe_check()
        except Exception:
            pass

    def go_to_tools():
        """Navega a herramientas vía NavigationController."""
        ctl = _nav()
        if ctl is None:
            return
        ctl.go_to_tools()

    def go_to_homologacion():
        """Navega a homologación vía NavigationController (back -> tools)."""
        ctl = _nav()
        if ctl is None:
            return
        ctl.go_to_homologacion()

    def go_to_mix_excel():
        """Navega a Mix Excel vía NavigationController (back -> tools)."""
        ctl = _nav()
        if ctl is None:
            return
        ctl.go_to_mix_excel()

    def go_to_homologador_manual():
        """Navega a homologador manual vía NavigationController (back -> tools)."""
        ctl = _nav()
        if ctl is None:
            return
        ctl.go_to_homologador_manual()

    def go_to_web_download():
        """Navega a descarga web vía NavigationController."""
        ctl = _nav()
        if ctl is None:
            return
        ctl.go_to_web_download()

    def go_to_eps_selection():
        """Navega a selección de EPS vía NavigationController."""
        ctl = _nav()
        if ctl is None:
            return
        ctl.go_to_eps_selection()

    def go_to_messages():
        """Navega a mensajes vía NavigationController."""
        ctl = _nav()
        if ctl is None:
            return
        ctl.go_to_messages()

    def go_back():
        """Retrocede según mapa único (messages->eps->dashboard, etc.)."""
        ctl = _nav()
        if ctl is None:
            return
        ctl.go_back()

    # ==================== FUNCIONES DE NEGOCIO ====================

    def handle_login_success():
        """Callback cuando el login es exitoso - ir a selección de método"""
        go_to_method_selection()

    def on_email_method():
        """Callback cuando se selecciona método de correo"""
        go_to_dashboard()

    def on_web_method():
        """Callback cuando se selecciona método web"""
        go_to_web_download()

    def on_dashboard_action(action_key):
        """Callback cuando se selecciona una acción del dashboard"""
        # Verificar si la funcionalidad está implementada
        funciones_en_desarrollo = {
            "evitar": "Evitar Glosa",
            "responder": "Responder Glosa"
        }

        if action_key in funciones_en_desarrollo:
            nombre_funcion = funciones_en_desarrollo[action_key]

            def _cerrar_dialogo(e):
                page.close(dialog)

            # Mostrar alerta usando overlay (Flet moderno)
            dialog = ft.AlertDialog(
                modal=True,
                title=ft.Text("🚧 En Desarrollo"),
                content=ft.Text(f"'{nombre_funcion}' estará disponible próximamente."),
                actions=[ft.TextButton("OK", on_click=_cerrar_dialogo)]
            )

            page.open(dialog)
            return

        # Funcionalidad implementada - continuar normalmente
        ui_state.dashboard_action = action_key
        go_to_eps_selection()

    def on_eps_selected(eps_info, date_from, date_to):
        """Callback cuando se selecciona una EPS"""
        ui_state.set_eps(eps_info, date_from, date_to)

        logger.debug("EPS seleccionada: %s | filter=%s | pattern=%s",
                     eps_info.get('name'), eps_info.get('filter'),
                     eps_info.get('subject_pattern'))

        # LIMPIAR sesión anterior antes de nueva búsqueda
        # (no borra archivos físicos, solo la lista de archivos de esta búsqueda)
        logger.debug("Limpiando archivos de busquedas anteriores...")
        email_service.clear_session()

        search_info = ui_state.get_search_info()

        # Configurar botón de procesamiento según la EPS (ft.Colors.*, sin hex)
        eps_filter = ui_state.get_eps_filter()
        if eps_filter == "mutualser":
            messages_view.show_process_button(True)
            messages_view.process_eps_btn.text = " Procesar MUTUALSER"
            messages_view.process_eps_btn.style = ft.ButtonStyle(
                color=ft.Colors.WHITE,
                bgcolor=ft.Colors.BLUE,
            )
            messages_view.process_eps_btn.data = "mutualser"
        elif eps_filter == "coosalud":
            messages_view.show_process_button(True)
            messages_view.process_eps_btn.text = " Procesar COOSALUD"
            messages_view.process_eps_btn.style = ft.ButtonStyle(
                color=ft.Colors.WHITE,
                bgcolor=ft.Colors.BLUE,
            )
            messages_view.process_eps_btn.data = "coosalud"
        elif eps_filter == "sanitas":
            messages_view.show_process_button(True)
            messages_view.process_eps_btn.text = " Procesar SANITAS"
            messages_view.process_eps_btn.style = ft.ButtonStyle(
                color=ft.Colors.WHITE,
                bgcolor=ft.Colors.BLUE,
            )
            messages_view.process_eps_btn.data = "sanitas"
        else:
            messages_view.show_process_button(False)

        # Navegar y cargar mensajes
        go_to_messages()
        load_messages(search_info)

    def filter_messages_by_eps(messages):
        """Filtra mensajes según la EPS (delega a business_logic.MessageFilter)."""
        return MessageFilter.filter_by_eps(messages, ui_state.selected_eps)

    def load_messages(search_info=""):
        """Carga mensajes del servidor y descarga adjuntos automáticamente"""
        def worker():
            load_seq = messages_view.new_generation()
            try:
                # IMPORTANTE: Limpiar archivos antiguos para que los nuevos tengan metadatos frescos
                logger.debug("Limpiando archivos temporales antiguos...")
                try:
                    email_service.attachment_service.clear_all(delete_files=True)
                    logger.debug("Archivos antiguos limpiados. Listos para nueva descarga.")
                except Exception as e:
                    logger.warning("Error limpiando temporales: %s", e)

                messages_view.set_loading(True, "🔍 Buscando correos...")

                all_msgs = []
                # Dedupe por asunto normalizado dentro de esta busqueda.
                seen_subjects = set()

                def on_found(msg):
                    if messages_view.is_cancelled(load_seq):
                        return
                    all_msgs.append(msg)
                    # Filtrar en tiempo real (lógica centralizada en MessageFilter)
                    filtered = filter_messages_by_eps(all_msgs)
                    # Mostrar mensajes en tiempo real
                    messages_view.show_messages(filtered, search_info)
                    messages_view.set_loading(True, f"🔍 Encontrados {len(all_msgs)} correo(s), mostrando {len(filtered)} filtrados...")

                    # Descargar adjuntos solo si matchea la EPS y no es duplicado.
                    if msg in filtered and not messages_view.is_cancelled(load_seq):
                        if not MessageFilter.matches(msg, ui_state.selected_eps):
                            logger.debug(
                                "Se omite descarga (no matchea EPS): %s",
                                str(msg.get("subject") or "")[:60],
                            )
                            return
                        _skey = MessageFilter.normalize_subject(msg.get("subject"))
                        if _skey and _skey in seen_subjects:
                            logger.debug(
                                "Asunto duplicado, se omite descarga: %s",
                                str(msg.get("subject") or "")[:60],
                            )
                            return
                        if _skey:
                            seen_subjects.add(_skey)
                        msg_id = msg.get("id")
                        if msg_id:
                            messages_view.update_message_status(msg_id, "📥 Descargando...")
                            try:
                                email_date_str = None
                                parsed = _parse_email_date(msg.get('date'))
                                if parsed is not None:
                                    email_date_str = parsed.strftime('%Y-%m-%d %H:%M:%S')

                                # Descargar con la fecha del correo
                                files = email_service.download_message_attachments(msg_id, email_date=email_date_str)

                                if files:
                                    messages_view.update_message_status(msg_id, f"✅ {len(files)} archivo(s)")
                                else:
                                    messages_view.update_message_status(msg_id, "⚠️ Sin adjuntos")
                            except Exception as e:
                                error_msg = str(e)
                                # Mostrar mensaje corto en UI, detalle en logs
                                if "No se pudo descargar" in error_msg or "timeout" in error_msg.lower():
                                    messages_view.update_message_status(msg_id, "❌ Error descarga", is_error=True)
                                elif "No tiene adjuntos" in error_msg:
                                    messages_view.update_message_status(msg_id, "⚠️ Sin adjuntos")
                                else:
                                    messages_view.update_message_status(msg_id, "❌ Error", is_error=True)
                                logger.warning("Error procesando correo %s: %s", msg_id, error_msg)

                # Palabra clave de búsqueda según EPS (centralizada en MessageFilter)
                search_keyword = MessageFilter.get_search_keyword(ui_state.selected_eps)
                logger.debug("Palabra clave seleccionada: '%s'", search_keyword)
                # Remitente a nivel IMAP (opcional): si la EPS tiene sender_filter
                # se envía como FROM para no descargar de más. Mismo flujo para
                # todas las EPS (dedupe + matches() sin rama especial).
                _eps_sel = ui_state.selected_eps or {}
                if isinstance(_eps_sel, dict):
                    _from_addr = (_eps_sel.get("sender_filter") or None)
                else:
                    _from_addr = (getattr(_eps_sel, "sender_filter", None) or None)

                # Buscar con filtro de fechas (timeout aumentado para búsquedas grandes)
                email_service.search_messages(
                    search_keyword,
                    limit=None,  # Sin límite - busca todos
                    timeout=120,  # 2 minutos de timeout
                    on_found=on_found,
                    date_from=ui_state.date_from,
                    date_to=ui_state.date_to,
                    from_addr=_from_addr
                )

                # Cancelado entre pasos: abortar limpio sin aplicar resultados tardíos
                if messages_view.is_cancelled(load_seq):
                    messages_view.set_loading(False, "⚠️ Procesado cancelado")
                    messages_view.show_toast("Procesado cancelado", is_success=False)
                    return

                # Filtrar por EPS (filtrado final)
                msgs = filter_messages_by_eps(all_msgs)
                ui_state.found_messages = msgs

                # Mostrar mensajes finales
                messages_view.show_messages(msgs, search_info)

                # Ocultar controles de descarga manual - no son necesarios
                messages_view.show_download_controls(False)

                excel_count = len(email_service.get_excel_files())
                if msgs:
                    messages_view.set_loading(False, f"✅ {len(msgs)} correo(s) | 📁 {excel_count} Excel listos para procesar")

                    # Mostrar diálogo de búsqueda completada
                    eps_name = (ui_state.selected_eps or {}).get("name", "")
                    date_range = ""
                    if ui_state.date_from and ui_state.date_to:
                        date_range = f"{ui_state.date_from.strftime('%d/%m/%Y')} - {ui_state.date_to.strftime('%d/%m/%Y')}"

                    AlertDialog.show_search_complete(
                        page=page,
                        total_found=len(all_msgs),
                        filtered_count=len(msgs),
                        excel_count=excel_count,
                        eps_name=eps_name,
                        date_range=date_range
                    )
                else:
                    messages_view.set_loading(False, "No hay resultados")
                    messages_view.show_download_controls(False)
                    AlertDialog.show_info(
                        page=page,
                        title="Sin resultados",
                        message=f"No se encontraron correos de {(ui_state.selected_eps or {}).get('name', 'la EPS seleccionada')} en el rango de fechas especificado."
                    )

            except Exception as ex:
                if messages_view.is_cancelled(load_seq):
                    messages_view.set_loading(False, "⚠️ Procesado cancelado")
                    return
                messages_view.set_loading(False, f"❌ Error: {str(ex)}")
                AlertDialog.show_error(
                    page=page,
                    title="Error en la búsqueda",
                    message=f"Ocurrió un error al buscar correos:\n\n{str(ex)}"
                )

        threading.Thread(target=worker, daemon=True).start()

    def download_selected_messages():
        """Descarga adjuntos de los mensajes seleccionados"""
        def worker():
            dl_seq = messages_view.new_generation()
            try:
                selected_ids = messages_view.get_selected_messages()
                if not selected_ids:
                    return

                messages_view.download_selected_btn.disabled = True
                # El refresh lo hace set_loading/update_message_status (sin page.update directo)
                messages_view.set_loading(True, f"📥 Descargando adjuntos de {len(selected_ids)} correo(s)...")

                downloaded = 0
                total_files = 0
                seen_selected = set()

                for msg in ui_state.found_messages:
                    if messages_view.is_cancelled(dl_seq):
                        break
                    if msg.get("id") in selected_ids:
                        if not MessageFilter.matches(msg, ui_state.selected_eps):
                            logger.debug(
                                "Se omite descarga manual (no matchea EPS): %s",
                                str(msg.get("subject") or "")[:60],
                            )
                            continue
                        _skey2 = MessageFilter.normalize_subject(msg.get("subject"))
                        if _skey2 and _skey2 in seen_selected:
                            logger.debug(
                                "Asunto duplicado en descarga manual, se omite: %s",
                                str(msg.get("subject") or "")[:60],
                            )
                            continue
                        if _skey2:
                            seen_selected.add(_skey2)
                        messages_view.update_message_status(msg["id"], "Descargando...")

                        try:
                            files = email_service.download_message_attachments(msg["id"])
                            downloaded += 1

                            if files:
                                total_files += len(files)
                                messages_view.update_message_status(
                                    msg["id"],
                                    f"✅ {len(files)} archivo(s)"
                                )
                            else:
                                messages_view.update_message_status(msg["id"], "Sin adjuntos")
                        except Exception:
                            messages_view.update_message_status(msg["id"], "❌ Error", is_error=True)

                messages_view.download_selected_btn.disabled = False
                if messages_view.is_cancelled(dl_seq):
                    messages_view.set_loading(False, "⚠️ Procesado cancelado")
                    messages_view.show_toast("Procesado cancelado", is_success=False)
                    return
                messages_view.set_loading(False, f"✅ Descargados {total_files} archivo(s) de {downloaded} correo(s)")

            except Exception as ex:
                messages_view.download_selected_btn.disabled = False
                if messages_view.is_cancelled(dl_seq):
                    messages_view.set_loading(False, "⚠️ Procesado cancelado")
                    return
                messages_view.set_loading(False, f"❌ Error: {str(ex)}")

        threading.Thread(target=worker, daemon=True).start()

    def process_eps_files():
        """Procesa archivos de una EPS (hilo principal deshabilita botón; worker no usa page.update directo)"""
        # Deshabilitar botón INMEDIATAMENTE al entrar (hilo principal: page.update OK)
        messages_view.process_eps_btn.disabled = True
        page.update()

        def worker():
            proc_seq = messages_view.new_generation()
            try:
                eps_type = messages_view.process_eps_btn.data
                if not eps_type:
                    messages_view.process_eps_btn.disabled = False
                    # Refresca vía canal de la vista (su show_process_button hace page.update)
                    messages_view.show_process_button(True)
                    return

                messages_view.set_processing(True, f"🔄 Procesando {eps_type.upper()}...")

                if eps_type == "mutualser":
                    # Usar session_only=True para procesar solo archivos de esta búsqueda
                    excel_files = email_service.get_excel_files(session_only=True)

                    # Verificación simple - solo verificar si hay archivos
                    if not excel_files:
                        messages_view.process_eps_btn.disabled = False
                        messages_view.set_processing(False, "❌ No hay archivos Excel para procesar")

                        # Mostrar diálogo informativo
                        AlertDialog.show_warning(
                            page=page,
                            title="Sin archivos para procesar",
                            message="No se descargaron archivos Excel en esta búsqueda.\n\nPrimero descarga los adjuntos de los correos."
                        )
                        return

                    # Procesar TODOS los archivos Excel encontrados sin confirmación
                    logger.info("Procesando %s archivos Excel automaticamente", len(excel_files))
                    messages_view.set_processing(True, f"📊 Procesando {len(excel_files)} archivo(s) Excel...")

                    resultado = email_service.procesar_mutualser()

                    # Cancelado durante el procesado (no divisible): no aplicar tardíos
                    if messages_view.is_cancelled(proc_seq):
                        messages_view.process_eps_btn.disabled = False
                        messages_view.set_processing(False, "⚠️ Procesado cancelado")
                        messages_view.show_toast("Procesado cancelado", is_success=False)
                        messages_view.show_process_button(True)
                        return

                    if resultado['success']:
                        resumen = resultado['resumen']
                        msg = f"✅ ¡Archivos generados!\n"
                        msg += f"📄 {resultado['output_file']}\n"
                        if resultado.get('objeciones_file'):
                            msg += f"📋 {resultado['objeciones_file']}\n"
                        msg += f"📊 {resumen['total_registros']} registros | {resumen['codigos_homologados']} homologados"
                        messages_view.set_processing(False, msg)
                        messages_view.processing_status.color = ft.Colors.GREEN

                        # Mostrar diálogo de procesamiento completado (resumen post-procesado)
                        output_files = [resultado['output_file']]
                        if resultado.get('objeciones_file'):
                            output_files.append(resultado['objeciones_file'])

                        _mutualser_output = str(resultado['output_file'])
                        _objeciones_output = str(resultado.get('objeciones_file') or "")
                        try:
                            _total = int(resumen.get('total_registros', 0) or 0)
                        except (TypeError, ValueError):
                            _total = 0
                        try:
                            _hom = int(resumen.get('codigos_homologados', 0) or 0)
                        except (TypeError, ValueError):
                            _hom = 0
                        resumen_summary = dict(resumen)
                        resumen_summary['no_homologados'] = max(_total - _hom, 0) if _total else 0
                        resumen_summary['output_dir'] = os.path.dirname(_mutualser_output)

                        def open_output_folder():
                            _open_folder_in_explorer(os.path.dirname(_mutualser_output))

                        def open_non_homologated():
                            if _objeciones_output and os.path.exists(_objeciones_output):
                                if not _open_file_default(_objeciones_output):
                                    AlertDialog.show_info(
                                        page=page,
                                        title="No homologados",
                                        message=f"Hay {resumen_summary['no_homologados']} registro(s) no homologados.\n\nArchivo:\n{_objeciones_output}",
                                    )
                            else:
                                AlertDialog.show_info(
                                    page=page,
                                    title="No homologados",
                                    message=f"Hay {resumen_summary['no_homologados']} registro(s) no homologados.",
                                )

                        AlertDialog.show_processing_complete(
                            page=page,
                            eps_name="MUTUALSER",
                            stats=resumen_summary,
                            output_files=output_files,
                            on_open_folder=open_output_folder,
                            on_view_non_homologated=open_non_homologated if resumen_summary['no_homologados'] > 0 else None
                        )
                    else:
                        messages_view.set_processing(False, f"❌ Error: {resultado['message']}")
                        messages_view.processing_status.color = ft.Colors.RED

                        AlertDialog.show_error(
                            page=page,
                            title="Error al procesar",
                            message=f"No se pudo procesar los archivos:\n\n{resultado['message']}"
                        )

                    messages_view.process_eps_btn.disabled = False
                    # Refresca vía canal de la vista (set_processing/show hacen page.update)
                    messages_view.show_process_button(True)

                elif eps_type == "coosalud":
                    from app.service.processors import CoosaludProcessor

                    # Obtener archivos Excel de ESTA SESIÓN (excluyendo devoluciones)
                    excel_files = email_service.get_excel_files(exclude_devoluciones=True, session_only=True)
                    if not excel_files:
                        messages_view.process_eps_btn.disabled = False
                        messages_view.set_processing(False, "❌ No hay archivos Excel para procesar")

                        AlertDialog.show_warning(
                            page=page,
                            title="Sin archivos para procesar",
                            message="No se descargaron archivos Excel de GLOSAS en esta búsqueda.\n\nPrimero descarga los adjuntos de los correos."
                        )
                        return

                    logger.info("COOSALUD procesando %s archivos Excel (devoluciones excluidas)", len(excel_files))
                    messages_view.set_processing(True, f"📊 Procesando {len(excel_files)} archivo(s) Excel...")

                    # Configurar procesador con homologador de Coosalud
                    homologador_path = get_homologador_path("coosalud")
                    output_dir = get_output_dir("Coosalud")

                    # Delegar creación del directorio al servicio de configuración
                    if not os.path.exists(output_dir):
                        if ensure_dir(output_dir):
                            logger.debug("COOSALUD directorio de salida creado: %s", output_dir)
                        else:
                            logger.warning("COOSALUD error al crear directorio: %s", output_dir)

                    # Fecha del correo más reciente (helper centralizado)
                    email_date = _latest_email_date_str(ui_state.found_messages)
                    if email_date:
                        logger.debug("COOSALUD fecha del correo extraida: %s", email_date)
                    else:
                        logger.warning("COOSALUD sin fecha extraible de %s mensajes", len(ui_state.found_messages))

                    processor = CoosaludProcessor(homologador_path=homologador_path)
                    result_data, message = processor.process_glosas(
                        excel_files,
                        output_dir=output_dir,
                        email_date=email_date,
                        attachment_service=email_service.attachment_service
                    )

                    # Cancelado durante el procesado (no divisible): no aplicar tardíos
                    if messages_view.is_cancelled(proc_seq):
                        messages_view.process_eps_btn.disabled = False
                        messages_view.set_processing(False, "⚠️ Procesado cancelado")
                        messages_view.show_toast("Procesado cancelado", is_success=False)
                        messages_view.show_process_button(True)
                        return

                    # Rehabilitar botón después de procesar
                    messages_view.process_eps_btn.disabled = False

                    if result_data:
                        messages_view.set_processing(False, f"✅ {message}")
                        messages_view.processing_status.color = ft.Colors.GREEN

                        # Preparar estadísticas desde los DataFrames (resumen post-procesado)
                        total_detalles = len(result_data.get('detalle', [])) if isinstance(result_data, dict) else 0
                        total_glosas = len(result_data.get('glosa', [])) if isinstance(result_data, dict) else 0

                        _coosalud_total = total_detalles + total_glosas
                        _coosalud_hom = 0
                        try:
                            _detalle_df = result_data.get('detalle') if isinstance(result_data, dict) else None
                            if _detalle_df is not None and hasattr(_detalle_df, 'columns') and "Codigo homologado DGH" in _detalle_df.columns:
                                _coosalud_hom = int((_detalle_df["Codigo homologado DGH"] != "").sum())
                        except Exception:
                            _coosalud_hom = 0

                        stats = {
                            'archivos_procesados': len(excel_files),
                            'total_registros': _coosalud_total,
                            'codigos_homologados': _coosalud_hom,
                            'no_homologados': max(_coosalud_total - _coosalud_hom, 0) if _coosalud_total else 0,
                            'output_dir': str(output_dir),
                        }

                        # Extraer nombre del archivo del mensaje
                        output_files = []
                        if "Guardado en:" in message:
                            for line in message.split('\n'):
                                if "Guardado en:" in line or "COOSALUD_GLOSAS_" in line:
                                    # Extraer ruta del archivo
                                    path = line.split(":")[-1].strip() if ":" in line else ""
                                    if path and os.path.exists(path):
                                        output_files.append(path)

                        _coosalud_dir = str(output_dir)
                        _coosalud_no_hom = int(stats.get('no_homologados', 0) or 0)

                        def open_coosalud_folder():
                            _open_folder_in_explorer(_coosalud_dir)

                        def open_coosalud_non_homologated():
                            AlertDialog.show_info(
                                page=page,
                                title="No homologados",
                                message=f"Hay {_coosalud_no_hom} registro(s) no homologados.\n\nRevisa el Excel generado en:\n{_coosalud_dir}",
                            )

                        AlertDialog.show_processing_complete(
                            page=page,
                            eps_name="COOSALUD",
                            stats=stats,
                            output_files=output_files if output_files else [f"📁 {output_dir}"],
                            on_open_folder=open_coosalud_folder,
                            on_view_non_homologated=open_coosalud_non_homologated if _coosalud_no_hom > 0 else None
                        )
                    else:
                        messages_view.set_processing(False, f"❌ {message}")
                        messages_view.processing_status.color = ft.Colors.RED

                        AlertDialog.show_error(
                            page=page,
                            title="Error al procesar",
                            message=message
                        )

                    # Refresca vía canal de la vista
                    messages_view.show_process_button(True)

                elif eps_type == "sanitas":
                    # Usar session_only=True para procesar solo archivos de esta búsqueda
                    excel_files = email_service.get_excel_files(exclude_devoluciones=True, session_only=True)

                    # Verificación simple - solo verificar si hay archivos
                    if not excel_files:
                        messages_view.process_eps_btn.disabled = False
                        messages_view.set_processing(False, "❌ No hay archivos Excel para procesar")

                        # Mostrar diálogo informativo
                        AlertDialog.show_warning(
                            page=page,
                            title="Sin archivos para procesar",
                            message="No se descargaron archivos Excel de GLOSAS en esta búsqueda.\n\nPrimero descarga los adjuntos de los correos."
                        )
                        return

                    logger.info("SANITAS procesando %s archivos Excel (devoluciones excluidas)", len(excel_files))
                    messages_view.set_processing(True, f"📊 Procesando {len(excel_files)} archivo(s) Excel...")

                    # Fecha del correo más reciente (helper centralizado)
                    email_date = _latest_email_date_str(ui_state.found_messages)
                    resultado = email_service.procesar_sanitas(email_date=email_date)

                    # Cancelado durante el procesado (no divisible): no aplicar tardíos
                    if messages_view.is_cancelled(proc_seq):
                        messages_view.process_eps_btn.disabled = False
                        messages_view.set_processing(False, "⚠️ Procesado cancelado")
                        messages_view.show_toast("Procesado cancelado", is_success=False)
                        messages_view.show_process_button(True)
                        return

                    # Rehabilitar botón después de procesar
                    messages_view.process_eps_btn.disabled = False

                    if resultado['success']:
                        resumen = resultado['resumen']
                        msg = f"✅ ¡Archivos generados!\n"
                        msg += f"📄 {resultado['output_file']}\n"
                        if resultado.get('objeciones_file'):
                            msg += f"📋 {resultado['objeciones_file']}\n"
                        msg += f"📊 {resumen['total_registros']} registros | {resumen['codigos_homologados']} homologados"
                        messages_view.set_processing(False, msg)
                        messages_view.processing_status.color = ft.Colors.GREEN

                        # Mostrar diálogo de procesamiento completado (resumen post-procesado)
                        output_files = [resultado['output_file']]
                        if resultado.get('objeciones_file'):
                            output_files.append(resultado['objeciones_file'])

                        _sanitas_output = str(resultado['output_file'])
                        _objeciones_output = str(resultado.get('objeciones_file') or "")
                        try:
                            _total = int(resumen.get('total_registros', 0) or 0)
                        except (TypeError, ValueError):
                            _total = 0
                        try:
                            _hom = int(resumen.get('codigos_homologados', 0) or 0)
                        except (TypeError, ValueError):
                            _hom = 0
                        resumen_summary = dict(resumen)
                        resumen_summary['no_homologados'] = max(_total - _hom, 0) if _total else 0
                        resumen_summary['output_dir'] = os.path.dirname(_sanitas_output)

                        def open_sanitas_folder():
                            _open_folder_in_explorer(os.path.dirname(_sanitas_output))

                        def open_sanitas_non_homologated():
                            if _objeciones_output and os.path.exists(_objeciones_output):
                                if not _open_file_default(_objeciones_output):
                                    AlertDialog.show_info(
                                        page=page,
                                        title="No homologados",
                                        message=f"Hay {resumen_summary['no_homologados']} registro(s) no homologados.\n\nArchivo:\n{_objeciones_output}",
                                    )
                            else:
                                AlertDialog.show_info(
                                    page=page,
                                    title="No homologados",
                                    message=f"Hay {resumen_summary['no_homologados']} registro(s) no homologados.",
                                )

                        AlertDialog.show_processing_complete(
                            page=page,
                            eps_name="SANITAS",
                            stats=resumen_summary,
                            output_files=output_files,
                            on_open_folder=open_sanitas_folder,
                            on_view_non_homologated=open_sanitas_non_homologated if resumen_summary['no_homologados'] > 0 else None
                        )
                    else:
                        messages_view.set_processing(False, f"❌ Error: {resultado['message']}")
                        messages_view.processing_status.color = ft.Colors.RED

                        AlertDialog.show_error(
                            page=page,
                            title="Error al procesar",
                            message=f"No se pudo procesar los archivos:\n\n{resultado['message']}"
                        )

                    messages_view.process_eps_btn.disabled = False
                    # Refresca vía canal de la vista (set_processing/show hacen page.update)
                    messages_view.show_process_button(True)

            except Exception as ex:
                if messages_view.is_cancelled(proc_seq):
                    messages_view.process_eps_btn.disabled = False
                    messages_view.set_processing(False, "⚠️ Procesado cancelado")
                    messages_view.show_process_button(True)
                    return
                messages_view.set_processing(False, f"❌ Error: {str(ex)}")
                messages_view.processing_status.color = ft.Colors.RED
                messages_view.process_eps_btn.disabled = False
                # Refresca vía canal de la vista
                messages_view.show_process_button(True)

                AlertDialog.show_error(
                    page=page,
                    title="Error en el procesamiento",
                    message=f"Ocurrió un error inesperado:\n\n{str(ex)}"
                )

        threading.Thread(target=worker, daemon=True).start()

    # ==================== CREAR VISTAS (inyección) ====================

    login_view = LoginView(
        page=page,
        email_service=email_service,
        on_login_success=handle_login_success,
        assets_dir=ASSETS_DIR
    )

    dashboard_view = DashboardView(
        page=page,
        assets_dir=ASSETS_DIR,
        on_card_click=on_dashboard_action,
        on_tools_click=go_to_tools,
        on_logout=lambda: go_to_login(logout=True),
        on_web_download=go_to_web_download
    )

    tools_view = ToolsView(
        page=page,
        assets_dir=ASSETS_DIR,
        navigation_controller=None,  # se inyecta tras crear el controlador
        on_back=go_to_dashboard,
        on_homologacion=go_to_homologacion,
        on_mix_excel=go_to_mix_excel,
        on_homologador_manual=go_to_homologador_manual
    )

    method_selection_view = MethodSelectionView(
        page=page,
        assets_dir=ASSETS_DIR,
        on_email_method=on_email_method,
        on_web_method=on_web_method,
        on_logout=lambda: go_to_login(logout=True)
    )

    web_download_view = WebDownloadView(
        page=page,
        assets_dir=ASSETS_DIR,
        on_back=go_to_method_selection  # Volver a selección de método
    )

    homologacion_view = HomologacionView(
        page=page,
        navigation_controller=None,  # se inyecta tras crear el controlador
        on_back=go_to_tools
    )

    mix_excel_view = MixExcelView(
        page=page,
        navigation_controller=None,  # se inyecta tras crear el controlador
        on_back=go_to_tools
    )

    homologador_manual_view = HomologadorManualView(
        page=page,
        on_back=go_to_tools
    )

    messages_view = MessagesView(
        page=page,
        on_back=go_to_eps_selection,
        on_refresh=lambda: load_messages(messages_view.search_info_text.value or ""),
        on_download_selected=download_selected_messages,
        on_process=process_eps_files,
        navigation_controller=None,  # se inyecta tras crear el controlador
    )

    eps_screen = EpsScreen(
        page=page,
        on_eps_selected=on_eps_selected,
        on_logout=go_to_dashboard,
        on_back=go_to_dashboard,
        navigation_controller=None,  # se inyecta tras crear el controlador
    )

    # Inicializar NavigationController con todas las vistas (canal único)
    views_dict = {
        "login": login_view,
        "method_selection": method_selection_view,
        "dashboard": dashboard_view,
        "tools": tools_view,
        "homologacion": homologacion_view,
        "mix_excel": mix_excel_view,
        "homologador_manual": homologador_manual_view,
        "web_download": web_download_view,
        "eps": eps_screen,
        "messages": messages_view
    }
    navigation_controller = NavigationController(page, views_dict, ui_state)
    nav_holder["controller"] = navigation_controller

    # Inyectar controlador en las vistas que lo usan (sin tercer canal page.data)
    tools_view.navigation_controller = navigation_controller
    homologacion_view.navigation_controller = navigation_controller
    mix_excel_view.navigation_controller = navigation_controller
    messages_view.navigation_controller = navigation_controller
    eps_screen.navigation_controller = navigation_controller
    # Sincronizar headers que capturaron None al construirse
    for _v in (tools_view, homologacion_view, mix_excel_view):
        try:
            if hasattr(_v, 'nav_header') and _v.nav_header is not None:
                _v.nav_header.nav_controller = navigation_controller
        except Exception:
            pass

    # ==================== REFRESH GLOBAL (F5) + FOCO ====================

    def refresh_current_view():
        """Re-ejecuta la acción de refresh de la vista actual (F5 global).

        Solo messages tiene refresh real (recarga del servidor). Si la
        vista actual no tiene refresh, no hace nada y nunca lanza.
        """
        try:
            current = getattr(ui_state, "current_view", None)
        except Exception:
            return
        try:
            if current == "messages":
                try:
                    search_text = ""
                    try:
                        search_text = messages_view.search_info_text.value or ""
                    except Exception:
                        pass
                    load_messages(search_text)
                    return
                except Exception:
                    return
            # Fallback genérico: si la vista expone on_refresh/refresh/reload,
            # se invoca; si no existe, no hace nada (sin errores).
            try:
                view = views_dict.get(current) if isinstance(views_dict, dict) else None
            except Exception:
                view = None
            if view is None:
                return
            for attr in ("on_refresh", "refresh", "reload", "refresh_view"):
                try:
                    fn = getattr(view, attr, None)
                except Exception:
                    continue
                if callable(fn):
                    try:
                        fn()
                    except TypeError:
                        try:
                            fn(None)
                        except Exception:
                            pass
                    except Exception:
                        pass
                    return
        except Exception:
            pass

    def _track_textfield_focus(field):
        """Encadena on_focus/on_blur para rastrear foco sin romper handlers."""
        if field is None:
            return
        try:
            prev_focus = getattr(field, "on_focus", None)
            prev_blur = getattr(field, "on_blur", None)

            def _on_focus(e):
                focus_state["textfield_focused"] = True
                try:
                    if callable(prev_focus):
                        prev_focus(e)
                except Exception:
                    pass

            def _on_blur(e):
                focus_state["textfield_focused"] = False
                try:
                    if callable(prev_blur):
                        prev_blur(e)
                except Exception:
                    pass

            field.on_focus = _on_focus
            field.on_blur = _on_blur
        except Exception:
            pass

    # Registrar foco en los TextField conocidos (login, filtro messages,
    # homologación, mix, web). Si una vista aún no construyó sus campos
    # (homologación los crea al seleccionar EPS), se ignora sin errores.
    try:
        _known_fields = []
        for _candidate in (
            getattr(login_view, "email_input", None),
            getattr(login_view, "password_input", None),
            getattr(login_view, "server_input", None),
            getattr(messages_view, "filter_field", None),
            getattr(homologacion_view, "codigo_erp_field", None),
            getattr(homologacion_view, "codigo_dgh_field", None),
            getattr(homologacion_view, "buscar_field", None),
            getattr(mix_excel_view, "tolerance_field", None),
            getattr(web_download_view, "familiar_nit", None),
            getattr(web_download_view, "familiar_usuario", None),
            getattr(web_download_view, "familiar_password", None),
            getattr(web_download_view, "familiar_fecha_inicio", None),
            getattr(web_download_view, "familiar_fecha_fin", None),
            getattr(web_download_view, "fomag_usuario", None),
            getattr(web_download_view, "fomag_password", None),
        ):
            if _candidate is not None:
                _known_fields.append(_candidate)
        for _field in _known_fields:
            _track_textfield_focus(_field)
    except Exception:
        pass

    # ==================== CONSTRUIR PÁGINA ====================

    # Función para abrir configuración global (canónica reutilizada)
    def open_global_settings(e):
        """Abre el diálogo de configuración desde cualquier pantalla"""
        show_settings_dialog(page)

    # Botón de configuración global (visible en todas las pantallas)
    global_settings_btn = ft.Container(
        content=ft.IconButton(
            icon=ft.Icons.SETTINGS,
            icon_size=22,
            tooltip="Configuración",
            on_click=open_global_settings,
        ),
        right=15,
        bottom=10,
    )

    page.add(
        ft.Stack([
            control for control in [
                login_view.container,
                method_selection_view.container,
                dashboard_view.container,
                tools_view.container,
                homologacion_view.container,
                mix_excel_view.container,
                homologador_manual_view.container,
                web_download_view.container,
                eps_screen.container,
                messages_view.container,
            ] if control is not None
        ] + [global_settings_btn], expand=True)  # Agregar el botón de config al final del Stack
    )

    # ==================== VERIFICADOR DE ACTUALIZACIONES ====================

    # Crear verificador de actualizaciones (intervalo real desde config)
    check_interval_hours = AUTO_UPDATE_CONFIG.get("check_interval_hours", 24)
    update_checker = UpdateChecker(
        page=page,
        current_version=APP_VERSION,
        github_repo=GITHUB_REPO,
        check_interval_hours=check_interval_hours,
    )
    update_holder["checker"] = update_checker

    # Verificar actualizaciones silenciosamente al inicio (si está habilitado).
    # maybe_check() respeta intervalo + remind_at/skip_versions y persiste
    # last_check en el mismo state file; no bloquea el arranque.
    if AUTO_UPDATE_CONFIG.get("enabled") and AUTO_UPDATE_CONFIG.get("check_on_startup"):
        logger.info(f"Verificando actualizaciones al inicio (v{APP_VERSION})...")
        try:
            update_checker.maybe_check()
        except Exception as ex:
            logger.warning("No se pudo verificar actualización inicial: %s", ex)

    # Exponer solo funciones no navegacionales en page.data (sin canal de navegación)
    if not hasattr(page, 'data') or not page.data:
        page.data = {}
    page.data['check_updates'] = update_checker.check_updates  # type: ignore
    page.data['maybe_check_updates'] = update_checker.maybe_check  # type: ignore
    page.data['app_version'] = APP_VERSION  # type: ignore

    # ==================== AUTO-LOGIN ====================

    login_view.try_auto_login()


if __name__ == "__main__":
    ft.app(target=main)
