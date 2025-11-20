import flet as ft
import threading
import os


class MessagesScreen:
    """
    Pantalla de listado de correos con 'glosa' en el asunto.
    
    Busca y muestra todos los correos que contienen la palabra 'glosa'
    en el asunto, permitiendo descargar sus adjuntos.
    """
    
    def __init__(self, page: ft.Page, imap_client, on_logout=None):
        """
        Inicializa la pantalla de mensajes.
        
        Args:
            page: Referencia a la página principal de Flet
            imap_client: Cliente IMAP ya autenticado
            on_logout: Callback opcional para cerrar sesión
        """
        self.page = page
        self.client = imap_client
        self.on_logout = on_logout
        
        # Componentes de la interfaz de usuario
        self.messages_column = ft.Column(
            scroll=ft.ScrollMode.AUTO,  # Scroll vertical
            expand=True  # Expandir para ocupar espacio disponible
        )
        self.status = ft.Text("", size=12)  # Texto de estado/feedback
        
    def show_status(self, msg: str):
        """
        Actualiza el mensaje de estado en la parte inferior.
        
        Args:
            msg: Mensaje a mostrar al usuario
        """
        self.status.value = msg
        self.page.update()
    
    def _download_attachments_worker(self, msg_id, msg_subject):
        """
        Thread worker que descarga adjuntos de un mensaje específico.
        
        Args:
            msg_id: ID del mensaje en el servidor IMAP
            msg_subject: Asunto del mensaje (para mostrar en el status)
        """
        try:
            # Informar al usuario que está descargando
            self.show_status(f"Descargando adjuntos de '{msg_subject}'...")
            
            # Descargar adjuntos usando el cliente IMAP
            saved = self.client.download_attachments(msg_id)
            
            # Mostrar resultado al usuario
            if saved:
                # Si se descargaron archivos, mostrar cantidad y ubicación
                self.show_status(
                    f"✓ Descargados {len(saved)} archivo(s) en: {os.path.dirname(saved[0])}"
                )
            else:
                self.show_status("Sin adjuntos en este correo.")
                
        except Exception as e:
            # Mostrar error si algo sale mal
            self.show_status(f"Error al descargar: {e}")
    
    def _on_download_click(self, msg_id, msg_subject):
        """
        Maneja el evento de click en el botón de descarga.
        
        Inicia la descarga en un thread separado para no bloquear la UI.
        
        Args:
            msg_id: ID del mensaje
            msg_subject: Asunto del mensaje
        """
        threading.Thread(
            target=self._download_attachments_worker,
            args=(msg_id, msg_subject),
            daemon=True  # Thread daemon (se cierra con la app)
        ).start()
    
    def _build_message_tile(self, msg):
        """
        Construye una tarjeta visual para un mensaje individual.
        
        Args:
            msg: Diccionario con datos del mensaje (subject, from, date, etc.)
        
        Returns:
            Card: Componente visual que representa el mensaje
        """
        return ft.Card(
            content=ft.Container(
                content=ft.Column([
                    # Asunto del mensaje en negrita
                    ft.Text(
                        msg.get("subject") or "(sin asunto)",
                        weight=ft.FontWeight.BOLD,
                        size=14
                    ),
                    # Remitente
                    ft.Text(
                        f"De: {msg.get('from')}",
                        size=11,
                        color=ft.Colors.GREY_700
                    ),
                    # Fecha
                    ft.Text(
                        f"Fecha: {msg.get('date')}",
                        size=10,
                        color=ft.Colors.GREY_600
                    ),
                    # Botón de descarga e indicador de adjuntos
                    ft.Row([
                        ft.ElevatedButton(
                            "Descargar Adjuntos",
                            icon=ft.Icons.DOWNLOAD,
                            on_click=lambda e, mid=msg["id"], subj=msg.get("subject"): 
                                self._on_download_click(mid, subj),
                            disabled=not msg.get("has_attachments")  # Deshabilitar si no hay adjuntos
                        ),
                        ft.Text(
                            "📎 Tiene adjuntos" if msg.get("has_attachments") else "Sin adjuntos",
                            size=11
                        )
                    ])
                ], tight=True, spacing=4),
                padding=10
            ),
            elevation=1,  # Sombra ligera
        )
    
    def _load_messages_worker(self):
        """
        Thread worker que busca y carga mensajes con 'glosa' en el asunto.
        
        Este método se ejecuta en un thread separado para no bloquear la UI
        mientras se consulta el servidor IMAP.
        """
        try:
            # Informar al usuario que está buscando
            self.show_status("Buscando correos con 'glosa' en el asunto...")
            
            # Buscar mensajes usando el cliente IMAP (límite de 100)
            msgs = self.client.search_by_subject("glosa", limit=100)
            
            # Limpiar la lista actual de mensajes
            self.messages_column.controls.clear()
            
            # Si no hay mensajes, mostrar mensaje informativo
            if not msgs:
                self.messages_column.controls.append(
                    ft.Container(
                        content=ft.Text(
                            "No se encontraron correos con 'glosa' en el asunto.",
                            size=16,
                            color=ft.Colors.GREY_600
                        ),
                        alignment=ft.alignment.center,
                        padding=20
                    )
                )
            else:
                # Agregar una tarjeta por cada mensaje encontrado
                for msg in msgs:
                    self.messages_column.controls.append(self._build_message_tile(msg))
            
            # Actualizar status con el resultado
            self.show_status(f"Se encontraron {len(msgs)} correo(s) con 'glosa' en el asunto.")
            
            # Actualizar la interfaz
            self.page.update()
            
        except Exception as ex:
            # Mostrar error si algo falla
            self.show_status(f"Error al buscar mensajes: {ex}")
            self.page.update()
    
    def load_messages(self):
        """
        Inicia la carga de mensajes en segundo plano.
        
        Este método se llama cuando se muestra la pantalla por primera vez
        o cuando el usuario presiona el botón de refrescar.
        """
        threading.Thread(target=self._load_messages_worker, daemon=True).start()
    
    def _on_refresh_click(self, e):
        """
        Maneja el evento de click en el botón de refrescar.
        
        Recarga la lista de mensajes desde el servidor.
        """
        self.load_messages()
    
    def build(self):
        """
        Construye y retorna el árbol de componentes de la pantalla.
        
        Returns:
            Column: Componente principal con header, lista de mensajes y status
        """
        # Header con título y botón de refrescar
        header = ft.Container(
            content=ft.Row([
                ft.Text(
                    "Correos con 'glosa'",
                    size=20,
                    weight=ft.FontWeight.BOLD
                ),
                ft.IconsButton(
                    ft.Icons.REFRESH,
                    on_click=self._on_refresh_click,
                    tooltip="Recargar mensajes"
                ),
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            padding=10,
            bgcolor=ft.Colors.BLUE_GREY_50
        )
        
        # Retornar columna principal con todos los componentes
        return ft.Column([
            header,  # Header fijo en la parte superior
            ft.Container(
                content=self.messages_column,  # Lista de mensajes con scroll
                expand=True,
                padding=10
            ),
            ft.Container(
                content=self.status,  # Texto de estado en la parte inferior
                padding=10
            )
        ], expand=True)
