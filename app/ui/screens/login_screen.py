import flet as ft
from app.ui.styles import COLORS, FONT_SIZES, SPACING


class LoginScreen:
    """
    Pantalla de inicio de sesión moderna y profesional.
    
    Muestra un formulario elegante con campos de email y contraseña,
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
        self._is_loading = False
        
        # Logo/Título con icono
        self.logo = ft.Icon(
            ft.Icons.HEALTH_AND_SAFETY_ROUNDED,
            size=48,
            color=COLORS["primary"]
        )
        
        self.title = ft.Text(
            "Glosaap", 
            size=FONT_SIZES["title"], 
            weight=ft.FontWeight.BOLD, 
            color=COLORS["text_primary"]
        )
        
        self.subtitle = ft.Text(
            "Gestión de Glosas Médicas",
            size=FONT_SIZES["body"],
            color=COLORS["text_secondary"]
        )
        
        # Campos de entrada estilizados
        self.email_field = ft.TextField(
            label="Correo electrónico",
            prefix_icon=ft.Icons.EMAIL_OUTLINED,
            width=320,
            height=52,
            autofocus=True,
            border_radius=10,
            border_color=COLORS["border"],
            focused_border_color=COLORS["primary"],
            bgcolor=COLORS["bg_white"],
            color=COLORS["text_primary"],
            cursor_color=COLORS["primary"],
            text_size=FONT_SIZES["body"],
            on_submit=self._on_login_click,
        )
        
        self.password_field = ft.TextField(
            label="Contraseña",
            prefix_icon=ft.Icons.LOCK_OUTLINED,
            password=True,
            can_reveal_password=True,
            width=320,
            height=52,
            border_radius=10,
            border_color=COLORS["border"],
            focused_border_color=COLORS["primary"],
            bgcolor=COLORS["bg_white"],
            color=COLORS["text_primary"],
            cursor_color=COLORS["primary"],
            text_size=FONT_SIZES["body"],
            on_submit=self._on_login_click,
        )
        
        # Mensaje de estado
        self.status = ft.Text(
            "", 
            size=FONT_SIZES["small"], 
            color=COLORS["error"],
            text_align=ft.TextAlign.CENTER,
        )
        
        # Spinner de carga
        self.loading_spinner = ft.ProgressRing(
            width=20, 
            height=20, 
            stroke_width=2,
            color=COLORS["bg_white"],
            visible=False,
        )
        
        # Botón de login con estilo moderno
        self.btn_login = ft.ElevatedButton(
            content=ft.Row(
                [
                    self.loading_spinner,
                    ft.Text("Iniciar sesión", size=FONT_SIZES["button"], weight=ft.FontWeight.W_600),
                ],
                alignment=ft.MainAxisAlignment.CENTER,
                spacing=8,
            ),
            width=320,
            height=48,
            style=ft.ButtonStyle(
                bgcolor={
                    ft.ControlState.DEFAULT: COLORS["primary"],
                    ft.ControlState.HOVERED: COLORS["primary_hover"],
                    ft.ControlState.DISABLED: COLORS["text_light"],
                },
                color=COLORS["bg_white"],
                elevation={"pressed": 0, "": 2},
                animation_duration=200,
                shape=ft.RoundedRectangleBorder(radius=10),
            ),
            on_click=self._on_login_click
        )
        
    def _on_login_click(self, e):
        """
        Maneja el evento de click en el botón de login.
        """
        if self._is_loading:
            return
            
        email = self.email_field.value
        password = self.password_field.value
        
        # Limpiar errores anteriores
        self._clear_field_errors()
        
        # Validar campos
        if not email:
            self._show_field_error(self.email_field, "Ingresa tu correo")
            return
        if not password:
            self._show_field_error(self.password_field, "Ingresa tu contraseña")
            return
        
        # Mostrar estado de carga
        self._set_loading(True)
        self.show_status("Conectando al servidor...")
        
        # Llamar al callback
        self.on_login_success(email, password)
    
    def _set_loading(self, loading: bool):
        """Activa o desactiva el estado de carga."""
        self._is_loading = loading
        self.btn_login.disabled = loading
        self.loading_spinner.visible = loading
        self.email_field.disabled = loading
        self.password_field.disabled = loading
        self.page.update()
    
    def _show_field_error(self, field: ft.TextField, message: str):
        """Muestra un error en un campo específico."""
        field.error_text = message
        field.border_color = COLORS["error"]
        self.page.update()
        field.focus()
    
    def _clear_field_errors(self):
        """Limpia los errores de los campos."""
        self.email_field.error_text = None
        self.email_field.border_color = COLORS["border"]
        self.password_field.error_text = None
        self.password_field.border_color = COLORS["border"]
        self.status.value = ""
    
    def show_status(self, msg: str, error: bool = False):
        """Muestra un mensaje de estado."""
        self.status.value = msg
        self.status.color = COLORS["error"] if error else COLORS["info"]
        self.page.update()
    
    def enable_login_button(self):
        """Rehabilita el formulario después de un error."""
        self._set_loading(False)
        self.status.value = ""
        self.page.update()
    
    def build(self):
        """Construye y retorna el árbol de componentes de la pantalla."""
        # Encabezado con logo
        header = ft.Column(
            [
                self.logo,
                self.title,
                self.subtitle,
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=4,
        )
        
        # Formulario
        form = ft.Column(
            [
                self.email_field,
                self.password_field,
                ft.Container(height=4),
                self.btn_login,
                self.status,
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=SPACING["md"],
        )
        
        # Tarjeta principal con sombra
        card = ft.Container(
            content=ft.Column(
                [
                    header,
                    ft.Container(height=SPACING["lg"]),
                    form,
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                tight=True,
            ),
            padding=ft.padding.symmetric(horizontal=40, vertical=36),
            bgcolor=COLORS["bg_white"],
            border_radius=16,
            shadow=ft.BoxShadow(
                spread_radius=0,
                blur_radius=24,
                color=ft.Colors.with_opacity(0.12, ft.Colors.BLACK),
                offset=ft.Offset(0, 8),
            ),
        )
        
        # Fondo con gradiente sutil
        return ft.Container(
            content=ft.Column(
                [card],
                alignment=ft.MainAxisAlignment.CENTER,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            expand=True,
            gradient=ft.LinearGradient(
                begin=ft.alignment.top_center,
                end=ft.alignment.bottom_center,
                colors=[COLORS["bg_light"], COLORS["bg_white"]],
            ),
        )
