"""
Vista para gestionar códigos de homologación - Estilo Minimalista
Con soporte para múltiples EPS
"""
import flet as ft
from app.ui.styles import COLORS, FONT_SIZES, SPACING
from app.core.homologacion_service import HomologacionService


class HomologacionView:
    """Vista para CRUD de códigos de homologación con selector de EPS"""
    
    def __init__(self, page: ft.Page, on_back):
        self.page = page
        self.on_back = on_back
        self.service = None  # Se inicializa cuando se selecciona una EPS
        self.current_eps = None
        
        # Vista de selección de EPS
        self.eps_selector_view = self._build_eps_selector()
        
        # Vista de gestión de códigos (inicialmente no construida)
        self.gestion_view = None
        
        # Container principal que alterna entre vistas
        self.container = ft.Container(
            content=self.eps_selector_view,
            bgcolor=COLORS["bg_light"],
            expand=True,
            visible=False
        )
    
    def _build_eps_selector(self):
        """Construye la vista de selección de EPS"""
        # Lista de tarjetas de EPS (se llenará dinámicamente)
        self.eps_cards_column = ft.Column(
            controls=[],
            spacing=16,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER
        )
        
        return ft.Column([
            # Header
            ft.Container(
                content=ft.Row([
                    ft.IconButton(
                        icon=ft.Icons.ARROW_BACK_IOS_NEW,
                        icon_color=COLORS["text_secondary"],
                        icon_size=18,
                        tooltip="Volver",
                        on_click=lambda e: self.on_back()
                    ),
                    ft.Text("Homologación", 
                           size=18,
                           weight=ft.FontWeight.W_500,
                           color=COLORS["text_primary"]),
                ], alignment=ft.MainAxisAlignment.START, spacing=8),
                padding=ft.padding.symmetric(horizontal=24, vertical=16),
            ),
            
            # Contenido
            ft.Container(
                content=ft.Column([
                    ft.Container(height=20),
                    ft.Text("Selecciona una EPS", 
                           size=16, 
                           weight=ft.FontWeight.W_500,
                           color=COLORS["text_primary"]),
                    ft.Text("Cada EPS tiene su propio archivo de homologación",
                           size=13,
                           color=COLORS["text_secondary"]),
                    ft.Container(height=24),
                    self.eps_cards_column
                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                expand=True,
                padding=ft.padding.symmetric(horizontal=24)
            )
        ], expand=True, spacing=0)
    
    def _create_eps_card(self, eps_info):
        """Crea una tarjeta para seleccionar una EPS"""
        def on_hover(e):
            card.scale = 1.02 if e.data == "true" else 1.0
            self.page.update()
        
        def on_click(e):
            self._seleccionar_eps(eps_info["key"])
        
        # Colores por EPS
        colores = {
            "mutualser": "#2196F3",
            "coosalud": "#4CAF50"
        }
        color = colores.get(eps_info["key"], COLORS["primary"])
        
        card = ft.Container(
            content=ft.Row([
                ft.Container(
                    content=ft.Text(
                        eps_info["name"][0],  # Primera letra
                        size=24,
                        weight=ft.FontWeight.BOLD,
                        color=COLORS["bg_white"]
                    ),
                    width=50,
                    height=50,
                    border_radius=10,
                    bgcolor=color,
                    alignment=ft.alignment.center
                ),
                ft.Container(width=16),
                ft.Column([
                    ft.Text(
                        eps_info["name"],
                        size=16,
                        weight=ft.FontWeight.W_600,
                        color=COLORS["text_primary"]
                    ),
                    ft.Text(
                        f"{eps_info['count']} códigos de homologación",
                        size=12,
                        color=COLORS["text_secondary"]
                    )
                ], spacing=2, alignment=ft.MainAxisAlignment.CENTER),
                ft.Container(expand=True),
                ft.Icon(
                    ft.Icons.ARROW_FORWARD_IOS,
                    size=16,
                    color=COLORS["text_secondary"]
                )
            ]),
            padding=20,
            bgcolor=COLORS["bg_white"],
            border_radius=12,
            border=ft.border.all(1, COLORS["border"]),
            animate_scale=ft.Animation(150, ft.AnimationCurve.EASE_OUT),
            scale=1.0,
            on_hover=on_hover,
            on_click=on_click,
            ink=True,
            width=400
        )
        return card
    
    def _seleccionar_eps(self, eps_key):
        """Selecciona una EPS y muestra la vista de gestión"""
        self.current_eps = eps_key
        self.service = HomologacionService(eps=eps_key)
        
        # Construir vista de gestión
        self.gestion_view = self._build_gestion_view()
        self.container.content = self.gestion_view
        
        self._actualizar_estadisticas()
        self._cargar_tabla()
        self.page.update()
    
    def _volver_a_selector(self):
        """Vuelve a la vista de selección de EPS"""
        self.current_eps = None
        self.service = None
        self.container.content = self.eps_selector_view
        self._cargar_eps_disponibles()
        self.page.update()
    
    def _build_gestion_view(self):
        """Construye la vista de gestión de códigos"""
        # Campos de formulario
        self.codigo_erp_field = ft.TextField(
            label="Código ERP",
            hint_text="881141",
            border_color=COLORS["border"],
            focused_border_color=COLORS["primary"],
            border_radius=8,
            content_padding=ft.padding.symmetric(horizontal=16, vertical=12),
            text_size=14,
            label_style=ft.TextStyle(size=12, color=COLORS["text_secondary"]),
            expand=True
        )
        
        self.codigo_dgh_field = ft.TextField(
            label="Código DGH",
            hint_text="881141",
            border_color=COLORS["border"],
            focused_border_color=COLORS["primary"],
            border_radius=8,
            content_padding=ft.padding.symmetric(horizontal=16, vertical=12),
            text_size=14,
            label_style=ft.TextStyle(size=12, color=COLORS["text_secondary"]),
            expand=True
        )
        
        self.buscar_field = ft.TextField(
            hint_text="Buscar código...",
            border_color=COLORS["border"],
            focused_border_color=COLORS["primary"],
            border_radius=8,
            content_padding=ft.padding.symmetric(horizontal=16, vertical=12),
            text_size=14,
            prefix_icon=ft.Icons.SEARCH,
            expand=True,
            on_change=self._on_buscar
        )
        
        # Tabla
        self.tabla = ft.DataTable(
            columns=[
                ft.DataColumn(ft.Text("Código ERP", size=12, weight=ft.FontWeight.W_500, color=COLORS["text_secondary"]), numeric=False),
                ft.DataColumn(ft.Text("Código DGH", size=12, weight=ft.FontWeight.W_500, color=COLORS["text_secondary"]), numeric=False),
                ft.DataColumn(ft.Text("COD_SERV_FACT", size=12, weight=ft.FontWeight.W_500, color=COLORS["text_secondary"]), numeric=False),
                ft.DataColumn(ft.Text("", size=12)),
            ],
            rows=[],
            border=ft.border.all(1, COLORS["border"]),
            border_radius=12,
            heading_row_color=COLORS["bg_light"],
            heading_row_height=50,
            data_row_max_height=48,
            data_row_min_height=44,
            column_spacing=40,
            horizontal_lines=ft.BorderSide(1, COLORS["border"]),
            show_checkbox_column=False,
            expand=True
        )
        
        # Status
        self.status_text = ft.Text("", size=12, color=COLORS["text_secondary"])
        self.stats_text = ft.Text("", size=13, color=COLORS["text_secondary"])
        
        # Colores por EPS
        colores = {
            "mutualser": "#2196F3",
            "coosalud": "#4CAF50"
        }
        eps_color = colores.get(self.current_eps, COLORS["primary"])
        
        return ft.Column([
            # Header con nombre de EPS
            ft.Container(
                content=ft.Row([
                    ft.IconButton(
                        icon=ft.Icons.ARROW_BACK_IOS_NEW,
                        icon_color=COLORS["text_secondary"],
                        icon_size=18,
                        tooltip="Volver a EPS",
                        on_click=lambda e: self._volver_a_selector()
                    ),
                    ft.Container(
                        content=ft.Text(
                            self.current_eps[0].upper(),
                            size=14,
                            weight=ft.FontWeight.BOLD,
                            color=COLORS["bg_white"]
                        ),
                        width=32,
                        height=32,
                        border_radius=8,
                        bgcolor=eps_color,
                        alignment=ft.alignment.center
                    ),
                    ft.Text(f"Homologación {self.current_eps.upper()}", 
                           size=18,
                           weight=ft.FontWeight.W_500,
                           color=COLORS["text_primary"]),
                    ft.Container(expand=True),
                    self.stats_text
                ], alignment=ft.MainAxisAlignment.START, spacing=8),
                padding=ft.padding.symmetric(horizontal=24, vertical=16),
            ),
            
            # Contenido
            ft.Container(
                content=ft.Column([
                    # Card agregar
                    ft.Container(
                        content=ft.Column([
                            ft.Text("Nuevo código", 
                                   size=14, 
                                   weight=ft.FontWeight.W_500,
                                   color=COLORS["text_primary"]),
                            ft.Container(height=12),
                            ft.Row([
                                self.codigo_erp_field,
                                self.codigo_dgh_field,
                            ], spacing=16),
                            ft.Container(height=12),
                            ft.Row([
                                self.status_text,
                                ft.Container(expand=True),
                                ft.ElevatedButton(
                                    content=ft.Row([
                                        ft.Icon(ft.Icons.ADD, size=16, color=COLORS["bg_white"]),
                                        ft.Text("Agregar", size=13, weight=ft.FontWeight.W_500)
                                    ], spacing=6),
                                    bgcolor=eps_color,
                                    color=COLORS["bg_white"],
                                    elevation=0,
                                    style=ft.ButtonStyle(
                                        shape=ft.RoundedRectangleBorder(radius=8),
                                        padding=ft.padding.symmetric(horizontal=20, vertical=12)
                                    ),
                                    on_click=self._on_agregar
                                )
                            ], alignment=ft.MainAxisAlignment.END)
                        ], spacing=0),
                        bgcolor=COLORS["bg_white"],
                        border_radius=12,
                        border=ft.border.all(1, COLORS["border"]),
                        padding=24
                    ),
                    
                    ft.Container(height=20),
                    
                    # Card tabla
                    ft.Container(
                        content=ft.Column([
                            ft.Row([
                                ft.Container(content=self.buscar_field, expand=True),
                                ft.IconButton(
                                    icon=ft.Icons.REFRESH_ROUNDED,
                                    icon_color=COLORS["text_secondary"],
                                    icon_size=20,
                                    tooltip="Actualizar",
                                    on_click=lambda e: self._cargar_tabla()
                                )
                            ], spacing=8),
                            ft.Container(height=16),
                            ft.Divider(height=1, color=COLORS["border"]),
                            ft.Container(height=8),
                            ft.ListView(controls=[self.tabla], expand=True, auto_scroll=False)
                        ], spacing=0, expand=True),
                        bgcolor=COLORS["bg_white"],
                        border_radius=12,
                        border=ft.border.all(1, COLORS["border"]),
                        padding=24,
                        expand=True
                    )
                ], spacing=0, expand=True),
                expand=True,
                padding=ft.padding.symmetric(horizontal=24, vertical=0)
            )
        ], expand=True, spacing=0)
    
    def _on_buscar(self, e):
        """Callback de búsqueda"""
        self._cargar_tabla(filtro=e.control.value)
    
    def _cargar_tabla(self, filtro=None):
        """Carga datos en la tabla"""
        if not self.service:
            return
            
        self.tabla.rows.clear()
        df = self.service.listar(filtro=filtro, limite=100)
        
        for _, row in df.iterrows():
            codigo_erp = str(row.get('Código Servicio de la ERP', ''))
            codigo_dgh = str(row.get('Código producto en DGH', ''))
            cod_serv_fact = str(row.get('COD_SERV_FACT', ''))
            
            self.tabla.rows.append(
                ft.DataRow(cells=[
                    ft.DataCell(ft.Text(codigo_erp, size=13, color=COLORS["text_primary"])),
                    ft.DataCell(ft.Text(codigo_dgh, size=13, color=COLORS["text_primary"])),
                    ft.DataCell(ft.Text(cod_serv_fact, size=13, color=COLORS["text_secondary"])),
                    ft.DataCell(
                        ft.IconButton(
                            icon=ft.Icons.DELETE_OUTLINE,
                            icon_color=COLORS["text_secondary"],
                            icon_size=18,
                            tooltip="Eliminar",
                            data=codigo_erp,
                            on_click=self._on_eliminar
                        )
                    )
                ])
            )
        
        if filtro:
            self.status_text.value = f"{len(df)} resultados"
            self.status_text.color = COLORS["text_secondary"]
        else:
            self.status_text.value = ""
        
        self.page.update()
    
    def _on_agregar(self, e):
        """Callback para agregar código"""
        if not self.service:
            return
            
        codigo_erp = self.codigo_erp_field.value.strip()
        codigo_dgh = self.codigo_dgh_field.value.strip()
        
        if not codigo_erp or not codigo_dgh:
            self.status_text.value = "❌ Completa ambos campos"
            self.status_text.color = COLORS["error"]
            self.page.update()
            return
        
        if self.service.agregar(codigo_erp, codigo_dgh):
            self.status_text.value = f"✅ Código {codigo_erp} agregado"
            self.status_text.color = COLORS["success"]
            self.codigo_erp_field.value = ""
            self.codigo_dgh_field.value = ""
            self._cargar_tabla()
            self._actualizar_estadisticas()
        else:
            self.status_text.value = f"⚠️ El código {codigo_erp} ya existe"
            self.status_text.color = COLORS["warning"]
        
        self.page.update()
    
    def _on_eliminar(self, e):
        """Callback para eliminar código"""
        if not self.service:
            return
            
        codigo = e.control.data
        
        def confirmar(e):
            self.page.close(dialog)
            if self.service.eliminar(codigo):
                self.status_text.value = f"✅ Código {codigo} eliminado"
                self.status_text.color = COLORS["success"]
                self._cargar_tabla()
                self._actualizar_estadisticas()
            else:
                self.status_text.value = f"❌ Error eliminando {codigo}"
                self.status_text.color = COLORS["error"]
            self.page.update()
        
        dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text("Eliminar código", size=16, weight=ft.FontWeight.W_500),
            content=ft.Text(f"¿Eliminar el código {codigo}?", size=14),
            actions=[
                ft.TextButton("Cancelar", style=ft.ButtonStyle(color=COLORS["text_secondary"]),
                             on_click=lambda e: self.page.close(dialog)),
                ft.TextButton("Eliminar", style=ft.ButtonStyle(color=COLORS["error"]),
                             on_click=confirmar)
            ],
            actions_alignment=ft.MainAxisAlignment.END,
            shape=ft.RoundedRectangleBorder(radius=12)
        )
        self.page.open(dialog)
    
    def _actualizar_estadisticas(self):
        """Actualiza las estadísticas"""
        if self.service:
            stats = self.service.get_estadisticas()
            self.stats_text.value = f"{stats['total']} códigos"
            self.page.update()
    
    def _cargar_eps_disponibles(self):
        """Carga las EPS disponibles en el selector"""
        self.eps_cards_column.controls.clear()
        
        eps_list = HomologacionService.get_eps_disponibles()
        
        if not eps_list:
            self.eps_cards_column.controls.append(
                ft.Text(
                    "No se encontraron archivos de homologación",
                    size=14,
                    color=COLORS["text_secondary"]
                )
            )
        else:
            for eps_info in eps_list:
                self.eps_cards_column.controls.append(
                    self._create_eps_card(eps_info)
                )
        
        self.page.update()
    
    def show(self):
        """Muestra la vista"""
        # Siempre empezar en el selector de EPS
        self.current_eps = None
        self.service = None
        self.container.content = self.eps_selector_view
        self._cargar_eps_disponibles()
        self.container.visible = True
        self.page.update()
    
    def hide(self):
        """Oculta la vista"""
        self.container.visible = False
        self.page.update()
