"""
Aplicación Glosaap - Cliente IMAP con Flet
Versión modular con separación de responsabilidades
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


def main(page: ft.Page):
    """Función principal de la aplicación"""
    
    # Configuración inicial
    page.title = "Glosaap"
    page.window_width = WINDOW_SIZES["login"]["width"]
    page.window_height = WINDOW_SIZES["login"]["height"]
    page.bgcolor = COLORS["bg_white"]
    page.padding = 0
    
    # Servicios
    email_service = EmailService()
    selected_eps = {"name": "Todas las EPS", "filter": None}  # EPS seleccionada

    
    
    # ==================== PANTALLA DE LOGIN ====================
    
    title = ft.Text(
        "Glosaap",
        size=FONT_SIZES["title"],
        weight=ft.FontWeight.W_300,
        color=COLORS["text_primary"],
        text_align=ft.TextAlign.CENTER
    )
    
    subtitle = ft.Text(
        "Gestor de correos IMAP | Soporta Gmail, Outlook, dominios personalizados",
        size=12,
        color=COLORS["text_secondary"],
        text_align=ft.TextAlign.CENTER
    )
    
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
    
    # Campo para servidor IMAP personalizado (ahora visible por defecto)
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
    
    status_text = ft.Text(
        "",
        size=FONT_SIZES["small"],
        color=COLORS["error"],
        text_align=ft.TextAlign.CENTER,
        weight=ft.FontWeight.W_400
    )
    
    login_progress = ft.ProgressBar(
        visible=False, 
        color=COLORS["primary"], 
        bgcolor=COLORS["border"], 
        width=380
    )
    
    login_button = ft.Container(
        content=ft.Text("Iniciar Sesión", size=15, weight=ft.FontWeight.W_500),
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
            # Card contenedor del formulario
            ft.Container(
                content=ft.Column([
                    title,
                    subtitle,
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
                shadow=ft.BoxShadow(
                    spread_radius=1,
                    blur_radius=15,
                    color=ft.Colors.with_opacity(0.1, COLORS["text_primary"]),
                    offset=ft.Offset(0, 4)
                )
            ),
            ft.Container(height=SPACING["xxl"]),
        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
        padding=ft.padding.symmetric(horizontal=SPACING["xxl"]),
        bgcolor=COLORS["bg_light"],
        alignment=ft.alignment.center,
        expand=True
    )
    
    # ==================== PANTALLA DE SELECCIÓN DE EPS ====================
    
    # Lista de EPS disponibles (puedes agregar más después)
    eps_list = [
        {"name": "Todas las EPS", "icon": "", "description": "Buscar en todas las EPS", "filter": None},
        {"name": "Sanitas", "icon": "🟢", "description": "Sanitas EPS", "filter": "sanitas"},
        {"name": "Sura", "icon": "🔵", "description": "Sura EPS", "filter": "sura"},
        {"name": "Nueva EPS", "icon": "🟠", "description": "Nueva EPS", "filter": "nuevaeps"},
        {"name": "Compensar", "icon": "🟡", "description": "Compensar EPS", "filter": "compensar"},
        {"name": "Famisanar", "icon": "🟣", "description": "Famisanar EPS", "filter": "famisanar"},
    ]
    
    def create_eps_card(eps_info):
        """Crea una tarjeta para cada EPS"""
        def on_click(e):
            selected_eps["name"] = eps_info["name"]
            selected_eps["filter"] = eps_info["filter"]
            
            # Cambiar a pantalla de mensajes
            eps_view.visible = False
            messages_view.visible = True
            page.update()
            
            # Cargar mensajes
            load_messages()
        
        return ft.Container(
            content=ft.Column([
                ft.Text(eps_info["icon"], size=40),
                ft.Text(
                    eps_info["name"],
                    size=FONT_SIZES["body"],
                    weight=ft.FontWeight.W_500,
                    color=COLORS["text_primary"],
                    text_align=ft.TextAlign.CENTER
                ),
                ft.Text(
                    eps_info["description"],
                    size=FONT_SIZES["small"],
                    color=COLORS["text_secondary"],
                    text_align=ft.TextAlign.CENTER
                )
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=8),
            bgcolor=COLORS["bg_white"],
            border_radius=12,
            padding=SPACING["lg"],
            width=160,
            height=140,
            ink=True,
            on_click=on_click,
            shadow=ft.BoxShadow(
                spread_radius=0,
                blur_radius=8,
                color=ft.Colors.with_opacity(0.08, COLORS["text_primary"]),
                offset=ft.Offset(0, 2)
            ),
            border=ft.border.all(1, COLORS["border"])
        )
    
    # Crear grid de EPSs
    eps_grid = ft.Row(
        [
            create_eps_card(eps) for eps in eps_list
        ],
        wrap=True,
        spacing=SPACING["md"],
        run_spacing=SPACING["md"],
        alignment=ft.MainAxisAlignment.CENTER
    )
    
    eps_view = ft.Container(
        content=ft.Column([
            ft.Container(height=SPACING["xl"]),
            ft.Text(
                "Selecciona una EPS",
                size=FONT_SIZES["title"],
                weight=ft.FontWeight.W_300,
                color=COLORS["text_primary"],
                text_align=ft.TextAlign.CENTER
            ),
            ft.Text(
                "Filtra los correos por entidad prestadora de salud",
                size=FONT_SIZES["small"],
                color=COLORS["text_secondary"],
                text_align=ft.TextAlign.CENTER
            ),
            ft.Container(height=SPACING["xl"]),
            ft.Container(
                content=eps_grid,
                padding=SPACING["lg"],
                bgcolor=COLORS["bg_light"],
                border_radius=12,
                shadow=ft.BoxShadow(
                    spread_radius=1,
                    blur_radius=15,
                    color=ft.Colors.with_opacity(0.05, COLORS["text_primary"]),
                    offset=ft.Offset(0, 4)
                )
            ),
            ft.Container(height=SPACING["md"]),
            ft.TextButton(
                "← Cerrar sesión",
                icon=ft.Icons.LOGOUT,
                on_click=lambda e: go_to_login(),
                style=ft.ButtonStyle(color=COLORS["text_secondary"])
            )
        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
        padding=ft.padding.all(SPACING["xxl"]),
        bgcolor=COLORS["bg_light"],
        alignment=ft.alignment.center,
        expand=True,
        visible=False
    )
    
    # ==================== PANTALLA DE MENSAJES ====================
    
    messages_list = ft.Column([], scroll=ft.ScrollMode.AUTO, expand=True, spacing=0)
    messages_status = ft.Text("", size=FONT_SIZES["small"], color=COLORS["text_secondary"])
    loading_bar = ft.ProgressBar(visible=False, color=COLORS["primary"], bgcolor=COLORS["border"])
    
    messages_view = ft.Column([
        # Header
        ft.Container(
            content=ft.Row([
                ft.Row([
                    ft.IconButton(
                        icon=ft.Icons.ARROW_BACK,
                        icon_color=COLORS["text_secondary"],
                        tooltip="Volver a EPS",
                        on_click=lambda e: go_to_eps_selection()
                    ),
                    ft.Text(
                        "Correos con 'glosa'",
                        size=FONT_SIZES["heading"],
                        weight=ft.FontWeight.W_400,
                        color=COLORS["text_primary"]
                    ),
                ], spacing=0),
                ft.IconButton(
                    icon=ft.Icons.REFRESH,
                    icon_color=COLORS["primary"],
                    tooltip="Actualizar",
                    on_click=lambda e: load_messages()
                )
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            bgcolor=COLORS["bg_white"],
            padding=SPACING["lg"],
            border=ft.border.only(bottom=ft.BorderSide(1, COLORS["border"]))
        ),
        loading_bar,
        ft.Container(
            content=messages_list,
            expand=True,
            padding=0,
            bgcolor=COLORS["bg_light"]
        ),
        ft.Container(
            content=messages_status,
            padding=SPACING["md"],
            bgcolor=COLORS["bg_white"],
            border=ft.border.only(top=ft.BorderSide(1, COLORS["border"]))
        )
    ], expand=True, spacing=0, visible=False)
    
    # ==================== FUNCIONES ====================
    
    def show_status(msg, is_error=False):
        """Muestra mensaje de estado en login"""
        status_text.value = msg
        status_text.color = COLORS["error"] if is_error else COLORS["primary"]
        page.update()
    
    def show_messages_status(msg):
        """Muestra mensaje de estado en pantalla de mensajes"""
        messages_status.value = msg
        page.update()
    
    def go_to_login():
        """Vuelve a la pantalla de login"""
        eps_view.visible = False
        messages_view.visible = False
        login_view.visible = True
        email_service.disconnect()
        page.window_width = WINDOW_SIZES["login"]["width"]
        page.window_height = WINDOW_SIZES["login"]["height"]
        page.update()
    
    def go_to_eps_selection():
        """Vuelve a la pantalla de selección de EPS"""
        messages_view.visible = False
        eps_view.visible = True
        page.update()
    
    def filter_messages_by_eps(messages):
        """Filtra mensajes según la EPS seleccionada"""
        if not selected_eps["filter"]:
            return messages  # Todas las EPS
        
        filtered = []
        filter_keyword = selected_eps["filter"].lower()
        
        for msg in messages:
            # Buscar en remitente y asunto
            from_addr = msg.get("from", "").lower()
            subject = msg.get("subject", "").lower()
            
            if filter_keyword in from_addr or filter_keyword in subject:
                filtered.append(msg)
        
        return filtered
    
    def load_messages():
        """Carga mensajes con 'glosa' y descarga adjuntos"""
        def worker():
            try:
                loading_bar.visible = True
                messages_list.controls.clear()
                show_messages_status("🔍 Buscando correos con 'glosa' en el asunto...")
                page.update()
                
                message_rows = []
                
                def on_message_found(msg):
                    """Callback cuando se encuentra un mensaje"""
                    msg_row = MessageRow(msg, len(message_rows) + 1)
                    messages_list.controls.append(msg_row.build())
                    message_rows.append(msg_row)
                    show_messages_status(f"🔍 Encontrados {len(message_rows)} correo(s)...")
                    page.update()
                
                # Buscar mensajes
                all_msgs = email_service.search_messages("glosa", limit=100, timeout=15, on_found=on_message_found)
                
                # Filtrar por EPS seleccionada
                msgs = filter_messages_by_eps(all_msgs)
                
                # Actualizar UI con mensajes filtrados
                if len(msgs) < len(all_msgs):
                    messages_list.controls.clear()
                    message_rows.clear()
                    for i, msg in enumerate(msgs):
                        msg_row = MessageRow(msg, i + 1)
                        messages_list.controls.append(msg_row.build())
                        message_rows.append(msg_row)
                    show_messages_status(f"🔍 Filtrados {len(msgs)} de {len(all_msgs)} correo(s) para {selected_eps['name']}")
                    page.update()
                
                if not msgs:
                    messages_list.controls.clear()
                    messages_list.controls.append(
                        ft.Container(
                            content=ft.Column([
                                ft.Icon(ft.Icons.MAIL_OUTLINE, size=60, color=COLORS["text_light"]),
                                ft.Text(
                                    "No se encontraron correos con 'glosa' en el asunto",
                                    size=FONT_SIZES["body"],
                                    color=COLORS["text_secondary"],
                                    text_align=ft.TextAlign.CENTER
                                )
                            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=15),
                            alignment=ft.alignment.center,
                            expand=True
                        )
                    )
                    loading_bar.visible = False
                    page.update()
                    return
                
                # Descargar adjuntos con callback de progreso
                show_messages_status("📥 Descargando adjuntos...")
                page.update()
                
                def on_download_progress(idx, total, msg, files):
                    """Callback de progreso de descarga"""
                    msg_row = message_rows[idx]
                    msg_row.show_downloading()
                    page.update()
                    
                    if files:
                        msg_row.show_success(files)
                    else:
                        msg_row.show_no_attachments()
                    
                    show_messages_status(f"📥 Procesado: {idx + 1}/{total} correos")
                    page.update()
                
                stats = email_service.download_all_attachments(msgs, on_download_progress)
                
                # Resumen final
                if stats["total_files"] > 0:
                    show_messages_status(
                        f"✅ {len(msgs)} correo(s) | "
                        f"📎 {stats['total_files']} adjunto(s) descargado(s)"
                    )
                else:
                    show_messages_status(f"✅ {len(msgs)} correo(s) encontrado(s) | ⚠ Sin adjuntos")
                
                loading_bar.visible = False
                page.update()
                
            except Exception as e:
                loading_bar.visible = False
                show_messages_status(f"❌ Error: {str(e)}")
                page.update()
        
        threading.Thread(target=worker, daemon=True).start()
    
    def do_login(e):
        """Procesa el login"""
        email = email_input.value
        password = password_input.value
        custom_server = server_input.value.strip() if server_input.value else None
        
        if not email or not password:
            show_status("Por favor ingresa email y contraseña", True)
            return
        
        login_button.disabled = True
        login_progress.visible = True
        status_text.value = ""
        page.update()
        
        def worker():
            try:
                # Si hay servidor personalizado, usarlo directamente
                if custom_server:
                    server = custom_server
                    show_status(f"Conectando a {server}...")
                    page.update()
                else:
                    # Detectar por dominio del email
                    domain = email.split("@")[1].lower()
                    
                    # Servidores comunes
                    imap_servers = {
                        "gmail.com": "imap.gmail.com",
                        "outlook.com": "outlook.office365.com",
                        "hotmail.com": "outlook.office365.com",
                        "yahoo.com": "imap.mail.yahoo.com",
                        "icloud.com": "imap.mail.me.com",
                    }
                    
                    if domain in imap_servers:
                        server = imap_servers[domain]
                        show_status(f"Conectando a {server}...")
                    else:
                        # Intentar patrones comunes para dominios personalizados
                        possible_servers = [
                            f"imap.{domain}",
                            f"mail.{domain}",
                            domain
                        ]
                        server = possible_servers[0]  # Intentar el primero
                        show_status(f"Intentando {server}...")
                    
                    page.update()
                
                # Conectar al servidor
                email_service.connect(email, password, server=server)
                login_progress.visible = False
                
                # Cambiar a pantalla de selección de EPS
                page.window_width = WINDOW_SIZES["main"]["width"]
                page.window_height = WINDOW_SIZES["main"]["height"]
                login_view.visible = False
                eps_view.visible = True
                page.update()
                
            except Exception as ex:
                login_button.disabled = False
                login_progress.visible = False
                show_status(f"❌ Error: {str(ex)}", True)
        
        threading.Thread(target=worker, daemon=True).start()
    
    login_button.on_click = do_login
    
    # Agregar vistas
    page.add(login_view)
    page.add(eps_view)
    page.add(messages_view)


if __name__ == "__main__":
    ft.app(target=main)
