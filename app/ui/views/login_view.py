"""
Vista de Login
"""
import flet as ft
import threading
import os
from app.ui.styles import COLORS, FONT_SIZES, SPACING, WINDOW_SIZES
from app.core.session_manager import save_session, load_session, clear_session


class LoginView:
    """Vista de login/autenticación"""
    
    def __init__(self, page: ft.Page, email_service, on_login_success=None, assets_dir=None):
        self.page = page
        self.email_service = email_service
        self.on_login_success = on_login_success
        self.assets_dir = assets_dir
        self.container = None
        
        # Controles
        self.email_input = None
        self.password_input = None
        self.server_input = None
        self.remember_session = None
        self.status_text = None
        self.login_progress = None
        self.login_button = None
        
        # Construir UI
        self._build()
        
    def _build(self):
        """Construye la vista de login"""
        self.email_input = ft.TextField(
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
        
        self.password_input = ft.TextField(
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
        
        self.server_input = ft.TextField(
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
        
        self.status_text = ft.Text("", size=FONT_SIZES["small"], color=COLORS["error"])
        self.login_progress = ft.ProgressBar(visible=False, color=COLORS["primary"], bgcolor=COLORS["border"], width=380)
        
        self.remember_session = ft.Checkbox(
            label="Recordar sesión",
            value=True,
            check_color=COLORS["bg_white"],
            width=200,
            focus_color=COLORS["bg_white"]
        )
        
        self.login_button = ft.Container(
            content=ft.Text("Iniciar Sesión", size=15, weight=ft.FontWeight.W_500, color=COLORS["bg_white"]),
            alignment=ft.alignment.center,
            bgcolor=COLORS["primary"],
            border_radius=8,
            padding=15,
            width=380,
            ink=True,
            on_click=self._handle_login
        )
        
        # Ruta del logo
        logo_path = os.path.join(self.assets_dir, "icons", "app_logo.png") if self.assets_dir else None
        
        self.container = ft.Container(
            content=ft.Column([
                ft.Container(height=SPACING["lg"]),
                ft.Container(
                    content=ft.Column([
                        # Logo de la app
                        ft.Image(
                            src=logo_path,
                            width=70,
                            height=70,
                            fit=ft.ImageFit.CONTAIN
                        ) if logo_path and os.path.exists(logo_path) else ft.Container(height=70),
                        ft.Container(height=SPACING["sm"]),
                        ft.Text("Glosaap", size=20, weight=ft.FontWeight.W_600, color=COLORS["text_primary"]),
                        ft.Text("Gestor de glosas y correos", size=11, color=COLORS["text_secondary"]),
                        ft.Container(height=SPACING["lg"]),
                        self.email_input,
                        ft.Container(height=SPACING["md"]),
                        self.password_input,
                        ft.Container(height=SPACING["md"]),
                        self.server_input,
                        ft.Container(height=SPACING["sm"]),
                        self.remember_session,
                        ft.Container(height=SPACING["md"]),
                        self.login_button,
                        ft.Container(height=SPACING["sm"]),
                        self.login_progress,
                        self.status_text
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
        
        return self.container
    
    def _handle_login(self, e):
        """Maneja el proceso de login"""
        email = self.email_input.value.strip()
        password = self.password_input.value
        server = self.server_input.value.strip()
        
        if not email or not password:
            self.show_status("Por favor ingresa correo y contraseña", True)
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
                self.login_progress.visible = True
                self.login_button.disabled = True
                self.show_status("Conectando...")
                
                self.email_service.connect(email, password, server)
                
                # Guardar sesión si está marcado
                if self.remember_session.value:
                    save_session(email, password, server)
                
                self.login_progress.visible = False
                self.login_button.disabled = False
                self.show_status("¡Conexión exitosa!")
                
                # Callback de éxito
                if self.on_login_success:
                    self.on_login_success()
                
            except Exception as ex:
                self.login_progress.visible = False
                self.login_button.disabled = False
                self.show_status(f"Error: {str(ex)}", True)
        
        threading.Thread(target=connect_worker, daemon=True).start()
    
    def try_auto_login(self):
        """Intenta hacer login automático con sesión guardada"""
        saved_session = load_session()
        if saved_session and saved_session.get("email") and saved_session.get("password"):
            # Rellenar campos
            self.email_input.value = saved_session["email"]
            self.password_input.value = saved_session["password"]
            self.server_input.value = saved_session.get("server", "")
            self.page.update()
            
            # Intentar conectar automáticamente
            def auto_connect():
                try:
                    self.show_status("🔄 Reconectando...")
                    self.login_progress.visible = True
                    self.page.update()
                    
                    self.email_service.connect(
                        saved_session["email"],
                        saved_session["password"],
                        saved_session.get("server", "imap.gmail.com")
                    )
                    
                    self.login_progress.visible = False
                    self.show_status("✅ Sesión restaurada")
                    self.page.update()
                    
                    # Callback de éxito
                    if self.on_login_success:
                        self.on_login_success()
                    
                except Exception as ex:
                    self.login_progress.visible = False
                    self.show_status(f"Sesión expirada - Ingresa de nuevo", True)
                    clear_session()
                    self.page.update()
            
            threading.Thread(target=auto_connect, daemon=True).start()
    
    def show_status(self, msg, is_error=False):
        """Muestra mensaje de estado"""
        self.status_text.value = msg
        self.status_text.color = COLORS["error"] if is_error else COLORS["primary"]
        self.page.update()
    
    def show_progress(self, visible):
        """Muestra/oculta barra de progreso"""
        self.login_progress.visible = visible
        self.page.update()
    
    def set_button_disabled(self, disabled):
        """Habilita/deshabilita botón de login"""
        self.login_button.disabled = disabled
        self.page.update()
    
    def set_credentials(self, email, password, server):
        """Establece las credenciales en los campos"""
        self.email_input.value = email
        self.password_input.value = password
        self.server_input.value = server
        self.page.update()
    
    def clear_credentials(self):
        """Limpia las credenciales"""
        self.email_input.value = ""
        self.password_input.value = ""
        self.server_input.value = ""
        self.page.update()
    
    def show(self):
        """Muestra la vista"""
        if self.container:
            self.container.visible = True
            self.page.update()
    
    def hide(self):
        """Oculta la vista"""
        if self.container:
            self.container.visible = False
            self.page.update()
    
    def logout(self):
        """Limpia la sesión y reinicia los campos"""
        clear_session()
        self.email_input.value = ""
        self.password_input.value = ""
        self.server_input.value = ""
        self.status_text.value = ""
        self.page.update()
