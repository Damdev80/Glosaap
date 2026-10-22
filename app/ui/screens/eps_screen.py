"""
Pantalla de selección de EPS y rango de fechas
Con soporte de temas claro/oscuro
"""
import flet as ft

from app.config.eps_config import get_eps_list
from app.ui.components.alert_dialog import AlertDialog
from app.ui.components.date_range_picker import DateRangePicker
from app.ui.components.eps_card import EpsCard
from app.ui.styles import SPACING


class EpsScreen:
    """Pantalla para seleccionar EPS y rango de fechas"""

    def __init__(self, page: ft.Page, on_eps_selected=None, on_logout=None, on_back=None, navigation_controller=None):
        """
        Args:
            page: Página de Flet
            on_eps_selected: Callback(eps_info, date_from, date_to) al seleccionar EPS
            on_logout: Callback al cerrar sesión
            on_back: Callback para navegar atrás
            navigation_controller: NavigationController (canal único de navegación)
        """
        self.page = page
        self.on_eps_selected = on_eps_selected
        self.on_logout = on_logout
        self.on_back = on_back
        self.navigation_controller = navigation_controller

        # Cargar lista de EPS desde configuración
        self.eps_list = get_eps_list()

        # Componente de fechas con callback de validación
        self.date_picker = DateRangePicker(
            page,
            on_validation_error=self._on_date_validation_error
        )

        # Estado de validación
        self.dates_selected = False
        self.warning_text = ft.Text(
            "",
            size=12,
            color=ft.Colors.RED,
            text_align=ft.TextAlign.CENTER,
            visible=False
        )

        # Crear vista
        self._create_view()

    def _on_date_validation_error(self, error_message):
        """Callback cuando hay un error de validación de fechas"""
        # El error ya se muestra en el DateRangePicker
        # Aquí podríamos agregar lógica adicional si fuera necesario
        pass

    def _on_eps_click(self, eps_info):
        """Maneja el click en una tarjeta de EPS"""

        # Verificar si la EPS tiene procesador implementado
        if not eps_info.get("processor_class"):
            eps_name = eps_info.get("name", "Esta EPS")

            # Diálogo informativo estándar (modal, botón Entendido que
            # solo cierra su diálogo vía page.close interno).
            AlertDialog.show_info(
                self.page,
                f"{eps_name} en Desarrollo",
                f"El procesador automático para {eps_name} aún no está disponible.\n\nEstamos trabajando en integrar esta EPS al sistema.",
            )
            return

        date_from, date_to = self.date_picker.get_dates()

        # Validar que se hayan seleccionado AMBAS fechas (obligatorio)
        if not date_from or not date_to:
            self._show_dates_required_dialog()
            return

        # Validar rango de fechas (desde <= hasta)
        if not self.date_picker.is_date_range_valid():
            self._show_date_error_dialog()
            return

        # Llamar callback con la info
        if self.on_eps_selected:
            self.on_eps_selected(eps_info, date_from, date_to)

    def _show_dates_required_dialog(self):
        """Muestra un diálogo indicando que las fechas son obligatorias"""
        AlertDialog.show_warning(
            self.page,
            "Fechas requeridas",
            "Debes seleccionar un rango de fechas antes de elegir una EPS.\n\nPor favor, selecciona la fecha 'Desde' y 'Hasta' para continuar."
        )

    def _show_date_error_dialog(self):
        """Muestra un diálogo de alerta cuando las fechas son incompatibles"""
        AlertDialog.show_error(
            self.page,
            "Rango de fechas inválido",
            "La fecha 'Desde' no puede ser mayor que la fecha 'Hasta'.\n\nPor favor, corrige el rango de fechas antes de continuar."
        )

    def _close_dialog(self, dialog):
        """Cierra un diálogo"""
        dialog.open = False
        self.page.update()

    def _close_overlay_dialog(self, dialog):
        """Cierra solo su diálogo (no usa overlay.clear() destructivo)."""
        try:
            self.page.close(dialog)
        except Exception:
            try:
                dialog.open = False
                self.page.update()
            except Exception:
                pass
        else:
            try:
                self.page.update()
            except Exception:
                pass

    def _handle_back(self, e):
        """Maneja el regreso al menú anterior"""
        if self.on_back:
            self.on_back()

    def _handle_logout(self, e):
        """Maneja el cierre de sesión (con confirmación previa)."""
        def do_logout(ev):
            if self.on_logout:
                self.on_logout()
        AlertDialog.show_confirm(
            self.page,
            title="Cerrar sesión",
            message=(
                "¿Cerrar la sesión actual?\n\n"
                "Se limpiará la sesión guardada y tendrás que iniciar sesión de nuevo."
            ),
            confirm_text="Cerrar sesión",
            cancel_text="Cancelar",
            on_confirm=do_logout,
        )

    def _create_view(self):
        """Crea la vista de la pantalla"""

        # Grid de tarjetas de EPS (usa la lista cargada desde config)
        eps_cards = ft.Row(
            controls=[EpsCard(eps, on_click=self._on_eps_click).build() for eps in self.eps_list],
            wrap=True,
            spacing=SPACING["md"],
            run_spacing=SPACING["md"],
            alignment=ft.MainAxisAlignment.CENTER
        )

        # Header con navegación
        header = ft.Container(
            content=ft.Row([
                ft.IconButton(
                    icon=ft.Icons.ARROW_BACK,
                    icon_color=ft.Colors.PRIMARY,
                    icon_size=24,
                    tooltip="Volver al Dashboard",
                    on_click=self._handle_back
                ),
                ft.Text(
                    "Gestor de Glosas",
                    size=20,
                    weight=ft.FontWeight.W_600,
                    color=ft.Colors.ON_SURFACE
                ),
                ft.Container(expand=True),  # Espaciador
            ], alignment=ft.MainAxisAlignment.START, vertical_alignment=ft.CrossAxisAlignment.CENTER),
            padding=ft.padding.symmetric(horizontal=20, vertical=10),
            bgcolor=ft.Colors.SURFACE,
            border=ft.border.only(bottom=ft.BorderSide(1, ft.Colors.OUTLINE))
        )

        # Contenedor principal
        self.view = ft.Container(
            content=ft.Column([
                # Header de navegación
                header,

                ft.Container(height=SPACING["sm"]),

                # Subtítulo
                ft.Text(
                    "Busca y procesa notificaciones de glosas por EPS",
                    size=15,
                    color=ft.Colors.ON_SURFACE_VARIANT,
                    text_align=ft.TextAlign.CENTER,
                    weight=ft.FontWeight.W_400
                ),

                ft.Container(height=SPACING["lg"]),

                # Paso 1: Selector de fechas
                ft.Container(
                    content=ft.Column([
                        ft.Row([
                            ft.Container(
                                content=ft.Text("1", size=15, weight=ft.FontWeight.BOLD, color=ft.Colors.SURFACE),
                                width=32,
                                height=32,
                                border_radius=16,
                                bgcolor=ft.Colors.PRIMARY,
                                alignment=ft.alignment.center,
                                shadow=ft.BoxShadow(
                                    spread_radius=0,
                                    blur_radius=8,
                                    color=ft.Colors.with_opacity(0.3, ft.Colors.PRIMARY),
                                    offset=ft.Offset(0, 2)
                                )
                            ),
                            ft.Text(
                                "Selecciona el rango de fechas",
                                size=16,
                                weight=ft.FontWeight.BOLD,
                                color=ft.Colors.ON_SURFACE
                            )
                        ], spacing=12, alignment=ft.MainAxisAlignment.CENTER),
                        ft.Container(height=8),
                        self.date_picker.build()
                    ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                ),

                ft.Container(height=SPACING["lg"]),

                # Paso 2: Selector de EPS
                ft.Container(
                    content=ft.Column([
                        ft.Row([
                            ft.Container(
                                content=ft.Text("2", size=15, weight=ft.FontWeight.BOLD, color=ft.Colors.SURFACE),
                                width=32,
                                height=32,
                                border_radius=16,
                                bgcolor=ft.Colors.PRIMARY,
                                alignment=ft.alignment.center,
                                shadow=ft.BoxShadow(
                                    spread_radius=0,
                                    blur_radius=8,
                                    color=ft.Colors.with_opacity(0.3, ft.Colors.PRIMARY),
                                    offset=ft.Offset(0, 2)
                                )
                            ),
                            ft.Text(
                                "Selecciona una EPS para buscar",
                                size=16,
                                weight=ft.FontWeight.BOLD,
                                color=ft.Colors.ON_SURFACE
                            )
                        ], spacing=10, alignment=ft.MainAxisAlignment.CENTER),
                        ft.Container(height=12),
                        self.warning_text,
                        ft.Container(
                            content=eps_cards,
                            padding=SPACING["md"],
                            bgcolor=ft.Colors.SURFACE_CONTAINER_HIGHEST,
                            border_radius=12
                        )
                    ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                ),

            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, scroll=ft.ScrollMode.AUTO),
            padding=ft.padding.all(SPACING["lg"]),
            bgcolor=ft.Colors.SURFACE,
            alignment=ft.alignment.top_center,
            expand=True,
            visible=False
        )
        # Alias exigido por el skill (toda vista expone .container)
        self.container = self.view

    def build(self):
        """Retorna la vista construida (alias legacy de .container)."""
        return self.container

    def show(self):
        """Muestra la pantalla"""
        self.view.visible = True
        self.warning_text.visible = False
        self.page.update()

    def hide(self):
        """Oculta la pantalla"""
        self.view.visible = False
        self.page.update()

    def get_date_range(self):
        """Retorna el rango de fechas seleccionado"""
        return self.date_picker.get_dates()
