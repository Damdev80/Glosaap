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
from core.data_processor import DataProcessor
from ui.styles import COLORS, FONT_SIZES, SPACING, WINDOW_SIZES
from ui.components.message_row import MessageRow
from ui.components.data_table import DataTable as DataTableComponent


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
    data_processor = DataProcessor()
    
    # ==================== PANTALLA DE LOGIN ====================
    
    title = ft.Text(
        "Glosaap",
        size=FONT_SIZES["title"],
        weight=ft.FontWeight.W_300,
        color=COLORS["text_primary"],
        text_align=ft.TextAlign.CENTER
    )
    
    subtitle = ft.Text(
        "Gestor de correos IMAP",
        size=FONT_SIZES["body"],
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
        label="Contraseña de aplicación",
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
            title,
            subtitle,
            ft.Container(height=SPACING["xl"]),
            email_input,
            ft.Container(height=SPACING["md"]),
            password_input,
            ft.Container(height=SPACING["lg"]),
            login_button,
            ft.Container(height=SPACING["sm"]),
            login_progress,
            status_text
        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
        padding=ft.padding.symmetric(horizontal=SPACING["xxl"]),
        bgcolor=COLORS["bg_white"]
    )
    
    # ==================== PANTALLA DE MENSAJES ====================
    
    messages_list = ft.Column([], scroll=ft.ScrollMode.AUTO, expand=True, spacing=0)
    messages_status = ft.Text("", size=FONT_SIZES["small"], color=COLORS["text_secondary"])
    loading_bar = ft.ProgressBar(visible=False, color=COLORS["primary"], bgcolor=COLORS["border"])
    
    messages_view = ft.Column([
        # Header
        ft.Container(
            content=ft.Row([
                ft.Text(
                    "Correos con 'glosa'",
                    size=FONT_SIZES["heading"],
                    weight=ft.FontWeight.W_400,
                    color=COLORS["text_primary"]
                ),
                ft.Row([
                    ft.TextButton(
                        "📊 Ver Datos",
                        icon=ft.Icons.TABLE_CHART,
                        style=ft.ButtonStyle(
                            color=COLORS["bg_white"],
                            bgcolor=COLORS["primary"]
                        ),
                        on_click=lambda e: show_data_view()
                    ),
                    ft.IconButton(
                        icon=ft.Icons.REFRESH,
                        icon_color=COLORS["primary"],
                        tooltip="Actualizar",
                        on_click=lambda e: load_messages()
                    )
                ], spacing=SPACING["sm"])
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
    
    # ==================== PANTALLA DE DATOS ====================
    
    data_table_container = ft.Column([], scroll=ft.ScrollMode.AUTO, expand=True)
    data_status = ft.Text("", size=FONT_SIZES["small"], color=COLORS["text_secondary"])
    
    data_view = ft.Column([
        ft.Container(
            content=ft.Row([
                ft.IconButton(
                    icon=ft.Icons.ARROW_BACK,
                    icon_color=COLORS["primary"],
                    tooltip="Volver a correos",
                    on_click=lambda e: (
                        setattr(data_view, 'visible', False),
                        setattr(messages_view, 'visible', True),
                        page.update()
                    )
                ),
                ft.Text(
                    "Datos Procesados",
                    size=FONT_SIZES["heading"],
                    weight=ft.FontWeight.W_400,
                    color=COLORS["text_primary"]
                ),
            ], spacing=SPACING["sm"]),
            bgcolor=COLORS["bg_white"],
            padding=SPACING["lg"],
            border=ft.border.only(bottom=ft.BorderSide(1, COLORS["border"]))
        ),
        ft.Container(
            content=data_table_container,
            expand=True,
            padding=SPACING["lg"],
            bgcolor=COLORS["bg_light"]
        ),
        ft.Container(
            content=data_status,
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
    
    def show_data_status(msg):
        """Muestra mensaje de estado en pantalla de datos"""
        data_status.value = msg
        page.update()
    
    def show_data_view():
        """Muestra la vista de datos procesados"""
        def worker():
            try:
                excel_files = email_service.get_excel_files()
                
                if not excel_files:
                    show_messages_status("⚠️ No hay archivos Excel o CSV para procesar")
                    return
                
                show_messages_status("🔄 Procesando archivos...")
                page.update()
                
                # Procesar archivos
                df = data_processor.process_files(excel_files)
                
                if df is not None:
                    # Crear componente de tabla
                    data_table_component = DataTableComponent(df)
                    
                    # Limpiar y agregar contenido
                    data_table_container.controls.clear()
                    
                    # Información del dataset
                    info_widget = data_table_component.get_info_widget()
                    if info_widget:
                        data_table_container.controls.append(info_widget)
                    
                    # Agregar tabla
                    table = data_table_component.build()
                    data_table_container.controls.append(
                        ft.Container(
                            content=ft.Row([table], scroll=ft.ScrollMode.ALWAYS),
                            margin=ft.margin.only(top=SPACING["sm"])
                        )
                    )
                    
                    # Cambiar a vista de datos
                    messages_view.visible = False
                    data_view.visible = True
                    
                    summary = data_processor.get_summary()
                    show_data_status(
                        f"✅ Mostrando {min(100, summary['rows'])} de {summary['rows']} filas | "
                        f"{summary['files_processed']} archivo(s) procesado(s)"
                    )
                    page.update()
                else:
                    show_messages_status("❌ No se pudieron procesar los archivos")
                    
            except Exception as e:
                show_messages_status(f"❌ Error: {str(e)}")
                page.update()
        
        threading.Thread(target=worker, daemon=True).start()
    
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
                msgs = email_service.search_messages("glosa", limit=100, timeout=15, on_found=on_message_found)
                
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
        
        if not email or not password:
            show_status("Por favor ingresa email y contraseña", True)
            return
        
        login_button.disabled = True
        login_progress.visible = True
        status_text.value = ""
        show_status("Conectando al servidor...")
        page.update()
        
        def worker():
            try:
                email_service.connect(email, password)
                login_progress.visible = False
                
                # Cambiar a pantalla de mensajes
                page.window_width = WINDOW_SIZES["main"]["width"]
                page.window_height = WINDOW_SIZES["main"]["height"]
                login_view.visible = False
                messages_view.visible = True
                page.update()
                
                # Cargar mensajes
                load_messages()
                
            except Exception as ex:
                login_button.disabled = False
                login_progress.visible = False
                show_status(f"❌ Error: {str(ex)}", True)
        
        threading.Thread(target=worker, daemon=True).start()
    
    login_button.on_click = do_login
    
    # Agregar vistas
    page.add(login_view)
    page.add(messages_view)
    page.add(data_view)


if __name__ == "__main__":
    ft.app(target=main)
