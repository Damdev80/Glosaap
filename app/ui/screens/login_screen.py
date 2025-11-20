import flet as ft


class LoginScreen:
    """
    Pantalla de inicio de sesión minimalista.
    
    Muestra un formulario simple con campos de email y contraseña,
    valida las entradas y notifica al callback cuando se presiona el botón.
    """
    
    def __init__(self, page: ft.Page, on_login_success):
        """
        Inicializa la pantalla de login.
        
        Args:
            page: Referencia a la página principal de Flet
            on_login_success: Callback que se llama con (email, password) al hacer login
        """
        self.page = page
        self.on_login_success = on_login_success
        
        # Componentes de la interfaz de usuario
        self.title = ft.Text(
            "Glosaap", 
            size=24, 
            weight=ft.FontWeight.BOLD, 
            color=ft.Colors.BLACK
        )
        
        self.email_field = ft.TextField(
            label="Email",
            width=360,
            autofocus=True,  # Foco automático al abrir
            bgcolor=ft.Colors.WHITE38,
            color=ft.Colors.BLACK
        )
        
        self.password_field = ft.TextField(
            label="Password",
            password=True,  # Ocultar contraseña
            can_reveal_password=True,  # Permitir mostrar contraseña
            width=360,
            bgcolor=ft.Colors.WHITE38,
            color=ft.Colors.BLACK
        )
        
        self.status = ft.Text("", size=12, color=ft.Colors.RED)
        self.btn_login = ft.ElevatedButton(
            "Entrar", 
            width=360, 
            on_click=self._on_login_click
        )
        
    def _on_login_click(self, e):
        """
        Maneja el evento de click en el botón de login.
        
        Valida que los campos no estén vacíos y llama al callback
        con las credenciales ingresadas.
        """
        email = self.email_field.value
        password = self.password_field.value
        
        # Validar que ambos campos tengan contenido
        if not email or not password:
            self.show_status("Por favor ingresa email y contraseña")
            return
        
        # Deshabilitar el botón para evitar múltiples clicks
        self.btn_login.disabled = True
        self.show_status("Conectando...")
        self.page.update()
        
        # Llamar al callback con las credenciales
        self.on_login_success(email, password)
    
    def show_status(self, msg: str, error: bool = False):
        """
        Muestra un mensaje de estado debajo del botón.
        
        Args:
            msg: Mensaje a mostrar
            error: Si es True, muestra el mensaje en rojo; si es False, en azul
        """
        self.status.value = msg
        self.status.color = ft.Colors.RED if error else ft.Colors.BLUE
        self.page.update()
    
    def enable_login_button(self):
        """
        Rehabilita el botón de login después de un error.
        
        Útil para permitir que el usuario intente conectarse nuevamente.
        """
        self.btn_login.disabled = False
        self.page.update()
    
    def build(self):
        """
        Construye y retorna el árbol de componentes de la pantalla.
        
        Returns:
            Column: Componente principal de la pantalla centrada verticalmente
        """
        # Tarjeta que contiene el formulario de login
        card = ft.Card(
            content=ft.Container(
                ft.Column([
                    self.title,
                    self.email_field,
                    self.password_field,
                    self.btn_login,
                    self.status
                ], tight=True, spacing=8),
                padding=20,
                alignment=ft.alignment.center,
            ),
            elevation=2,  # Sombra de la tarjeta
            color=ft.Colors.WHITE
        )
        
        # Retornar columna centrada horizontal y verticalmente
        return ft.Column(
            [ft.Row(
                [ft.Container(width=400, content=card)],
                alignment=ft.MainAxisAlignment.CENTER
            )],
            alignment=ft.MainAxisAlignment.CENTER,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            expand=True  # Expandir para ocupar todo el espacio disponible
        )
