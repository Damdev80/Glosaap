"""
Aplicación Glosaap - Cliente IMAP con Flet
Busca correos con 'glosa' en el asunto y descarga adjuntos
"""
import flet as ft
import os
import sys
import threading
import pandas as pd

# Configurar path para imports
PROJECT_APP_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_APP_DIR not in sys.path:
    sys.path.insert(0, PROJECT_APP_DIR)

from core.imap_client import ImapClient


def main(page: ft.Page):
    """Función principal de la aplicación"""
    
    # Configuración inicial de la página
    page.title = "Glosaap"
    page.window_width = 480
    page.window_height = 420
    page.bgcolor = "#FFFFFF"  # Blanco puro
    page.padding = 0
    
    # Variable para guardar el cliente IMAP
    imap_client = {"client": None}
    
    # ==================== PANTALLA DE LOGIN ====================
    
    # Componentes de login con diseño minimalista
    title = ft.Text(
        "Glosaap",
        size=36,
        weight=ft.FontWeight.W_300,
        color="#2C3E50",
        text_align=ft.TextAlign.CENTER
    )
    
    subtitle = ft.Text(
        "Gestor de correos IMAP",
        size=14,
        color="#7F8C8D",
        text_align=ft.TextAlign.CENTER
    )
    
    email_input = ft.TextField(
        label="Correo electrónico",
        width=380,
        autofocus=True,
        border_color="#E8E8E8",
        focused_border_color="#3498DB",
        bgcolor="#FAFAFA",
        color="#2C3E50",
        cursor_color="#3498DB",
        text_size=14
    )
    
    password_input = ft.TextField(
        label="Contraseña de aplicación",
        password=True,
        can_reveal_password=True,
        width=380,
        border_color="#E8E8E8",
        focused_border_color="#3498DB",
        bgcolor="#FAFAFA",
        color="#2C3E50",
        cursor_color="#3498DB",
        text_size=14
    )
    
    status_text = ft.Text(
        "",
        size=13,
        color="#E74C3C",
        text_align=ft.TextAlign.CENTER,
        weight=ft.FontWeight.W_400
    )
    
    # ProgressBar para login
    login_progress = ft.ProgressBar(visible=False, color="#3498DB", bgcolor="#E8E8E8", width=380)
    
    login_button = ft.Container(
        content=ft.Text("Iniciar Sesión", size=15, weight=ft.FontWeight.W_500),
        alignment=ft.alignment.center,
        bgcolor="#3498DB",
        border_radius=8,
        padding=15,
        width=380,
        ink=True
    )
    
    # Contenedor de login con espaciado elegante
    login_view = ft.Container(
        content=ft.Column([
            ft.Container(height=40),
            title,
            subtitle,
            ft.Container(height=30),
            email_input,
            ft.Container(height=15),
            password_input,
            ft.Container(height=25),
            login_button,
            ft.Container(height=10),
            login_progress,
            status_text
        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
        padding=ft.padding.symmetric(horizontal=40),
        bgcolor="#FFFFFF"
    )
    
    # ==================== PANTALLA DE MENSAJES ====================
    
    messages_list = ft.Column([], scroll=ft.ScrollMode.AUTO, expand=True, spacing=10)
    messages_status = ft.Text("", size=13, color="#7F8C8D")
    loading_bar = ft.ProgressBar(visible=False, color="#3498DB", bgcolor="#E8E8E8")
    
    # Variable para guardar datos procesados
    processed_data = {"df": None, "attachments": []}
    
    def create_message_row(msg, index):
        """Crea una fila de lista para un mensaje con indicadores de descarga"""
        subject = msg.get("subject", "(sin asunto)")
        msg_id = msg.get("id", "")
        
        # Crear contenedor para el progreso de descarga
        download_progress = ft.ProgressBar(
            width=200,
            color="#27AE60",
            bgcolor="#E8E8E8",
            visible=False,
            height=3
        )
        
        # Status de descarga
        download_status = ft.Text(
            "",
            size=11,
            color="#27AE60",
            visible=False
        )
        
        # Contador de adjuntos
        attachment_count = ft.Text(
            "",
            size=11,
            color="#7F8C8D",
            visible=False
        )
        
        # Guardar referencias en el mensaje para actualizarlas después
        msg["_progress"] = download_progress
        msg["_status"] = download_status
        msg["_count"] = attachment_count
        
        return ft.Container(
            content=ft.Row([
                # Número
                ft.Container(
                    content=ft.Text(
                        str(index),
                        size=13,
                        weight=ft.FontWeight.W_500,
                        color="#95A5A6"
                    ),
                    width=40,
                    alignment=ft.alignment.center
                ),
                # Subject
                ft.Container(
                    content=ft.Column([
                        ft.Text(
                            subject[:90] + "..." if len(subject) > 90 else subject,
                            size=13,
                            color="#2C3E50",
                            weight=ft.FontWeight.W_400
                        ),
                        ft.Row([
                            download_progress,
                            download_status
                        ], spacing=10, visible=False),
                        attachment_count
                    ], spacing=3),
                    expand=True
                ),
                # Ícono de estado
                ft.Container(
                    content=ft.Icon(
                        ft.Icons.CHECK_CIRCLE,
                        size=20,
                        color="#27AE60"
                    ) if msg.get("_downloaded") else ft.Icon(
                        ft.Icons.DOWNLOADING,
                        size=20,
                        color="#3498DB"
                    ),
                    width=40
                )
            ], spacing=10),
            padding=ft.padding.symmetric(horizontal=15, vertical=12),
            border=ft.border.only(bottom=ft.BorderSide(1, "#F0F0F0")),
            bgcolor="#FFFFFF"
        )
        """Crea una tarjeta visual minimalista para un mensaje"""
        subject = msg.get("subject", "(sin asunto)")
        from_addr = msg.get("from", "")
        date = msg.get("date", "")
        has_attach = msg.get("has_attachments", False)
        
        return ft.Container(
            content=ft.Column([
                # Header del mensaje
                ft.Row([
                    ft.Container(
                        content=ft.Icon(
                            ft.Icons.ATTACH_FILE if has_attach else ft.Icons.MAIL_OUTLINE,
                            size=20,
                            color="#3498DB" if has_attach else "#BDC3C7"
                        ),
                        width=40
                    ),
                    ft.Column([
                        ft.Text(
                            subject,
                            size=15,
                            weight=ft.FontWeight.W_500,
                            color="#2C3E50",
                            overflow=ft.TextOverflow.ELLIPSIS
                        ),
                        ft.Text(
                            f"De: {from_addr}",
                            size=12,
                            color="#7F8C8D",
                            overflow=ft.TextOverflow.ELLIPSIS
                        ),
                        ft.Text(
                            date,
                            size=11,
                            color="#95A5A6"
                        )
                    ], spacing=2, expand=True)
                ], spacing=10),
                # Botón de descarga si hay adjuntos
                ft.Container(
                    content=ft.TextButton(
                        "Descargar adjuntos",
                        icon=ft.Icons.DOWNLOAD,
                        style=ft.ButtonStyle(
                            color="#3498DB",
                            bgcolor="#EBF5FB"
                        ),
                        on_click=lambda e, mid=msg["id"], subj=subject: download_attachments(mid, subj)
                    ) if has_attach else ft.Text(
                        "Sin archivos adjuntos",
                        size=12,
                        color="#BDC3C7",
                        italic=True
                    ),
                    margin=ft.margin.only(left=40, top=5)
                )
            ], spacing=8),
            bgcolor="#FFFFFF",
            border=ft.border.all(1, "#E8E8E8"),
            border_radius=10,
            padding=20,
            animate=ft.animation.Animation(300, "easeOut")
        )
    
    messages_view = ft.Column([
        # Header fijo
        ft.Container(
            content=ft.Row([
                ft.Text(
                    "Correos con 'glosa'",
                    size=22,
                    weight=ft.FontWeight.W_400,
                    color="#2C3E50"
                ),
                ft.Row([
                    ft.TextButton(
                        "📊 Ver Datos",
                        icon=ft.Icons.TABLE_CHART,
                        style=ft.ButtonStyle(
                            color="#FFFFFF",
                            bgcolor="#3498DB"
                        ),
                        on_click=lambda e: show_data_view()
                    ),
                    ft.IconButton(
                        icon=ft.Icons.REFRESH,
                        icon_color="#3498DB",
                        tooltip="Actualizar",
                        on_click=lambda e: load_messages()
                    )
                ], spacing=10)
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            bgcolor="#FFFFFF",
            padding=20,
            border=ft.border.only(bottom=ft.BorderSide(1, "#E8E8E8"))
        ),
        # Barra de carga
        loading_bar,
        # Lista de mensajes
        ft.Container(
            content=messages_list,
            expand=True,
            padding=20,
            bgcolor="#F8F9FA"
        ),
        # Footer con status
        ft.Container(
            content=messages_status,
            padding=15,
            bgcolor="#FFFFFF",
            border=ft.border.only(top=ft.BorderSide(1, "#E8E8E8"))
        )
    ], expand=True, spacing=0, visible=False)
    
    # ==================== PANTALLA DE DATOS ====================
    
    data_table_container = ft.Column([], scroll=ft.ScrollMode.AUTO, expand=True)
    data_status = ft.Text("", size=13, color="#7F8C8D")
    
    data_view = ft.Column([
        # Header
        ft.Container(
            content=ft.Row([
                ft.IconButton(
                    icon=ft.Icons.ARROW_BACK,
                    icon_color="#3498DB",
                    tooltip="Volver a correos",
                    on_click=lambda e: (
                        setattr(data_view, 'visible', False),
                        setattr(messages_view, 'visible', True),
                        page.update()
                    )
                ),
                ft.Text(
                    "Datos Procesados",
                    size=22,
                    weight=ft.FontWeight.W_400,
                    color="#2C3E50"
                ),
            ], spacing=10),
            bgcolor="#FFFFFF",
            padding=20,
            border=ft.border.only(bottom=ft.BorderSide(1, "#E8E8E8"))
        ),
        # Tabla de datos
        ft.Container(
            content=data_table_container,
            expand=True,
            padding=20,
            bgcolor="#F8F9FA"
        ),
        # Footer con status
        ft.Container(
            content=data_status,
            padding=15,
            bgcolor="#FFFFFF",
            border=ft.border.only(top=ft.BorderSide(1, "#E8E8E8"))
        )
    ], expand=True, spacing=0, visible=False)
    
    # ==================== FUNCIONES ====================
    
    def show_status(msg, is_error=False):
        """Muestra mensaje de estado en login"""
        status_text.value = msg
        status_text.color = "#E74C3C" if is_error else "#3498DB"
        page.update()
    
    def show_messages_status(msg):
        """Muestra mensaje de estado en pantalla de mensajes"""
        messages_status.value = msg
        page.update()
    
    def show_data_status(msg):
        """Muestra mensaje de estado en pantalla de datos"""
        data_status.value = msg
        page.update()
    
    def process_excel_files(file_paths):
        """Procesa archivos Excel y CSV y retorna un DataFrame consolidado"""
        dfs = []
        for file_path in file_paths:
            try:
                if file_path.endswith(('.xlsx', '.xls')):
                    df = pd.read_excel(file_path)
                    dfs.append(df)
                elif file_path.endswith('.csv'):
                    df = pd.read_csv(file_path)
                    dfs.append(df)
            except Exception as e:
                print(f"Error procesando {file_path}: {e}")
        
        if dfs:
            return pd.concat(dfs, ignore_index=True)
        return None
    
    def create_data_table(df):
        """Crea una tabla visual con los datos del DataFrame"""
        if df is None or df.empty:
            return ft.Text("No hay datos para mostrar", size=14, color="#7F8C8D")
        
        # Limitar a las primeras 100 filas para rendimiento
        display_df = df.head(100)
        
        # Crear columnas de la tabla
        columns = [ft.DataColumn(ft.Text(str(col), weight=ft.FontWeight.BOLD, size=12)) 
                   for col in display_df.columns]
        
        # Crear filas
        rows = []
        for idx, row in display_df.iterrows():
            cells = [ft.DataCell(ft.Text(str(val)[:50], size=11)) for val in row]
            rows.append(ft.DataRow(cells=cells))
        
        return ft.DataTable(
            columns=columns,
            rows=rows,
            border=ft.border.all(1, "#E8E8E8"),
            border_radius=10,
            horizontal_lines=ft.BorderSide(1, "#F0F0F0"),
            heading_row_color="#F8F9FA",
            heading_row_height=50,
            data_row_max_height=40,
        )
    
    def show_data_view():
        """Muestra la vista de datos procesados"""
        def worker():
            try:
                if not processed_data["attachments"]:
                    show_messages_status("⚠️ No hay adjuntos descargados para procesar")
                    return
                
                show_messages_status("🔄 Procesando archivos...")
                page.update()
                
                # Filtrar solo archivos Excel/CSV
                excel_files = [f for f in processed_data["attachments"] 
                              if f.endswith(('.xlsx', '.xls', '.csv'))]
                
                if not excel_files:
                    show_messages_status("⚠️ No se encontraron archivos Excel o CSV")
                    return
                
                # Procesar archivos
                df = process_excel_files(excel_files)
                
                if df is not None:
                    processed_data["df"] = df
                    
                    # Crear tabla
                    data_table_container.controls.clear()
                    
                    # Información del dataset
                    info_text = ft.Text(
                        f"📊 {len(df)} filas × {len(df.columns)} columnas | "
                        f"📁 {len(excel_files)} archivo(s) procesado(s)",
                        size=13,
                        color="#3498DB",
                        weight=ft.FontWeight.W_500
                    )
                    data_table_container.controls.append(
                        ft.Container(content=info_text, padding=10, bgcolor="#EBF5FB", border_radius=5)
                    )
                    
                    # Agregar tabla
                    table = create_data_table(df)
                    data_table_container.controls.append(
                        ft.Container(
                            content=ft.Row([table], scroll=ft.ScrollMode.ALWAYS),
                            margin=ft.margin.only(top=10)
                        )
                    )
                    
                    # Cambiar a vista de datos
                    messages_view.visible = False
                    data_view.visible = True
                    show_data_status(f"✅ Mostrando primeras 100 de {len(df)} filas")
                    page.update()
                else:
                    show_messages_status("❌ No se pudieron procesar los archivos")
                    
            except Exception as e:
                show_messages_status(f"❌ Error: {str(e)}")
                page.update()
        
        threading.Thread(target=worker, daemon=True).start()
    
    def download_attachments(msg_id, subject):
        """Descarga adjuntos de un mensaje"""
        def worker():
            try:
                show_messages_status(f"📥 Descargando adjuntos de: {subject[:50]}...")
                saved = imap_client["client"].download_attachments(msg_id)
                if saved:
                    show_messages_status(f"✅ Descargados {len(saved)} archivo(s) en: {os.path.dirname(saved[0])}")
                else:
                    show_messages_status("⚠️ No se encontraron adjuntos en este mensaje")
            except Exception as e:
                show_messages_status(f"❌ Error: {str(e)}")
        
        threading.Thread(target=worker, daemon=True).start()
    
    def load_messages():
        """Carga mensajes con 'glosa' en el asunto y descarga adjuntos automáticamente"""
        def worker():
            try:
                loading_bar.visible = True
                messages_list.controls.clear()
                show_messages_status("🔍 Buscando correos con 'glosa' en el asunto...")
                page.update()
                
                found_count = [0]  # Lista para que sea mutable en el callback
                all_attachments = []  # Guardar rutas de todos los adjuntos
                all_messages = []  # Guardar referencias a los mensajes
                
                def on_message_found(msg):
                    """Callback cuando se encuentra un mensaje"""
                    found_count[0] += 1
                    
                    # Crear y agregar fila de mensaje
                    msg_row = create_message_row(msg, found_count[0])
                    messages_list.controls.append(msg_row)
                    all_messages.append(msg)
                    
                    show_messages_status(f"🔍 Encontrados {found_count[0]} correo(s)...")
                    page.update()
                
                # Buscar mensajes sin descargar todavía
                show_messages_status("🔍 Buscando correos...")
                msgs = imap_client["client"].search_by_subject("glosa", limit=100, timeout=15, on_found=on_message_found)
                
                if not msgs:
                    messages_list.controls.clear()
                    messages_list.controls.append(
                        ft.Container(
                            content=ft.Column([
                                ft.Icon(ft.Icons.MAIL_OUTLINE, size=60, color="#BDC3C7"),
                                ft.Text(
                                    "No se encontraron correos con 'glosa' en el asunto",
                                    size=15,
                                    color="#7F8C8D",
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
                
                # Ahora descargar adjuntos de todos los mensajes
                show_messages_status("📥 Descargando adjuntos...")
                page.update()
                
                for idx, msg in enumerate(msgs):
                    try:
                        # Buscar el Row que contiene el progreso
                        msg_row_controls = messages_list.controls[idx].content.controls[1].content.controls[1]
                        
                        # Mostrar progreso
                        if "_progress" in msg:
                            msg_row_controls.visible = True  # Hacer visible el Row
                            msg["_progress"].visible = True
                            msg["_status"].visible = True
                            msg["_status"].value = "Descargando..."
                            page.update()
                        
                        # Descargar adjuntos
                        saved = imap_client["client"].download_attachments(msg["id"])
                        
                        if saved:
                            all_attachments.extend(saved)
                            
                            # Actualizar UI
                            if "_progress" in msg:
                                msg["_progress"].visible = False
                                msg["_status"].value = f"✓ {len(saved)} archivo(s)"
                                msg["_status"].color = "#27AE60"
                                
                                # Mostrar nombres de archivos
                                file_names = [os.path.basename(f) for f in saved]
                                if len(file_names) <= 2:
                                    msg["_count"].value = f"📎 {', '.join(file_names)}"
                                else:
                                    msg["_count"].value = f"📎 {file_names[0]}, {file_names[1]} y {len(file_names)-2} más"
                                    
                                msg["_count"].visible = True
                                msg["_downloaded"] = True
                                page.update()
                        else:
                            # Sin adjuntos
                            if "_progress" in msg:
                                msg["_progress"].visible = False
                                msg["_status"].value = "Sin adjuntos"
                                msg["_status"].color = "#95A5A6"
                                page.update()
                        
                        show_messages_status(f"📥 Descargados: {len(all_attachments)} archivo(s) de {idx + 1}/{len(msgs)} correos")
                        page.update()
                        
                    except Exception as e:
                        print(f"Error descargando adjuntos del mensaje {msg.get('id')}: {e}")
                        if "_progress" in msg:
                            msg["_progress"].visible = False
                            msg["_status"].value = "⚠ Error"
                            msg["_status"].color = "#E74C3C"
                            msg["_status"].visible = True
                            page.update()
                
                # Guardar adjuntos en variable global para procesamiento
                processed_data["attachments"] = all_attachments
                
                # Mostrar resumen final
                if all_attachments:
                    show_messages_status(f"✅ {len(msgs)} correo(s) | 📎 {len(all_attachments)} adjunto(s) descargado(s)")
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
                # Conectar al servidor IMAP
                client = ImapClient()
                client.connect(email, password)
                imap_client["client"] = client
                
                # Ocultar loader
                login_progress.visible = False
                
                # Cambiar a pantalla de mensajes
                page.window_width = 900
                page.window_height = 700
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
    
    # Asignar evento al botón (click en el contenedor)
    login_button.on_click = do_login
    
    # Agregar vistas a la página
    page.add(login_view)
    page.add(messages_view)
    page.add(data_view)


if __name__ == "__main__":
    ft.app(target=main)
