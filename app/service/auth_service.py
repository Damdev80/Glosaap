import threading
from app.core.imap_client import ImapClient


class AuthService:
    """
    Servicio de autenticación que maneja la conexión IMAP.
    
    Esta clase encapsula la lógica de autenticación y mantiene
    el estado de la sesión del usuario con el servidor IMAP.
    """
    
    def __init__(self):
        """Inicializa el servicio de autenticación."""
        self.client = None  # Cliente IMAP (None si no está conectado)
        self.is_authenticated = False  # Estado de autenticación
        self.current_email = None  # Email del usuario autenticado
    
    def login(self, email: str, password: str, on_success, on_error):
        """
        Intenta conectarse al servidor IMAP en un thread separado.
        
        Args:
            email: Dirección de correo electrónico
            password: Contraseña de aplicación (no la contraseña normal)
            on_success: Función callback cuando la conexión es exitosa
            on_error: Función callback cuando hay un error
        """
        def _login_worker():
            """Thread worker que realiza la conexión IMAP."""
            try:
                # Crear una nueva instancia del cliente IMAP
                self.client = ImapClient()
                
                # Intentar conectar al servidor IMAP (por defecto Gmail)
                self.client.connect(email, password)
                
                # Marcar como autenticado y guardar el email
                self.is_authenticated = True
                self.current_email = email
                
                # Notificar éxito al callback - IMPORTANTE: importar time
                import time
                time.sleep(0.1)  # Pequeña pausa para asegurar que la UI esté lista
                on_success(self.client)
                
            except Exception as ex:
                # Si hay error, limpiar el estado
                self.is_authenticated = False
                self.current_email = None
                
                # Notificar error al callback
                on_error(str(ex))
        
        # Ejecutar el login en un thread separado para no bloquear la UI
        threading.Thread(target=_login_worker, daemon=True).start()
    
    def logout(self):
        """
        Cierra la sesión IMAP y limpia el estado.
        
        Intenta cerrar la conexión IMAP de forma segura,
        ignorando errores si la conexión ya estaba cerrada.
        """
        if self.client:
            try:
                # Intentar cerrar la conexión IMAP
                self.client.logout()
            except Exception:
                # Ignorar errores al cerrar (ej: conexión ya cerrada)
                pass
        
        # Limpiar el estado de autenticación
        self.client = None
        self.is_authenticated = False
        self.current_email = None
    
    def get_client(self):
        """
        Retorna el cliente IMAP actual si está autenticado.
        
        Returns:
            ImapClient si está autenticado, None en caso contrario
        """
        return self.client if self.is_authenticated else None
