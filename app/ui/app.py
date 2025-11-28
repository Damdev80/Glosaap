"""
Aplicación Glosaap - Cliente IMAP con Flet
"""
import flet as ft
import os
import sys
import threading

# Configurar path para imports
PROJECT_APP_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_APP_DIR not in sys.path:
    sys.path.insert(0, PROJECT_APP_DIR)

from service.email_service import EmailService
from ui.styles import COLORS, FONT_SIZES, SPACING, WINDOW_SIZES
from ui.components.message_row import MessageRow
from ui.screens.eps_screen import EpsScreen


def main(page: ft.Page):
    """Función principal de la aplicación"""
    
    # ==================== CONFIGURACIÓN INICIAL ====================
    page.title = "Glosaap"
    page.window_width = WINDOW_SIZES["login"]["width"]
    page.window_height = WINDOW_SIZES["login"]["height"]
    page.bgcolor = COLORS["bg_white"]
    page.padding = 0
    
    # Estado de navegación actual
    current_view = {"name": "login"}
    
    # ==================== SERVICIOS ====================
    email_service = EmailService()
    
    # Estado global
    app_state = {
        "selected_eps": None,
        "date_from": None,
        "date_to": None,
        "dashboard_action": None  # "evitar", "manejar", "responder"
    }
    
    # ==================== DASHBOARD - 3 CARDS ====================
    
    def create_dashboard_card(icon, title, subtitle, color, action_key, image_path=None):
        """
        Crea una card del dashboard
        
        Para usar imagen personalizada en lugar de icono:
        - Crea carpeta 'assets/images/' en tu proyecto
        - Coloca tus imágenes ahí (ej: evitar.png, manejar.png, responder.png)
        - Pasa image_path="images/evitar.png"
        
        También puedes usar URL:
        - image_path="https://ejemplo.com/imagen.png"
        """
        
        # Decidir si usar imagen o icono
        if image_path:
            # OPCIÓN 1: Usar imagen personalizada
            visual_element = ft.Image(
                src=image_path,
                width=80,
                height=80,
                fit=ft.ImageFit.CONTAIN,
            )
        else:
            # OPCIÓN 2: Usar icono (por defecto)
            visual_element = ft.Container(
                content=ft.Icon(icon, size=50, color=COLORS["bg_white"]),
                width=80,
                height=80,
                border_radius=40,
                bgcolor=color,
                alignment=ft.alignment.center
            )
        
        def on_hover(e):
            card_container.scale = 1.03 if e.data == "true" else 1.0
            card_container.shadow = ft.BoxShadow(
                spread_radius=2 if e.data == "true" else 1,
                blur_radius=20 if e.data == "true" else 10,
                color=ft.Colors.with_opacity(0.2 if e.data == "true" else 0.1, color),
                offset=ft.Offset(0, 8 if e.data == "true" else 4)
            )
            page.update()
        
        def on_click(e):
            app_state["dashboard_action"] = action_key
            go_to_eps_selection()
        
        card_container = ft.Container(
            content=ft.Column([
                visual_element,
                ft.Container(height=15),
                ft.Text(
                    title,
                    size=20,
                    weight=ft.FontWeight.W_600,
                    color=COLORS["text_primary"],
                    text_align=ft.TextAlign.CENTER
                ),
                ft.Container(height=5),
                ft.Text(
                    subtitle,
                    size=12,
                    color=COLORS["text_secondary"],
                    text_align=ft.TextAlign.CENTER
                )
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, alignment=ft.MainAxisAlignment.CENTER),
            width=200,
            height=220,
            bgcolor=COLORS["bg_white"],
            border_radius=16,
            padding=25,
            shadow=ft.BoxShadow(
                spread_radius=1,
                blur_radius=10,
                color=ft.Colors.with_opacity(0.1, color),
                offset=ft.Offset(0, 4)
            ),
            border=ft.border.all(2, ft.Colors.with_opacity(0.3, color)),
            animate=ft.Animation(200, ft.AnimationCurve.EASE_OUT),
            animate_scale=ft.Animation(200, ft.AnimationCurve.EASE_OUT),
            scale=1.0,
            on_hover=on_hover,
            on_click=on_click,
            ink=True
        )
        
        return card_container
    
    # Crear las 3 cards del dashboard
    card_evitar = create_dashboard_card(
        icon=ft.Icons.SHIELD_OUTLINED,
        title="Evitar Glosa",
        subtitle="Prevención y validación\nantes de facturar",
        color="#4CAF50",  # Verde
        action_key="evitar",
        # Para imagen: image_path="images/evitar.png"
    )
    
    card_manejar = create_dashboard_card(
        icon=ft.Icons.BUILD_OUTLINED,
        title="Manejar Glosa",
        subtitle="Gestión y seguimiento\nde glosas activas",
        color="#FF9800",  # Naranja
        action_key="manejar",
        # Para imagen: image_path="images/manejar.png"
    )
    
    card_responder = create_dashboard_card(
        icon=ft.Icons.REPLY_ALL_OUTLINED,
        title="Responder Glosa",
        subtitle="Respuesta a objeciones\ny documentación",
        color="#2196F3",  # Azul
        action_key="responder",
        # Para imagen: image_path="images/responder.png"
    )
    
    # Vista del Dashboard
    dashboard_view = ft.Container(
        content=ft.Column([
            ft.Container(height=40),
            # Header
            ft.Column([
                ft.Text(
                    "Glosaap",
                    size=36,
                    weight=ft.FontWeight.W_300,
                    color=COLORS["text_primary"]
                ),
                ft.Text(
                    "Sistema de Gestión de Glosas",
                    size=14,
                    color=COLORS["text_secondary"]
                ),
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
            ft.Container(height=40),
            # Cards
            ft.Row([
                card_evitar,
                card_manejar,
                card_responder
            ], alignment=ft.MainAxisAlignment.CENTER, spacing=30),
            ft.Container(height=30),
            # Info de usuario
            ft.Container(
                content=ft.Row([
                    ft.Icon(ft.Icons.PERSON_OUTLINE, size=16, color=COLORS["text_secondary"]),
                    ft.Text(
                        "Sesión activa",
                        size=12,
                        color=COLORS["text_secondary"]
                    ),
                    ft.Container(width=20),
                    ft.TextButton(
                        "Cerrar sesión",
                        on_click=lambda e: go_to_login(),
                        style=ft.ButtonStyle(color=COLORS["error"])
                    )
                ], alignment=ft.MainAxisAlignment.CENTER),
                padding=10
            )
        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
        bgcolor=COLORS["bg_light"],
        expand=True,
        alignment=ft.alignment.center,
        visible=False
    )
    
    # ==================== PANTALLA DE LOGIN ====================
    
    email_input = ft.TextField(
        label="Correo electrónico",
        width=380,
        autofocus=True,
        border_color=COLORS["border"],
        focused_border_color=COLORS["primary"],
        bgcolor=COLORS["bg_input"],
        color=COLORS["text_primary"],
        cursor_color=COLORS["primary"],
        text_size=FONT_SIZES["body"]
    )
    
    password_input = ft.TextField(
        label="Contraseña",
        password=True,
        can_reveal_password=True,
        width=380,
        border_color=COLORS["border"],
        focused_border_color=COLORS["primary"],
        bgcolor=COLORS["bg_input"],
        color=COLORS["text_primary"],
        cursor_color=COLORS["primary"],
        text_size=FONT_SIZES["body"]
    )
    
    server_input = ft.TextField(
        label="Servidor IMAP",
        hint_text="Ej: imap.gmail.com, mail.tudominio.com",
        width=380,
        border_color=COLORS["border"],
        focused_border_color=COLORS["primary"],
        bgcolor=COLORS["bg_input"],
        color=COLORS["text_primary"],
        cursor_color=COLORS["primary"],
        text_size=FONT_SIZES["body"]
    )
    
    status_text = ft.Text("", size=FONT_SIZES["small"], color=COLORS["error"])
    login_progress = ft.ProgressBar(visible=False, color=COLORS["primary"], bgcolor=COLORS["border"], width=380)
    
    login_button = ft.Container(
        content=ft.Text("Iniciar Sesión", size=15, weight=ft.FontWeight.W_500, color=COLORS["bg_white"]),
        alignment=ft.alignment.center,
        bgcolor=COLORS["primary"],
        border_radius=8,
        padding=15,
        width=380,
        ink=True
    )
    
    login_view = ft.Container(
        content=ft.Column([
            ft.Container(height=SPACING["xxl"]),
            ft.Container(
                content=ft.Column([
                    ft.Text("Glosaap", size=FONT_SIZES["title"], weight=ft.FontWeight.W_300, color=COLORS["text_primary"]),
                    ft.Text("Gestor de correos IMAP", size=12, color=COLORS["text_secondary"]),
                    ft.Container(height=SPACING["lg"]),
                    email_input,
                    ft.Container(height=SPACING["md"]),
                    password_input,
                    ft.Container(height=SPACING["md"]),
                    server_input,
                    ft.Container(height=SPACING["lg"]),
                    login_button,
                    ft.Container(height=SPACING["sm"]),
                    login_progress,
                    status_text
                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                padding=ft.padding.all(SPACING["xxl"]),
                bgcolor=COLORS["bg_white"],
                border_radius=12,
                shadow=ft.BoxShadow(spread_radius=1, blur_radius=15, color=ft.Colors.with_opacity(0.1, COLORS["text_primary"]), offset=ft.Offset(0, 4))
            ),
        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
        padding=ft.padding.symmetric(horizontal=SPACING["xxl"]),
        bgcolor=COLORS["bg_light"],
        alignment=ft.alignment.center,
        expand=True
    )
    
    # ==================== PANTALLA DE MENSAJES ====================
    
    messages_list = ft.Column([], scroll=ft.ScrollMode.AUTO, expand=True, spacing=0)
    messages_status = ft.Text("", size=FONT_SIZES["small"], color=COLORS["text_secondary"])
    loading_bar = ft.ProgressBar(visible=False, color=COLORS["primary"], bgcolor=COLORS["border"])
    processing_bar = ft.ProgressBar(visible=False, color=COLORS["success"], bgcolor=COLORS["border"])
    processing_status = ft.Text("", size=FONT_SIZES["small"], color=COLORS["text_secondary"])
    
    # Info de búsqueda actual
    search_info_text = ft.Text("", size=12, color=COLORS["text_secondary"])
    
    # Contenedor para el botón de procesamiento (se actualiza según la EPS seleccionada)
    process_eps_btn = ft.ElevatedButton(
        "📊 Procesar",
        icon=ft.Icons.TABLE_CHART,
        bgcolor=COLORS["primary"],
        color=COLORS["bg_white"],
        visible=False
    )
    
    messages_view = ft.Column([
        # Header
        ft.Container(
            content=ft.Row([
                ft.Row([
                    ft.IconButton(icon=ft.Icons.ARROW_BACK, icon_color=COLORS["text_secondary"], tooltip="Volver"),
                    ft.Text("Correos con 'glosa'", size=FONT_SIZES["heading"], weight=ft.FontWeight.W_400, color=COLORS["text_primary"]),
                ], spacing=0),
                ft.IconButton(icon=ft.Icons.REFRESH, icon_color=COLORS["primary"], tooltip="Actualizar")
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            bgcolor=COLORS["bg_white"],
            padding=SPACING["lg"],
            border=ft.border.only(bottom=ft.BorderSide(1, COLORS["border"]))
        ),
        # Info de búsqueda
        ft.Container(
            content=ft.Row([
                ft.Icon(ft.Icons.INFO_OUTLINE, size=14, color=COLORS["primary"]),
                search_info_text
            ], spacing=8, alignment=ft.MainAxisAlignment.CENTER),
            padding=ft.padding.symmetric(horizontal=SPACING["md"], vertical=8),
            bgcolor=COLORS["bg_input"]
        ),
        loading_bar,
        ft.Container(content=messages_list, expand=True, padding=0, bgcolor=COLORS["bg_light"]),
        # Procesamiento
        ft.Container(
            content=ft.Column([
                ft.Row([process_eps_btn], spacing=SPACING["md"], alignment=ft.MainAxisAlignment.CENTER),
                processing_bar,
                processing_status
            ], spacing=SPACING["sm"]),
            padding=SPACING["md"],
            bgcolor=COLORS["bg_white"],
            border=ft.border.only(top=ft.BorderSide(1, COLORS["border"]))
        ),
        ft.Container(content=messages_status, padding=SPACING["md"], bgcolor=COLORS["bg_white"])
    ], expand=True, spacing=0, visible=False)
    
    # ==================== FUNCIONES DE NAVEGACIÓN ====================
    
    def go_to_login():
        """Navega a la pantalla de login"""
        current_view["name"] = "login"
        login_view.visible = True
        dashboard_view.visible = False
        eps_screen.hide()
        messages_view.visible = False
        page.window_width = WINDOW_SIZES["login"]["width"]
        page.window_height = WINDOW_SIZES["login"]["height"]
        page.update()
    
    def go_to_dashboard():
        """Navega al dashboard principal"""
        current_view["name"] = "dashboard"
        login_view.visible = False
        dashboard_view.visible = True
        eps_screen.hide()
        messages_view.visible = False
        page.window_width = 800
        page.window_height = 500
        page.update()
    
    def go_to_eps_selection():
        """Navega a la pantalla de selección de EPS"""
        current_view["name"] = "eps"
        login_view.visible = False
        dashboard_view.visible = False
        eps_screen.show()
        messages_view.visible = False
        page.window_width = WINDOW_SIZES["main"]["width"]
        page.window_height = WINDOW_SIZES["main"]["height"]
        page.update()
    
    def go_to_messages():
        """Navega a la pantalla de mensajes"""
        current_view["name"] = "messages"
        login_view.visible = False
        dashboard_view.visible = False
        eps_screen.hide()
        messages_view.visible = True
        page.update()
    
    def go_back():
        """Navega hacia atrás según la vista actual"""
        if current_view["name"] == "messages":
            go_to_eps_selection()
        elif current_view["name"] == "eps":
            go_to_dashboard()
        elif current_view["name"] == "dashboard":
            go_to_login()
    
    # ==================== FUNCIONES DE NEGOCIO ====================
    
    def show_status(msg, is_error=False):
        """Muestra mensaje de estado en login"""
        status_text.value = msg
        status_text.color = COLORS["error"] if is_error else COLORS["primary"]
        page.update()
    
    def handle_login(e):
        """Maneja el proceso de login"""
        email = email_input.value.strip()
        password = password_input.value
        server = server_input.value.strip()
        
        if not email or not password:
            show_status("Por favor ingresa correo y contraseña", True)
            return
        
        # Auto-detectar servidor si no se especifica
        if not server:
            if "gmail" in email.lower():
                server = "imap.gmail.com"
            elif "outlook" in email.lower() or "hotmail" in email.lower():
                server = "imap-mail.outlook.com"
            elif "yahoo" in email.lower():
                server = "imap.mail.yahoo.com"
            else:
                domain = email.split("@")[1] if "@" in email else ""
                server = f"mail.{domain}" if domain else "imap.gmail.com"
        
        def connect_worker():
            try:
                login_progress.visible = True
                login_button.disabled = True
                show_status("Conectando...")
                page.update()
                
                email_service.connect(email, password, server)
                
                login_progress.visible = False
                login_button.disabled = False
                show_status("¡Conexión exitosa!")
                page.update()
                
                # Navegar al dashboard
                go_to_dashboard()
                
            except Exception as ex:
                login_progress.visible = False
                login_button.disabled = False
                show_status(f"Error: {str(ex)}", True)
                page.update()
        
        threading.Thread(target=connect_worker, daemon=True).start()
    
    def on_eps_selected(eps_info, date_from, date_to):
        """Callback cuando se selecciona una EPS"""
        app_state["selected_eps"] = eps_info
        app_state["date_from"] = date_from
        app_state["date_to"] = date_to
        
        # Actualizar info de búsqueda
        eps_name = eps_info["name"]
        date_info = ""
        if date_from and date_to:
            date_info = f" | {date_from.strftime('%d/%m/%Y')} - {date_to.strftime('%d/%m/%Y')}"
        elif date_from:
            date_info = f" | Desde {date_from.strftime('%d/%m/%Y')}"
        elif date_to:
            date_info = f" | Hasta {date_to.strftime('%d/%m/%Y')}"
        
        search_info_text.value = f"EPS: {eps_name}{date_info}"
        
        # Configurar botón de procesamiento según la EPS
        eps_filter = eps_info.get("filter", "").lower()
        if eps_filter == "mutualser":
            process_eps_btn.text = "📊 Procesar MUTUALSER"
            process_eps_btn.bgcolor = COLORS["primary"]
            process_eps_btn.visible = True
            process_eps_btn.data = "mutualser"
        elif eps_filter == "cosalud":
            process_eps_btn.text = "📊 Procesar COSALUD"
            process_eps_btn.bgcolor = COLORS["success"]
            process_eps_btn.visible = True
            process_eps_btn.data = "cosalud"
        else:
            # Para otras EPS o "Todas", ocultar el botón
            process_eps_btn.visible = False
        
        # Navegar y cargar mensajes
        go_to_messages()
        load_messages()
    
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
    
    def load_messages():
        """Carga mensajes del servidor"""
        def worker():
            try:
                loading_bar.visible = True
                messages_list.controls.clear()
                messages_status.value = "🔍 Buscando correos..."
                page.update()
                
                message_rows = []
                
                def on_found(msg):
                    msg_row = MessageRow(msg, len(message_rows) + 1)
                    messages_list.controls.append(msg_row.build())
                    message_rows.append(msg_row)
                    messages_status.value = f"🔍 Encontrados {len(message_rows)} correo(s)..."
                    page.update()
                
                # Buscar con filtro de fechas
                all_msgs = email_service.search_messages(
                    "glosa",
                    limit=100,
                    timeout=15,
                    on_found=on_found,
                    date_from=app_state.get("date_from"),
                    date_to=app_state.get("date_to")
                )
                
                # Filtrar por EPS
                msgs = filter_messages_by_eps(all_msgs)
                
                # Actualizar lista con mensajes filtrados
                messages_list.controls.clear()
                message_rows.clear()
                
                if msgs:
                    for i, msg in enumerate(msgs):
                        msg_row = MessageRow(msg, i + 1)
                        messages_list.controls.append(msg_row.build())
                        message_rows.append(msg_row)
                    
                    messages_status.value = f"✅ {len(msgs)} correo(s) encontrados"
                else:
                    messages_list.controls.append(
                        ft.Container(
                            content=ft.Column([
                                ft.Icon(ft.Icons.MAIL_OUTLINE, size=60, color=COLORS["text_light"]),
                                ft.Text("No se encontraron correos", size=FONT_SIZES["body"], color=COLORS["text_secondary"])
                            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=15),
                            alignment=ft.alignment.center,
                            expand=True
                        )
                    )
                    messages_status.value = "No hay resultados"
                
                loading_bar.visible = False
                
                # Descargar adjuntos si hay mensajes
                if msgs:
                    messages_status.value = "📥 Descargando adjuntos..."
                    page.update()
                    
                    email_service.download_all_attachments(msgs)
                    messages_status.value = f"✅ {len(msgs)} correo(s) - Adjuntos descargados"
                
                page.update()
                
            except Exception as ex:
                loading_bar.visible = False
                messages_status.value = f"❌ Error: {str(ex)}"
                page.update()
        
        threading.Thread(target=worker, daemon=True).start()
    
    def process_eps_files(eps_type):
        """Procesa archivos de una EPS"""
        def worker():
            try:
                processing_bar.visible = True
                process_eps_btn.disabled = True
                processing_status.value = f"🔄 Procesando {eps_type.upper()}..."
                page.update()
                
                if eps_type == "mutualser":
                    excel_files = email_service.get_excel_files()
                    
                    if not excel_files:
                        processing_status.value = "⚠️ No hay archivos Excel"
                        processing_bar.visible = False
                        process_eps_btn.disabled = False
                        page.update()
                        return
                    
                    processing_status.value = f"📊 Procesando {len(excel_files)} archivo(s)..."
                    page.update()
                    
                    resultado = email_service.procesar_mutualser()
                    
                    processing_bar.visible = False
                    
                    if resultado['success']:
                        resumen = resultado['resumen']
                        msg = f"✅ ¡Archivos generados!\n"
                        msg += f"📄 {resultado['output_file']}\n"
                        if resultado.get('objeciones_file'):
                            msg += f"📋 {resultado['objeciones_file']}\n"
                        msg += f"📊 {resumen['total_registros']} registros | {resumen['codigos_homologados']} homologados"
                        processing_status.value = msg
                        processing_status.color = COLORS["success"]
                        
                        # Abrir carpeta
                        import subprocess
                        output_dir = os.path.dirname(resultado['output_file'])
                        subprocess.Popen(f'explorer "{output_dir}"')
                    else:
                        processing_status.value = f"❌ Error: {resultado['message']}"
                        processing_status.color = COLORS["error"]
                    
                    process_eps_btn.disabled = False
                    page.update()
                
                elif eps_type == "cosalud":
                    # TODO: Implementar procesamiento de COSALUD
                    processing_status.value = "⚠️ Procesador de COSALUD pendiente de implementar"
                    processing_bar.visible = False
                    process_eps_btn.disabled = False
                    page.update()
                    
            except Exception as ex:
                processing_bar.visible = False
                processing_status.value = f"❌ Error: {str(ex)}"
                processing_status.color = COLORS["error"]
                process_eps_btn.disabled = False
                page.update()
        
        threading.Thread(target=worker, daemon=True).start()
    
    def on_process_btn_click(e):
        """Maneja el click en el botón de procesamiento"""
        eps_type = process_eps_btn.data
        if eps_type:
            process_eps_files(eps_type)
    
    # ==================== PANTALLA EPS (MODULAR) ====================
    
    eps_screen = EpsScreen(
        page=page,
        on_eps_selected=on_eps_selected,
        on_logout=go_to_dashboard  # Volver al dashboard
    )
    
    # ==================== CONECTAR EVENTOS ====================
    
    login_button.on_click = handle_login
    process_eps_btn.on_click = on_process_btn_click
    
    # Botón volver en mensajes
    messages_view.controls[0].content.controls[0].controls[0].on_click = lambda e: go_to_eps_selection()
    # Botón refresh en mensajes
    messages_view.controls[0].content.controls[1].on_click = lambda e: load_messages()
    
    # ==================== CONSTRUIR PÁGINA ====================
    
    page.add(
        ft.Stack([
            login_view,
            dashboard_view,
            eps_screen.build(),
            messages_view
        ], expand=True)
    )


if __name__ == "__main__":
    ft.app(target=main)
