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
        tools_view.hide()
        eps_screen.hide()
        messages_view.hide()
        page.window_width = WINDOW_SIZES["login"]["width"]
        page.window_height = WINDOW_SIZES["login"]["height"]
        page.update()
    
    def go_to_dashboard():
        """Navega al dashboard principal"""
        current_view["name"] = "dashboard"
        login_view.hide()
        dashboard_view.show()
        tools_view.hide()
        eps_screen.hide()
        messages_view.hide()
        page.window_width = 800
        page.window_height = 550
        page.update()
    
    def go_to_tools():
        """Navega a la pantalla de herramientas"""
        current_view["name"] = "tools"
        login_view.hide()
        dashboard_view.hide()
        tools_view.show()
        eps_screen.hide()
        messages_view.hide()
        page.window_width = 800
        page.window_height = 500
        page.update()
    
    def go_to_eps_selection():
        """Navega a la pantalla de selección de EPS"""
        current_view["name"] = "eps"
        login_view.hide()
        dashboard_view.hide()
        tools_view.hide()
        eps_screen.show()
        messages_view.hide()
        page.window_width = WINDOW_SIZES["main"]["width"]
        page.window_height = WINDOW_SIZES["main"]["height"]
        page.update()
    
    def go_to_messages():
        """Navega a la pantalla de mensajes"""
        current_view["name"] = "messages"
        login_view.hide()
        dashboard_view.hide()
        tools_view.hide()
        eps_screen.hide()
        messages_view.show()
        page.update()
    
    def go_back():
        """Navega hacia atrás según la vista actual"""
        if current_view["name"] == "messages":
            go_to_eps_selection()
        elif current_view["name"] == "eps":
            go_to_dashboard()
        elif current_view["name"] == "tools":
            go_to_dashboard()
        elif current_view["name"] == "dashboard":
            go_to_login()
    
    # ==================== FUNCIONES DE NEGOCIO ====================
    
    def handle_login_success():
        """Callback cuando el login es exitoso"""
        go_to_dashboard()
    
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
                        filtered.append(msg)
            elif filter_type == "email":
                if filter_value in from_addr:
                    filtered.append(msg)
        
        return filtered
    
    def load_messages(search_info=""):
        """Carga mensajes del servidor"""
        def worker():
            try:
                messages_view.set_loading(True, "🔍 Buscando correos...")
                
                all_msgs = []
                
                def on_found(msg):
                    all_msgs.append(msg)
                    messages_view.set_loading(True, f"🔍 Encontrados {len(all_msgs)} correo(s)...")
                
                # Buscar con filtro de fechas
                email_service.search_messages(
                    "glosa",
                    limit=100,
                    timeout=15,
                    on_found=on_found,
                    date_from=app_state.get("date_from"),
                    date_to=app_state.get("date_to")
                )
                
                # Filtrar por EPS
                msgs = filter_messages_by_eps(all_msgs)
                app_state["found_messages"] = msgs
                
                # Mostrar mensajes
                messages_view.show_messages(msgs, search_info)
                messages_view.show_download_controls(True)
                
                if msgs:
                    messages_view.set_loading(False, f"✅ {len(msgs)} correo(s) encontrados - Selecciona para descargar")
                else:
                    messages_view.set_loading(False, "No hay resultados")
                    messages_view.show_download_controls(False)
                
            except Exception as ex:
                messages_view.set_loading(False, f"❌ Error: {str(ex)}")
        
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
                    
                    if not excel_files:
                        messages_view.set_processing(False, "⚠️ No hay archivos Excel")
                        messages_view.process_eps_btn.disabled = False
                        return
                    
                    messages_view.set_processing(True, f"📊 Procesando {len(excel_files)} archivo(s)...")
                    
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
                        
                        # Abrir carpeta
                        import subprocess
                        output_dir = os.path.dirname(resultado['output_file'])
                        subprocess.Popen(f'explorer "{output_dir}"')
                    else:
                        messages_view.set_processing(False, f"❌ Error: {resultado['message']}")
                        messages_view.processing_status.color = COLORS["error"]
                    
                    messages_view.process_eps_btn.disabled = False
                
                elif eps_type == "coosalud":
                    messages_view.set_processing(False, "⚠️ Procesador de COOSALUD pendiente de implementar")
                    messages_view.process_eps_btn.disabled = False
                    
            except Exception as ex:
                messages_view.set_processing(False, f"❌ Error: {str(ex)}")
                messages_view.processing_status.color = COLORS["error"]
                messages_view.process_eps_btn.disabled = False
        
        threading.Thread(target=worker, daemon=True).start()
    
    # ==================== CREAR VISTAS ====================
    
    login_view = LoginView(
        page=page,
        email_service=email_service,
        on_login_success=handle_login_success
    )
    
    dashboard_view = DashboardView(
        page=page,
        assets_dir=ASSETS_DIR,
        on_card_click=on_dashboard_action,
        on_tools_click=go_to_tools,
        on_logout=lambda: go_to_login(logout=True)
    )
    
    tools_view = ToolsView(
        page=page,
        assets_dir=ASSETS_DIR,
        on_back=go_to_dashboard
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
            dashboard_view.container,
            tools_view.container,
            eps_screen.build(),
            messages_view.container
        ], expand=True)
    )
    
    # ==================== AUTO-LOGIN ====================
    
    login_view.try_auto_login()


if __name__ == "__main__":
    ft.app(target=main)
