"""
Vista de selección de método: Correo vs Web
"""
import flet as ft
import os


class MethodSelectionView:
    """Vista para elegir entre descarga por correo o web"""
    
    def __init__(self, page, assets_dir, on_email_method=None, on_web_method=None, on_logout=None):
        self.page = page
        self.assets_dir = assets_dir
        self.on_email_method = on_email_method
        self.on_web_method = on_web_method
        self.on_logout = on_logout
        self.container = self._build()
    
    def _create_method_card(self, title, description, action_key, icon, is_primary=True):
        """Crea una card de método usando Card de Flet (respeta temas)"""
        
        def on_click(e):
            if action_key == "email" and self.on_email_method:
                self.on_email_method()
            elif action_key == "web" and self.on_web_method:
                self.on_web_method()
        
        card = ft.Card(
            content=ft.Container(
                content=ft.Column([
                    ft.Icon(icon, size=48, color=ft.Colors.PRIMARY if is_primary else ft.Colors.GREEN),
                    ft.Container(height=15),
                    ft.Text(
                        title,
                        size=20,
                        weight=ft.FontWeight.BOLD,
                        text_align=ft.TextAlign.CENTER
                    ),
                    ft.Container(height=10),
                    ft.Text(
                        description,
                        size=13,
                        text_align=ft.TextAlign.CENTER,
                    ),
                    ft.Container(height=20),
                    ft.ElevatedButton(
                        "Seleccionar",
                        icon=ft.Icons.ARROW_FORWARD,
                        on_click=on_click,
                        color=ft.Colors.ON_PRIMARY if is_primary else ft.Colors.WHITE,
                        bgcolor=ft.Colors.PRIMARY if is_primary else ft.Colors.GREEN,
                    )
                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=0),
                padding=30,
                width=300,
                height=280,
                on_click=on_click,
                ink=True,
            ),
            elevation=3,
        )
        
        return card
    
    def _build(self):
        """Construye la interfaz"""
        
        # Header
        header = ft.Column([
            ft.Text(
                "Selecciona el método de descarga",
                size=28,
                weight=ft.FontWeight.BOLD,
                text_align=ft.TextAlign.CENTER
            ),
            ft.Container(height=8),
            ft.Text(
                "Elige cómo quieres obtener los archivos de glosas",
                size=14,
                text_align=ft.TextAlign.CENTER
            )
        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER)
        
        # Cards de métodos
        email_card = self._create_method_card(
            title="📧 Glosa por Correo",
            description="Descarga archivos desde tu bandeja de entrada usando IMAP.\nIdeal para glosas recibidas vía email.",
            action_key="email",
            icon=ft.Icons.EMAIL_OUTLINED,
            is_primary=True
        )
        
        web_card = self._create_method_card(
            title="🌐 Glosa por Web",
            description="Descarga automática desde portales web de EPS.\nAcceso directo a Familiar, Fomag, etc.",
            action_key="web",
            icon=ft.Icons.LANGUAGE,
            is_primary=False
        )
        
        # Layout
        content = ft.Column([
            ft.Container(height=40),
            header,
            ft.Container(height=40),
            ft.Row([
                email_card,
                ft.Container(width=30),
                web_card
            ], alignment=ft.MainAxisAlignment.CENTER),
            ft.Container(height=30),
            ft.OutlinedButton(
                "Cerrar sesión",
                icon=ft.Icons.LOGOUT,
                on_click=lambda e: self.on_logout() if self.on_logout else None,
            )
        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, expand=True)
        
        return ft.Container(
            content=content,
            bgcolor=ft.Colors.SURFACE,  # Fondo sólido
            expand=True,
            visible=False
        )
    
    def show(self):
        """Muestra la vista"""
        self.container.visible = True
        self.page.update()
    
    def hide(self):
        """Oculta la vista"""
        self.container.visible = False
        self.page.update()
