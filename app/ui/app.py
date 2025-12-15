"""
Aplicación Glosaap - Cliente IMAP con Flet (REFACTORIZADO)
"""
import flet as ft
import os
import sys
import threading

# Configurar path para imports - agregar el directorio raíz del proyecto
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from app.service.email_service import EmailService
from app.ui.styles import COLORS, WINDOW_SIZES
from app.ui.screens.eps_screen import EpsScreen
from app.ui.views import DashboardView, LoginView, ToolsView, MessagesView
from app.ui.views.homologacion_view import HomologacionView
from app.ui.views.mix_excel_view import MixExcelView
from app.ui.views.homologador_manual_view import HomologadorManualView
from app.ui.views.web_download_view import WebDownloadView
from app.ui.views.method_selection_view import MethodSelectionView
from app.ui.components.alert_dialog import AlertDialog

# Ruta de assets (carpeta con imágenes)
ASSETS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "assets"))


def main(page: ft.Page):
    """Función principal de la aplicación"""
    
    # ==================== CONFIGURACIÓN INICIAL ====================
    page.title = "Glosaap"
    page.window_width = WINDOW_SIZES["login"]["width"]
    page.window_height = WINDOW_SIZES["login"]["height"]
    page.bgcolor = COLORS["bg_white"]
    page.padding = 0
    page.assets_dir = ASSETS_DIR
    
    # Icono de la ventana (ruta absoluta)
    icon_path = os.path.join(ASSETS_DIR, "icons", "app_logo.png")
    if os.path.exists(icon_path):
        page.window.icon = icon_path
    
    # Estado de navegación actual
    current_view = {"name": "login"}
    
    # ==================== SERVICIOS ====================
    email_service = EmailService()
    
    # Estado global
    app_state = {
        "selected_eps": None,
        "date_from": None,
        "date_to": None,
        "dashboard_action": None,
        "found_messages": []
    }
    
    # ==================== FUNCIONES DE NAVEGACIÓN ====================
    
    def go_to_login(logout=False):
        """Navega a la pantalla de login"""
        if logout:
            login_view.logout()
        current_view["name"] = "login"
        login_view.show()
        dashboard_view.hide()
        method_selection_view.hide()
        tools_view.hide()
        eps_screen.hide()
        messages_view.hide()
        homologacion_view.hide()
        mix_excel_view.hide()
        homologador_manual_view.hide()
        web_download_view.hide()
        page.window_width = WINDOW_SIZES["login"]["width"]
        page.window_height = WINDOW_SIZES["login"]["height"]
        page.update()
    
    def go_to_method_selection():
        """Navega a la selección de método (correo vs web)"""
        current_view["name"] = "method_selection"
        login_view.hide()
        dashboard_view.hide()
        method_selection_view.show()
        tools_view.hide()
        eps_screen.hide()
        messages_view.hide()
        homologacion_view.hide()
        mix_excel_view.hide()
        homologador_manual_view.hide()
        web_download_view.hide()
        page.window_width = 900
        page.window_height = 600
        page.update()
    
    def go_to_dashboard():
        """Navega al dashboard principal"""
        current_view["name"] = "dashboard"
        login_view.hide()
        dashboard_view.show()
        method_selection_view.hide()
        tools_view.hide()
        eps_screen.hide()
        messages_view.hide()
        homologacion_view.hide()
        mix_excel_view.hide()
        homologador_manual_view.hide()
        web_download_view.hide()
        page.window_width = 800
        page.window_height = 550
        page.update()
    
    def go_to_tools():
        """Navega a la pantalla de herramientas"""
        current_view["name"] = "tools"
        login_view.hide()
        dashboard_view.hide()
        method_selection_view.hide()
        tools_view.show()
        eps_screen.hide()
        messages_view.hide()
        homologacion_view.hide()
        mix_excel_view.hide()
        homologador_manual_view.hide()
        web_download_view.hide()
        page.window_width = 800
        page.window_height = 500
        page.update()
    
    def go_to_homologacion():
        """Navega a la gestión de homologación"""
        current_view["name"] = "homologacion"
        login_view.hide()
        dashboard_view.hide()
        method_selection_view.hide()
        tools_view.hide()
        eps_screen.hide()
        messages_view.hide()
        homologacion_view.show()
        mix_excel_view.hide()
        homologador_manual_view.hide()
        web_download_view.hide()
        page.window_width = 900
        page.window_height = 600
        page.update()
    
    def go_to_mix_excel():
        """Navega a Mix Excel"""
        current_view["name"] = "mix_excel"
        login_view.hide()
        dashboard_view.hide()
        method_selection_view.hide()
        tools_view.hide()
        eps_screen.hide()
        messages_view.hide()
        homologacion_view.hide()
        homologador_manual_view.hide()
        mix_excel_view.show()
        web_download_view.hide()
        page.window_width = 600
        page.window_height = 700
        page.update()
    
    def go_to_homologador_manual():
        """Navega al Homologador Manual"""
        current_view["name"] = "homologador_manual"
        login_view.hide()
        dashboard_view.hide()
        method_selection_view.hide()
        tools_view.hide()
        eps_screen.hide()
        messages_view.hide()
        homologacion_view.hide()
        mix_excel_view.hide()
        homologador_manual_view.show()
        web_download_view.hide()
        page.window_width = 650
        page.window_height = 700
        page.update()
    
    def go_to_web_download():
        """Navega a la pantalla de descarga web"""
        current_view["name"] = "web_download"
        login_view.hide()
        dashboard_view.hide()
        method_selection_view.hide()
        tools_view.hide()
        eps_screen.hide()
        messages_view.hide()
        homologacion_view.hide()
        mix_excel_view.hide()
        homologador_manual_view.hide()
        web_download_view.show()
        page.window_width = 1000
        page.window_height = 700
        page.update()
    
    def go_to_eps_selection():
        """Navega a la pantalla de selección de EPS"""
        current_view["name"] = "eps"
        login_view.hide()
        dashboard_view.hide()
        method_selection_view.hide()
        tools_view.hide()
        eps_screen.show()
        messages_view.hide()
        homologacion_view.hide()
        mix_excel_view.hide()
        homologador_manual_view.hide()
        web_download_view.hide()
        page.window_width = WINDOW_SIZES["main"]["width"]
        page.window_height = WINDOW_SIZES["main"]["height"]
        page.update()
    
    def go_to_messages():
        """Navega a la pantalla de mensajes"""
        current_view["name"] = "messages"
        login_view.hide()
        dashboard_view.hide()
        method_selection_view.hide()
        tools_view.hide()
        eps_screen.hide()
        messages_view.show()
        homologacion_view.hide()
        mix_excel_view.hide()
        homologador_manual_view.hide()
        web_download_view.hide()
        page.update()
    
    def go_back():
        """Navega hacia atrás según la vista actual"""
        if current_view["name"] == "messages":
            go_to_eps_selection()
        elif current_view["name"] == "eps":
            go_to_dashboard()
        elif current_view["name"] == "tools":
            go_to_dashboard()
        elif current_view["name"] == "mix_excel":
            go_to_tools()
        elif current_view["name"] == "homologador_manual":
            go_to_tools()
        elif current_view["name"] == "web_download":
            go_to_dashboard()
        elif current_view["name"] == "dashboard":
            go_to_login()
    
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
        app_state["dashboard_action"] = action_key
        go_to_eps_selection()
    
    def on_eps_selected(eps_info, date_from, date_to):
        """Callback cuando se selecciona una EPS"""
        app_state["selected_eps"] = eps_info
        app_state["date_from"] = date_from
        app_state["date_to"] = date_to
        
        # Preparar info de búsqueda
        eps_name = eps_info["name"]
        date_info = ""
        if date_from and date_to:
            date_info = f" | {date_from.strftime('%d/%m/%Y')} - {date_to.strftime('%d/%m/%Y')}"
        elif date_from:
            date_info = f" | Desde {date_from.strftime('%d/%m/%Y')}"
        elif date_to:
            date_info = f" | Hasta {date_to.strftime('%d/%m/%Y')}"
        
        search_info = f"EPS: {eps_name}{date_info}"
        
        # Configurar botón de procesamiento según la EPS
        eps_filter = eps_info.get("filter", "").lower()
        if eps_filter == "mutualser":
            messages_view.show_process_button(True)
            messages_view.process_eps_btn.text = "📊 Procesar MUTUALSER"
            messages_view.process_eps_btn.bgcolor = COLORS["primary"]
            messages_view.process_eps_btn.data = "mutualser"
        elif eps_filter == "coosalud":
            messages_view.show_process_button(True)
            messages_view.process_eps_btn.text = "📊 Procesar COOSALUD"
            messages_view.process_eps_btn.bgcolor = COLORS["success"]
            messages_view.process_eps_btn.data = "coosalud"
        else:
            messages_view.show_process_button(False)
        
        # Navegar y cargar mensajes
        go_to_messages()
        load_messages(search_info)
    
    def filter_messages_by_eps(messages):
        """Filtra mensajes según la EPS seleccionada"""
        eps = app_state.get("selected_eps")
        if not eps or not eps.get("filter"):
            return messages
        
        filtered = []
        filter_type = eps.get("filter_type", "keyword")
        filter_value = eps["filter"].lower()
        subject_pattern = eps.get("subject_pattern", "").lower()
        
        for msg in messages:
            subject = (msg.get("subject") or "").lower()
            from_addr = (msg.get("from") or "").lower()
            
            if filter_type == "keyword":
                if filter_value in subject or filter_value in from_addr:
                    filtered.append(msg)
            elif filter_type == "subject_exact_pattern":
                if subject_pattern in subject:
                    # Excluir Sanitas si es filtro de Mutualser
                    if "sanitas" not in subject and "sanitas" not in from_addr:
                        # Verificar filtro por remitente si existe
                        sender_filter = eps.get("sender_filter", "").lower()
                        if sender_filter:
                            if sender_filter in from_addr:
                                filtered.append(msg)
                        else:
                            filtered.append(msg)
            elif filter_type == "email":
                if filter_value in from_addr:
                    filtered.append(msg)
        
        return filtered
    
    def load_messages(search_info=""):
        """Carga mensajes del servidor y descarga adjuntos automáticamente"""
        def worker():
            try:
                messages_view.set_loading(True, "🔍 Buscando correos...")
                
                all_msgs = []
                downloaded_count = 0
                
                def on_found(msg):
                    nonlocal downloaded_count
                    all_msgs.append(msg)
                    # Filtrar en tiempo real
                    filtered = filter_messages_by_eps(all_msgs)
                    # Mostrar mensajes en tiempo real
                    messages_view.show_messages(filtered, search_info)
                    messages_view.set_loading(True, f"🔍 Encontrados {len(all_msgs)} correo(s), mostrando {len(filtered)} filtrados...")
                    
                    # Descargar adjuntos automáticamente para mensajes de la EPS seleccionada
                    if msg in filtered:
                        msg_id = msg.get("id")
                        if msg_id:
                            messages_view.update_message_status(msg_id, "📥 Descargando...")
                            try:
                                files = email_service.download_message_attachments(msg_id)
                                if files:
                                    downloaded_count += 1
                                    messages_view.update_message_status(msg_id, f"✅ {len(files)} archivo(s)")
                                else:
                                    messages_view.update_message_status(msg_id, "Sin adjuntos Excel")
                            except Exception as e:
                                messages_view.update_message_status(msg_id, f"❌ Error", is_error=True)
                
                # Buscar con filtro de fechas
                email_service.search_messages(
                    "glosa",
                    limit=500,
                    timeout=30,
                    on_found=on_found,
                    date_from=app_state.get("date_from"),
                    date_to=app_state.get("date_to")
                )
                
                # Filtrar por EPS (filtrado final)
                msgs = filter_messages_by_eps(all_msgs)
                app_state["found_messages"] = msgs
                
                # Mostrar mensajes finales
                messages_view.show_messages(msgs, search_info)
                # Actualizar estados de los mensajes que ya fueron descargados
                for msg in msgs:
                    msg_id = msg.get("id")
                    if msg_id and msg_id in messages_view.message_rows:
                        # Re-verificar archivos descargados
                        pass  # El estado ya fue actualizado durante la descarga
                
                # Ocultar controles de descarga manual - no son necesarios
                messages_view.show_download_controls(False)
                
                excel_count = len(email_service.get_excel_files())
                if msgs:
                    messages_view.set_loading(False, f"✅ {len(msgs)} correo(s) | 📁 {excel_count} Excel listos para procesar")
                    
                    # Mostrar diálogo de búsqueda completada
                    eps_name = app_state.get("selected_eps", {}).get("name", "")
                    date_from = app_state.get("date_from")
                    date_to = app_state.get("date_to")
                    date_range = ""
                    if date_from and date_to:
                        date_range = f"{date_from.strftime('%d/%m/%Y')} - {date_to.strftime('%d/%m/%Y')}"
                    
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
                        message=f"No se encontraron correos de {app_state.get('selected_eps', {}).get('name', 'la EPS seleccionada')} en el rango de fechas especificado."
                    )
                
            except Exception as ex:
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
            try:
                selected_ids = messages_view.get_selected_messages()
                if not selected_ids:
                    return
                
                messages_view.download_selected_btn.disabled = True
                messages_view.messages_status.value = f"📥 Descargando adjuntos de {len(selected_ids)} correo(s)..."
                page.update()
                
                downloaded = 0
                total_files = 0
                
                for msg in app_state["found_messages"]:
                    if msg.get("id") in selected_ids:
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
                
                messages_view.messages_status.value = f"✅ Descargados {total_files} archivo(s) de {downloaded} correo(s)"
                messages_view.download_selected_btn.disabled = False
                page.update()
                
            except Exception as ex:
                messages_view.messages_status.value = f"❌ Error: {str(ex)}"
                messages_view.download_selected_btn.disabled = False
                page.update()
        
        threading.Thread(target=worker, daemon=True).start()
    
    def process_eps_files():
        """Procesa archivos de una EPS"""
        def worker():
            try:
                eps_type = messages_view.process_eps_btn.data
                if not eps_type:
                    return
                
                messages_view.set_processing(True, f"🔄 Procesando {eps_type.upper()}...")
                messages_view.process_eps_btn.disabled = True
                
                if eps_type == "mutualser":
                    excel_files = email_service.get_excel_files()
                    
                    # Verificación simple - solo verificar si hay archivos
                    if not excel_files:
                        messages_view.set_processing(False, "❌ No hay archivos Excel para procesar")
                        messages_view.process_eps_btn.disabled = False
                        
                        # Mostrar diálogo informativo
                        AlertDialog.show_warning(
                            page=page,
                            title="Sin archivos para procesar",
                            message="No se encontraron archivos Excel en el directorio temporal.\n\nLos archivos se almacenan automáticamente cuando descargas adjuntos."
                        )
                        return
                    
                    # Procesar TODOS los archivos Excel encontrados sin confirmación
                    print(f"✅ Procesando TODOS los {len(excel_files)} archivos Excel automáticamente")
                    messages_view.set_processing(True, f"📊 Procesando {len(excel_files)} archivo(s) Excel...")
                    
                    resultado = email_service.procesar_mutualser()
                    
                    if resultado['success']:
                        resumen = resultado['resumen']
                        msg = f"✅ ¡Archivos generados!\n"
                        msg += f"📄 {resultado['output_file']}\n"
                        if resultado.get('objeciones_file'):
                            msg += f"📋 {resultado['objeciones_file']}\n"
                        msg += f"📊 {resumen['total_registros']} registros | {resumen['codigos_homologados']} homologados"
                        messages_view.set_processing(False, msg)
                        messages_view.processing_status.color = COLORS["success"]
                        
                        # Mostrar diálogo de procesamiento completado
                        output_files = [resultado['output_file']]
                        if resultado.get('objeciones_file'):
                            output_files.append(resultado['objeciones_file'])
                        
                        def open_output_folder():
                            import subprocess
                            output_dir = os.path.dirname(resultado['output_file'])
                            subprocess.Popen(f'explorer "{output_dir}"')
                        
                        AlertDialog.show_processing_complete(
                            page=page,
                            eps_name="MUTUALSER",
                            stats=resumen,
                            output_files=output_files,
                            on_open_folder=open_output_folder
                        )
                    else:
                        messages_view.set_processing(False, f"❌ Error: {resultado['message']}")
                        messages_view.processing_status.color = COLORS["error"]
                        
                        AlertDialog.show_error(
                            page=page,
                            title="Error al procesar",
                            message=f"No se pudo procesar los archivos:\n\n{resultado['message']}"
                        )
                    
                    messages_view.process_eps_btn.disabled = False
                
                elif eps_type == "coosalud":
                    from app.service.processors import CoosaludProcessor
                    
                    # Obtener archivos Excel (excluyendo devoluciones)
                    excel_files = email_service.get_excel_files(exclude_devoluciones=True)
                    if not excel_files:
                        messages_view.set_processing(False, "❌ No hay archivos Excel para procesar")
                        messages_view.process_eps_btn.disabled = False
                        
                        AlertDialog.show_warning(
                            page=page,
                            title="Sin archivos para procesar",
                            message="No se encontraron archivos Excel de GLOSAS.\n\nLos archivos de DEVOLUCIÓN fueron excluidos automáticamente."
                        )
                        return

                    print(f"[COOSALUD] Procesando {len(excel_files)} archivos Excel (devoluciones excluidas)")
                    messages_view.set_processing(True, f"📊 Procesando {len(excel_files)} archivo(s) Excel...")

                    # Configurar procesador con homologador de Coosalud
                    homologador_path = r"\\MINERVA\Cartera\GLOSAAP\HOMOLOGADOR\mutualser_homologacion.xlsx"
                    output_dir = r"\\MINERVA\Cartera\GLOSAAP\REPOSITORIO DE RESULTADOS\COOSALUD"
                    
                    processor = CoosaludProcessor(homologador_path=homologador_path)
                    result_data, message = processor.process_glosas(excel_files, output_dir=output_dir)
                    
                    if result_data:
                        messages_view.set_processing(False, f"✅ {message}")
                        messages_view.processing_status.color = COLORS["success"]
                        
                        AlertDialog.show_success(
                            page=page,
                            title="Procesamiento completado",
                            message=message
                        )
                    else:
                        messages_view.set_processing(False, f"❌ {message}")
                        messages_view.processing_status.color = COLORS["error"]
                        
                        AlertDialog.show_error(
                            page=page,
                            title="Error al procesar",
                            message=message
                        )
                    
            except Exception as ex:
                messages_view.set_processing(False, f"❌ Error: {str(ex)}")
                messages_view.processing_status.color = COLORS["error"]
                messages_view.process_eps_btn.disabled = False
                
                AlertDialog.show_error(
                    page=page,
                    title="Error en el procesamiento",
                    message=f"Ocurrió un error inesperado:\n\n{str(ex)}"
                )
        
        threading.Thread(target=worker, daemon=True).start()
    
    # ==================== CREAR VISTAS ====================
    
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
        assets_dir=ASSETS_DIR
    )
    
    homologacion_view = HomologacionView(
        page=page,
        on_back=go_to_tools
    )
    
    mix_excel_view = MixExcelView(
        page=page,
        on_back=go_to_tools
    )
    
    homologador_manual_view = HomologadorManualView(
        page=page,
        on_back=go_to_tools
    )
    
    messages_view = MessagesView(
        page=page,
        on_back=go_to_eps_selection,
        on_refresh=lambda: load_messages(messages_view.search_info_text.value),
        on_download_selected=download_selected_messages,
        on_process=process_eps_files
    )
    
    eps_screen = EpsScreen(
        page=page,
        on_eps_selected=on_eps_selected,
        on_logout=go_to_dashboard
    )
    
    # ==================== CONSTRUIR PÁGINA ====================
    
    page.add(
        ft.Stack([
            login_view.container,
            method_selection_view.container,
            dashboard_view.container,
            tools_view.container,
            homologacion_view.container,
            mix_excel_view.container,
            homologador_manual_view.container,
            web_download_view.container,
            eps_screen.build(),
            messages_view.container
        ], expand=True)
    )
    
    # ==================== AUTO-LOGIN ====================
    
    login_view.try_auto_login()


if __name__ == "__main__":
    ft.app(target=main)
