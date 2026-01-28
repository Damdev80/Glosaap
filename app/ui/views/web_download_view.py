"""
Vista para descarga automatizada de portales web
Con soporte de temas claro/oscuro
"""
import flet as ft
import threading
import os
from app.service.credential_manager import CredentialManager


class WebDownloadView:
    """Vista de descarga automática desde portales EPS"""
    
    def __init__(self, page, assets_dir, on_back=None):
        self.page = page
        self.assets_dir = assets_dir
        self.on_back = on_back  # Callback para volver al dashboard
        self.familiar_scraper = None
        self.fomag_scraper = None
        self.selected_eps = None  # Para saber cuál EPS está activa
        self.credential_manager = CredentialManager()
        self.container = self.build()
    
    def _create_eps_selection_card(self, eps_name, color, description):
        """Crea una card de selección de EPS"""
        
        def on_hover(e):
            card_container.scale = 1.02 if e.data == "true" else 1.0
            card_container.shadow = ft.BoxShadow(
                spread_radius=0,
                blur_radius=25 if e.data == "true" else 15,
                color=ft.Colors.with_opacity(0.10 if e.data == "true" else 0.06, ft.Colors.ON_SURFACE),
                offset=ft.Offset(0, 6 if e.data == "true" else 2)
            )
            self.page.update()
        
        def on_click(e):
            self.show_eps_form(eps_name)
        
        card_content = ft.Column([
            ft.Text(
                eps_name,
                size=22,
                weight=ft.FontWeight.BOLD,
                color=ft.Colors.ON_SURFACE,
                text_align=ft.TextAlign.CENTER
            ),
            ft.Container(
                width=50,
                height=3,
                bgcolor=color,
                border_radius=2
            ),
            ft.Container(height=10),
            ft.Text(
                description,
                size=13,
                color=ft.Colors.ON_SURFACE_VARIANT,
                text_align=ft.TextAlign.CENTER,
                weight=ft.FontWeight.W_400
            ),
            ft.Container(height=20),
            ft.Text(
                "Seleccionar →",
                size=12,
                weight=ft.FontWeight.W_500,
                color=color
            )
        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=0)
        
        card_container = ft.Container(
            content=card_content,
            width=320,
            height=200,
            bgcolor=ft.Colors.SURFACE,
            border_radius=12,
            padding=30,
            shadow=ft.BoxShadow(
                spread_radius=0,
                blur_radius=15,
                color=ft.Colors.with_opacity(0.06, ft.Colors.ON_SURFACE),
                offset=ft.Offset(0, 2)
            ),
            border=ft.border.all(1, ft.Colors.OUTLINE_VARIANT),
            animate=ft.Animation(250, ft.AnimationCurve.EASE_OUT),
            animate_scale=ft.Animation(250, ft.AnimationCurve.EASE_OUT),
            scale=1.0,
            on_hover=on_hover,
            on_click=on_click,
            ink=True
        )
        
        return card_container
    
    def build(self):
        """Construye la vista"""
        
        # Header con botón de volver
        back_header = ft.Container(
            content=ft.Row([
                ft.IconButton(
                    icon=ft.Icons.ARROW_BACK,
                    icon_color=ft.Colors.PRIMARY,
                    icon_size=24,
                    tooltip="Volver al Dashboard",
                    on_click=lambda e: self.on_back() if self.on_back else None
                ),
                ft.Text(
                    "Descarga Web",
                    size=18,
                    weight=ft.FontWeight.W_600,
                ),
                ft.Container(expand=True),
            ], alignment=ft.MainAxisAlignment.START, vertical_alignment=ft.CrossAxisAlignment.CENTER),
            padding=ft.padding.symmetric(horizontal=20, vertical=10),
            bgcolor=ft.Colors.SURFACE,
            border=ft.border.only(bottom=ft.BorderSide(1, ft.Colors.OUTLINE))
        )
        
        # Header minimalista
        self.header = ft.Container(
            content=ft.Column([
                ft.Text(
                    "Descarga desde Portales Web",
                    size=28,
                    weight=ft.FontWeight.BOLD,
                    color=ft.Colors.ON_SURFACE,
                    text_align=ft.TextAlign.CENTER
                ),
                ft.Container(height=5),
                ft.Text(
                    "Selecciona la EPS para automatizar la descarga",
                    size=14,
                    color=ft.Colors.ON_SURFACE_VARIANT,
                    text_align=ft.TextAlign.CENTER,
                    width=600
                )
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
            padding=ft.padding.only(top=20, bottom=35)
        )
        
        # Cards de selección
        familiar_card = self._create_eps_selection_card(
            eps_name="Familiar de Colombia",
            color="#2196F3",
            description="Automatiza la descarga de archivos de glosas desde el portal web de Familiar"
        )
        
        fomag_card = self._create_eps_selection_card(
            eps_name="Fomag (Horus)",
            color="#4CAF50",
            description="Descarga automática de facturas objetadas desde el sistema Horus de Fomag"
        )
        
        # Vista de selección (inicial)
        self.selection_view = ft.Column([
            self.header,
            ft.Row([
                familiar_card,
                ft.Container(width=30),
                fomag_card
            ], alignment=ft.MainAxisAlignment.CENTER),
            ft.Container(height=50)
        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, visible=True)
        
        # Vista de formulario (oculta inicialmente)
        self.form_view = ft.Column([
            ft.Container(height=20),
            ft.Row([
                ft.TextButton(
                    "← Volver a selección",
                    on_click=lambda e: self.show_selection(),
                    style=ft.ButtonStyle(color=ft.Colors.ON_SURFACE_VARIANT)
                )
            ], alignment=ft.MainAxisAlignment.START),
            ft.Container(height=10)
        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, visible=False, scroll=ft.ScrollMode.AUTO)
        
        # ========== FAMILIAR DE COLOMBIA ==========
        self.familiar_nit = ft.TextField(
            label="NIT de la IPS",
            hint_text="Ej: 830510991",
            border_color=ft.Colors.OUTLINE,
            focused_border_color="#2196F3",
            color=ft.Colors.ON_SURFACE,
            label_style=ft.TextStyle(color=ft.Colors.ON_SURFACE),
            height=50,
            text_size=14
        )
        
        self.familiar_usuario = ft.TextField(
            label="Usuario",
            hint_text="Ingresa tu usuario",
            border_color=ft.Colors.OUTLINE,
            focused_border_color="#2196F3",
            color=ft.Colors.ON_SURFACE,
            label_style=ft.TextStyle(color=ft.Colors.ON_SURFACE),
            height=50,
            text_size=14
        )
        
        self.familiar_password = ft.TextField(
            label="Contraseña",
            password=True,
            can_reveal_password=True,
            border_color=ft.Colors.OUTLINE,
            focused_border_color="#2196F3",
            color=ft.Colors.ON_SURFACE,
            label_style=ft.TextStyle(color=ft.Colors.ON_SURFACE),
            height=50,
            text_size=14
        )
        
        # Fechas
        self.familiar_fecha_inicio = ft.TextField(
            label="Fecha Inicio (opcional)",
            hint_text="2024/01/01",
            border_color=ft.Colors.OUTLINE,
            focused_border_color="#2196F3",
            color=ft.Colors.ON_SURFACE,
            label_style=ft.TextStyle(color=ft.Colors.ON_SURFACE),
            height=50,
            text_size=14,
            width=280
        )
        
        self.familiar_fecha_fin = ft.TextField(
            label="Fecha Fin (opcional)",
            hint_text="2025/12/15",
            border_color=ft.Colors.OUTLINE,
            focused_border_color="#2196F3",
            color=ft.Colors.ON_SURFACE,
            label_style=ft.TextStyle(color=ft.Colors.ON_SURFACE),
            height=50,
            text_size=14,
            width=280
        )
        
        # Checkbox para recordar credenciales de Familiar
        self.familiar_remember = ft.Checkbox(
            label="Recordar credenciales",
            value=False,
            label_style=ft.TextStyle(
                size=12,
                color=ft.Colors.ON_SURFACE
            )
        )
        
        self.familiar_status = ft.Text(
            "",
            size=12,
            color=ft.Colors.ON_SURFACE_VARIANT,
            text_align=ft.TextAlign.CENTER,
            weight=ft.FontWeight.W_500
        )
        
        self.familiar_btn = ft.ElevatedButton(
            "Iniciar Descarga",
            on_click=self.download_familiar,
            bgcolor="#2196F3",
            color=ft.Colors.SURFACE,
            height=45,
            width=200,
            style=ft.ButtonStyle(
                shape=ft.RoundedRectangleBorder(radius=8)
            )
        )
        
        self.familiar_form = ft.Container(
            content=ft.Column([
                ft.Text(
                    "Familiar de Colombia",
                    size=24,
                    weight=ft.FontWeight.BOLD,
                    color=ft.Colors.ON_SURFACE
                ),
                ft.Container(
                    width=60,
                    height=3,
                    bgcolor="#2196F3",
                    border_radius=2
                ),
                ft.Container(height=25),
                self.familiar_nit,
                self.familiar_usuario,
                self.familiar_password,
                ft.Container(height=5),
                ft.Text(
                    "Rango de fechas",
                    size=13,
                    color=ft.Colors.ON_SURFACE_VARIANT
                ),
                ft.Container(height=5),
                ft.Row([
                    self.familiar_fecha_inicio,
                    ft.Container(width=10),
                    self.familiar_fecha_fin
                ], alignment=ft.MainAxisAlignment.CENTER),
                ft.Container(height=5),
                self.familiar_remember,
                ft.Container(height=25),
                self.familiar_btn,
                ft.Container(height=10),
                self.familiar_status
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=15),
            width=650,
            padding=40,
            bgcolor=ft.Colors.SURFACE,
            border_radius=12,
            border=ft.border.all(1, ft.Colors.OUTLINE_VARIANT),
            shadow=ft.BoxShadow(
                spread_radius=0,
                blur_radius=15,
                color=ft.Colors.with_opacity(0.06, ft.Colors.ON_SURFACE),
                offset=ft.Offset(0, 2)
            )
        )
        
        # ========== FOMAG ==========
        self.fomag_usuario = ft.TextField(
            label="Usuario",
            hint_text="usuario@fomag.com",
            border_color=ft.Colors.OUTLINE,
            focused_border_color="#4CAF50",
            color=ft.Colors.ON_SURFACE,
            label_style=ft.TextStyle(color=ft.Colors.ON_SURFACE),
            height=50,
            text_size=14
        )
        
        self.fomag_password = ft.TextField(
            label="Contraseña",
            password=True,
            can_reveal_password=True,
            border_color=ft.Colors.OUTLINE,
            focused_border_color="#4CAF50",
            color=ft.Colors.ON_SURFACE,
            label_style=ft.TextStyle(color=ft.Colors.ON_SURFACE),
            height=50,
            text_size=14
        )
        
        # Checkbox para recordar credenciales
        self.fomag_remember = ft.Checkbox(
            label="Recordar credenciales",
            value=False,
            label_style=ft.TextStyle(
                size=12,
                color=ft.Colors.ON_SURFACE
            )
        )
        
        # Nota sobre CAPTCHA y sesión
        captcha_note = ft.Container(
            content=ft.Column([
                ft.Row([
                    ft.Icon(ft.Icons.INFO_OUTLINE, size=16, color="#2196F3"),
                    ft.Container(width=8),
                    ft.Text(
                        "Sesión Persistente Activada",
                        size=13,
                        weight=ft.FontWeight.BOLD,
                        color="#2196F3"
                    )
                ], alignment=ft.MainAxisAlignment.CENTER),
                ft.Container(height=8),
                ft.Text(
                    "• Primera vez: Resuelve el CAPTCHA manualmente",
                    size=11,
                    color=ft.Colors.ON_SURFACE
                ),
                ft.Text(
                    "• Siguientes veces: Sesión guardada, sin CAPTCHA",
                    size=11,
                    color=ft.Colors.ON_SURFACE
                ),
                ft.Container(height=5),
                ft.Text(
                    "La sesión se mantiene abierta en el navegador",
                    size=10,
                    color=ft.Colors.ON_SURFACE_VARIANT,
                    italic=True,
                    text_align=ft.TextAlign.CENTER
                )
            ], spacing=2, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
            padding=ft.padding.symmetric(horizontal=20, vertical=15),
            bgcolor="#E3F2FD",
            border_radius=8,
            border=ft.border.all(1, "#90CAF9")
        )
        
        self.fomag_status = ft.Text(
            "",
            size=12,
            color=ft.Colors.ON_SURFACE_VARIANT,
            text_align=ft.TextAlign.CENTER,
            weight=ft.FontWeight.W_500
        )
        
        self.fomag_btn = ft.ElevatedButton(
            "Iniciar Descarga",
            on_click=self.download_fomag,
            bgcolor="#4CAF50",
            color=ft.Colors.SURFACE,
            height=45,
            width=200,
            style=ft.ButtonStyle(
                shape=ft.RoundedRectangleBorder(radius=8)
            )
        )
        
        self.fomag_form = ft.Container(
            content=ft.Column([
                ft.Text(
                    "Fomag (Horus)",
                    size=24,
                    weight=ft.FontWeight.BOLD,
                    color=ft.Colors.ON_SURFACE
                ),
                ft.Container(
                    width=60,
                    height=3,
                    bgcolor="#4CAF50",
                    border_radius=2
                ),
                ft.Container(height=25),
                captcha_note,
                ft.Container(height=10),
                self.fomag_usuario,
                self.fomag_password,
                ft.Container(height=5),
                self.fomag_remember,
                ft.Container(height=25),
                self.fomag_btn,
                ft.Container(height=10),
                self.fomag_status
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=15),
            width=650,
            padding=40,
            bgcolor=ft.Colors.SURFACE,
            border_radius=12,
            border=ft.border.all(1, ft.Colors.OUTLINE_VARIANT),
            shadow=ft.BoxShadow(
                spread_radius=0,
                blur_radius=15,
                color=ft.Colors.with_opacity(0.06, ft.Colors.ON_SURFACE),
                offset=ft.Offset(0, 2)
            )
        )
        
        # Contenedor principal con header de navegación
        content = ft.Column([
            back_header,
            ft.Container(
                content=ft.Stack([
                    self.selection_view,
                    self.form_view
                ], expand=True),
                expand=True,
                padding=20,
            )
        ], spacing=0, expand=True)
        
        self.container = ft.Container(
            content=content,
            expand=True,
            bgcolor=ft.Colors.SURFACE,
            visible=False
        )
        
        return self.container
    
    def show_selection(self):
        """Muestra la vista de selección de EPS"""
        self.selection_view.visible = True
        self.form_view.visible = False
        self.selected_eps = None
        self.page.update()
    
    def show_eps_form(self, eps_name):
        """Muestra el formulario de la EPS seleccionada"""
        self.selected_eps = eps_name
        self.selection_view.visible = False
        self.form_view.visible = True
        
        # Limpiar formulario anterior
        while len(self.form_view.controls) > 2:
            self.form_view.controls.pop()
        
        # Agregar formulario correspondiente
        if eps_name == "Familiar de Colombia":
            # Cargar credenciales guardadas
            self._load_familiar_credentials()
            self.form_view.controls.append(self.familiar_form)
        else:  # Fomag
            # Cargar credenciales guardadas
            self._load_fomag_credentials()
            self.form_view.controls.append(self.fomag_form)
        
        self.page.update()
    
    def _load_familiar_credentials(self):
        """Carga las credenciales guardadas de Familiar"""
        creds = self.credential_manager.load_credentials("familiar")
        if creds:
            self.familiar_nit.value = creds.get("nit", "")
            self.familiar_usuario.value = creds.get("username", "")
            self.familiar_password.value = creds.get("password", "")
            self.familiar_remember.value = True
            self.page.update()
    
    def _load_fomag_credentials(self):
        """Carga las credenciales guardadas de Fomag"""
        creds = self.credential_manager.load_credentials("fomag")
        if creds:
            self.fomag_usuario.value = creds.get("username", "")
            self.fomag_password.value = creds.get("password", "")
            self.fomag_remember.value = True
            self.page.update()
    
    def show(self):
        """Muestra la vista"""
        self.container.visible = True
        self.show_selection()
        self.page.update()
    
    def hide(self):
        """Oculta la vista"""
        self.container.visible = False
        self.page.update()
    
    def update_familiar_status(self, message):
        """Actualiza el estado de Familiar"""
        self.familiar_status.value = message
        self.page.update()
    
    def update_fomag_status(self, message):
        """Actualiza el estado de Fomag"""
        self.fomag_status.value = message
        self.page.update()
    
    def download_familiar(self, e):
        """Descarga desde Familiar de Colombia"""
        if not all([
            self.familiar_nit.value,
            self.familiar_usuario.value,
            self.familiar_password.value
        ]):
            self.update_familiar_status("❌ Completa todos los campos obligatorios")
            return
        
        # Guardar credenciales si está marcado
        if self.familiar_remember.value:
            self.credential_manager.save_credentials(
                "familiar",
                self.familiar_usuario.value,
                self.familiar_password.value,
                nit=self.familiar_nit.value
            )
        
        self.familiar_btn.disabled = True
        self.update_familiar_status("🔄 Iniciando descarga...")
        
        def worker():
            try:
                from app.service.web_scraper import FamiliarScraper
                
                scraper = FamiliarScraper(
                    download_dir=os.path.join(os.path.expanduser("~"), "Desktop", "descargas_familiar"),
                    progress_callback=self.update_familiar_status
                )
                
                if not self.familiar_nit.value:
                    raise ValueError("El NIT es obligatorio")

                if not self.familiar_usuario.value:
                    raise ValueError("El usuario es obligatorio")

                if not self.familiar_password.value:
                    raise ValueError("La contraseña es obligatoria")
                
                

                result = scraper.login_and_download(
                    nit=self.familiar_nit.value,
                    usuario=self.familiar_usuario.value,
                    contraseña=self.familiar_password.value,
                    fecha_inicio=self.familiar_fecha_inicio.value or None,
                    fecha_fin=self.familiar_fecha_fin.value or None
                )
                
                if result["success"]:
                    self.update_familiar_status(f"✅ {result['message']}")
                else:
                    self.update_familiar_status(f"❌ {result['message']}")
                    
            except Exception as ex:
                self.update_familiar_status(f"❌ Error: {str(ex)}")
            finally:
                self.familiar_btn.disabled = False
                self.page.update()
        
        threading.Thread(target=worker, daemon=True).start()
    
    def download_fomag(self, e):
        """Descarga desde Fomag"""
        if not all([
            self.fomag_usuario.value,
            self.fomag_password.value
        ]):
            self.update_fomag_status("❌ Completa todos los campos")
            return
        
        # Guardar credenciales si está marcado
        if self.fomag_remember.value:
            self.credential_manager.save_credentials(
                "fomag",
                self.fomag_usuario.value,
                self.fomag_password.value
            )
        
        self.fomag_btn.disabled = True
        self.update_fomag_status("🔄 Abriendo navegador con sesión persistente...")
        
        def worker():
            try:
                from app.service.web_scraper import FomagScraper
                
                # Ruta de red para resultados de glosa web
                download_dir = r"\\MINERVA\Cartera\GLOSAAP\RESULTADO DE GLOSA WEB"
                
                # Crear directorio si no existe
                try:
                    os.makedirs(download_dir, exist_ok=True)
                except:
                    # Fallback a escritorio si no hay acceso a red
                    download_dir = os.path.join(os.path.expanduser("~"), "Desktop", "descargas_fomag")
                    os.makedirs(download_dir, exist_ok=True)
                    self.update_fomag_status(f"⚠️ Sin acceso a red, guardando en: {download_dir}")
                
                scraper = FomagScraper(
                    download_dir=download_dir,
                    progress_callback=self.update_fomag_status
                )
                
                result = scraper.login_and_download(
                    usuario=self.fomag_usuario.value,
                    contraseña=self.fomag_password.value
                )
                
                if result["success"]:
                    self.update_fomag_status(f"✅ {result['message']}")
                else:
                    self.update_fomag_status(f"❌ {result['message']}")
                    
            except Exception as ex:
                self.update_fomag_status(f"❌ Error: {str(ex)}")
            finally:
                self.fomag_btn.disabled = False
                self.page.update()
        
        threading.Thread(target=worker, daemon=True).start()
