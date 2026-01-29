"""
Vista para gestionar códigos de homologación - Estilo Minimalista
Con soporte para múltiples EPS y temas claro/oscuro
"""
import flet as ft
import pandas as pd
from app.ui.styles import FONT_SIZES, SPACING
from app.ui.components.navigation_header import NavigationHeader
from app.core.homologacion_service import HomologacionService


class HomologacionView:
    """Vista para CRUD de códigos de homologación con selector de EPS"""
    
    def __init__(self, page: ft.Page, navigation_controller=None, on_back=None):
        self.page = page
        self.navigation_controller = navigation_controller
        self.on_back = on_back
        self.nav_header = NavigationHeader(page, navigation_controller)
        self.service = None  # Se inicializa cuando se selecciona una EPS
        self.current_eps = None
        
        # Vista de selección de EPS
        self.eps_selector_view = self._build_eps_selector()
        
        # Vista de gestión de códigos (inicialmente no construida)
        self.gestion_view = None
        
        # Container principal que alterna entre vistas
        self.container = ft.Container(
            content=self.eps_selector_view,
            bgcolor=ft.Colors.SURFACE,
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
                        icon_size=18,
                        tooltip="Volver",
                        on_click=lambda e: self.on_back() if self.on_back else None
                    ),
                    ft.Text("Homologación", 
                           size=18,
                           weight=ft.FontWeight.W_500),
                ], alignment=ft.MainAxisAlignment.START, spacing=8),
                padding=ft.padding.symmetric(horizontal=24, vertical=16),
            ),
            
            # Contenido
            ft.Container(
                content=ft.Column([
                    ft.Container(height=20),
                    ft.Text("Selecciona una EPS", 
                           size=16, 
                           weight=ft.FontWeight.W_500),
                    ft.Text("Cada EPS tiene su propio archivo de homologación",
                           size=13),
                    ft.Container(height=24),
                    self.eps_cards_column
                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                expand=True,
                padding=ft.padding.symmetric(horizontal=24)
            )
        ], expand=True, spacing=0)
    
    def _create_eps_card(self, eps_info):
        """Crea una tarjeta para seleccionar una EPS usando Card de Flet"""
        def on_click(e):
            self._seleccionar_eps(eps_info["key"])
        
        # Colores por EPS
        colores = {
            "mutualser": "#2196F3",
            "coosalud": "#4CAF50"
        }
        color = colores.get(eps_info["key"], ft.Colors.PRIMARY)
        
        card = ft.Card(
            content=ft.Container(
                content=ft.Row([
                    ft.Container(
                        content=ft.Text(
                            eps_info["name"][0],  # Primera letra
                            size=24,
                            weight=ft.FontWeight.BOLD,
                            color=ft.Colors.WHITE
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
                            weight=ft.FontWeight.W_600
                        ),
                        ft.Text(
                            f"{eps_info['count']} códigos de homologación",
                            size=12
                        )
                    ], spacing=2, alignment=ft.MainAxisAlignment.CENTER),
                    ft.Container(expand=True),
                    ft.Icon(ft.Icons.ARROW_FORWARD_IOS, size=16)
                ]),
                padding=20,
                on_click=on_click,
                ink=True,
                width=400
            ),
            elevation=2,
        )
        return card
    
    def _seleccionar_eps(self, eps_key):
        """Selecciona una EPS y muestra la vista de gestión"""
        self.current_eps = eps_key
        self.service = HomologacionService(eps=eps_key)
        
        # Variables para carga masiva
        self.archivo_carga_masiva = None
        self.df_carga_masiva = None
        self.resultado_verificacion = None
        
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
        # Campos de formulario para agregar individual
        self.codigo_erp_field = ft.TextField(
            label="Código ERP",
            hint_text="881141",
            hint_style=ft.TextStyle(color="#000000"),
            color="#000000",
            border_color=ft.Colors.OUTLINE,
            focused_border_color=ft.Colors.PRIMARY,
            border_radius=8,
            content_padding=ft.padding.symmetric(horizontal=16, vertical=12),
            text_size=14,
            label_style=ft.TextStyle(size=12, color=ft.Colors.ON_SURFACE_VARIANT),
            expand=True
        )
        
        self.codigo_dgh_field = ft.TextField(
            label="Código DGH",
            hint_text="881141",
            hint_style=ft.TextStyle(color="#000000"),
            color="#000000",
            border_color=ft.Colors.OUTLINE,
            focused_border_color=ft.Colors.PRIMARY,
            border_radius=8,
            content_padding=ft.padding.symmetric(horizontal=16, vertical=12),
            text_size=14,
            label_style=ft.TextStyle(size=12, color=ft.Colors.ON_SURFACE_VARIANT),
            expand=True
        )
        
        self.buscar_field = ft.TextField(
            hint_text="Buscar código...",
            hint_style=ft.TextStyle(color="#000000"),
            color="#000000",
            border_color=ft.Colors.OUTLINE,
            focused_border_color=ft.Colors.PRIMARY,
            border_radius=8,
            content_padding=ft.padding.symmetric(horizontal=16, vertical=12),
            text_size=14,
            prefix_icon=ft.Icons.SEARCH,
            expand=True,
            on_change=self._on_buscar
        )
        
        # Determinar si mostrar columna COD_SERV_FACT (solo Mutualser)
        mostrar_cod_serv_fact = self.current_eps == "mutualser"
        
        # Tabla de códigos existentes - columnas según EPS
        columnas_tabla = [
            ft.DataColumn(ft.Text("Código ERP", size=12, weight=ft.FontWeight.W_500, color=ft.Colors.ON_SURFACE_VARIANT), numeric=False),
            ft.DataColumn(ft.Text("Código DGH", size=12, weight=ft.FontWeight.W_500, color=ft.Colors.ON_SURFACE_VARIANT), numeric=False),
        ]
        if mostrar_cod_serv_fact:
            columnas_tabla.append(ft.DataColumn(ft.Text("COD_SERV_FACT", size=12, weight=ft.FontWeight.W_500, color=ft.Colors.ON_SURFACE_VARIANT), numeric=False))
        columnas_tabla.append(ft.DataColumn(ft.Text("", size=12)))
        
        self.mostrar_cod_serv_fact = mostrar_cod_serv_fact
        
        self.tabla = ft.DataTable(
            columns=columnas_tabla,
            rows=[],
            border=ft.border.all(1, ft.Colors.OUTLINE),
            border_radius=12,
            heading_row_color=ft.Colors.SURFACE_CONTAINER_HIGHEST,
            heading_row_height=50,
            data_row_max_height=48,
            data_row_min_height=44,
            column_spacing=40,
            horizontal_lines=ft.BorderSide(1, ft.Colors.OUTLINE),
            show_checkbox_column=False,
            expand=True
        )
        
        # Status
        self.status_text = ft.Text("", size=12, color=ft.Colors.ON_SURFACE_VARIANT)
        self.stats_text = ft.Text("", size=13, color=ft.Colors.ON_SURFACE_VARIANT)
        
        # Colores por EPS
        colores = {
            "mutualser": "#2196F3",
            "coosalud": "#4CAF50"
        }
        eps_color = colores.get(self.current_eps or "", ft.Colors.PRIMARY)
        
        # ==================== ELEMENTOS PARA CARGA MASIVA ====================
        self.archivo_nombre_text = ft.Text(
            "Ningún archivo seleccionado",
            size=13,
            color=ft.Colors.ON_SURFACE_VARIANT,
            italic=True
        )
        
        self.masiva_status_text = ft.Text("", size=12, color=ft.Colors.ON_SURFACE_VARIANT)
        
        # Tabla de verificación masiva
        self.tabla_verificacion = ft.DataTable(
            columns=[
                ft.DataColumn(ft.Text("Estado", size=12, weight=ft.FontWeight.W_500, color=ft.Colors.ON_SURFACE_VARIANT)),
                ft.DataColumn(ft.Text("Código EPS", size=12, weight=ft.FontWeight.W_500, color=ft.Colors.ON_SURFACE_VARIANT)),
                ft.DataColumn(ft.Text("Código Homólogo", size=12, weight=ft.FontWeight.W_500, color=ft.Colors.ON_SURFACE_VARIANT)),
                ft.DataColumn(ft.Text("Detalle", size=12, weight=ft.FontWeight.W_500, color=ft.Colors.ON_SURFACE_VARIANT)),
            ],
            rows=[],
            border=ft.border.all(1, ft.Colors.OUTLINE),
            border_radius=12,
            heading_row_color=ft.Colors.SURFACE_CONTAINER_HIGHEST,
            heading_row_height=50,
            data_row_max_height=48,
            data_row_min_height=44,
            column_spacing=30,
            horizontal_lines=ft.BorderSide(1, ft.Colors.OUTLINE),
            show_checkbox_column=False,
            expand=True
        )
        
        # Resumen de verificación
        self.resumen_validos = ft.Text("0 válidos", size=13, color=ft.Colors.GREEN)
        self.resumen_duplicados = ft.Text("0 duplicados", size=13, color=ft.Colors.ORANGE)
        self.resumen_errores = ft.Text("0 errores", size=13, color=ft.Colors.RED)
        
        # Botón agregar masivo (inicialmente deshabilitado)
        self.btn_agregar_masivo = ft.ElevatedButton(
            content=ft.Row([
                ft.Icon(ft.Icons.PLAYLIST_ADD_CHECK, size=18, color=ft.Colors.SURFACE),
                ft.Text("Agregar válidos", size=13, weight=ft.FontWeight.W_500)
            ], spacing=6),
            bgcolor=eps_color,
            color=ft.Colors.SURFACE,
            elevation=0,
            disabled=True,
            style=ft.ButtonStyle(
                shape=ft.RoundedRectangleBorder(radius=8),
                padding=ft.padding.symmetric(horizontal=20, vertical=12)
            ),
            on_click=self._on_agregar_masivo
        )
        
        # FilePicker
        self.file_picker = ft.FilePicker(on_result=self._on_archivo_seleccionado)
        self.page.overlay.append(self.file_picker)
        
        # ==================== TABS ====================
        # Tab Individual
        tab_individual = ft.Tab(
            text="Individual",
            icon=ft.Icons.PERSON,
            content=ft.Container(
                content=ft.Column([
                    # Card agregar
                    ft.Container(
                        content=ft.Column([
                            ft.Text("Nuevo código", 
                                   size=14, 
                                   weight=ft.FontWeight.W_500,
                                   color=ft.Colors.ON_SURFACE),
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
                                        ft.Icon(ft.Icons.ADD, size=16, color=ft.Colors.SURFACE),
                                        ft.Text("Agregar", size=13, weight=ft.FontWeight.W_500)
                                    ], spacing=6),
                                    bgcolor=eps_color,
                                    color=ft.Colors.SURFACE,
                                    elevation=0,
                                    style=ft.ButtonStyle(
                                        shape=ft.RoundedRectangleBorder(radius=8),
                                        padding=ft.padding.symmetric(horizontal=20, vertical=12)
                                    ),
                                    on_click=self._on_agregar
                                )
                            ], alignment=ft.MainAxisAlignment.END)
                        ], spacing=0),
                        bgcolor=ft.Colors.SURFACE,
                        border_radius=12,
                        border=ft.border.all(1, ft.Colors.OUTLINE),
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
                                    icon_color=ft.Colors.ON_SURFACE_VARIANT,
                                    icon_size=20,
                                    tooltip="Actualizar",
                                    on_click=lambda e: self._cargar_tabla()
                                )
                            ], spacing=8),
                            ft.Container(height=16),
                            ft.Divider(height=1, color=ft.Colors.OUTLINE),
                            ft.Container(height=8),
                            ft.ListView(controls=[self.tabla], expand=True, auto_scroll=False)
                        ], spacing=0, expand=True),
                        bgcolor=ft.Colors.SURFACE,
                        border_radius=12,
                        border=ft.border.all(1, ft.Colors.OUTLINE),
                        padding=24,
                        expand=True
                    )
                ], spacing=0, expand=True),
                padding=ft.padding.only(top=16),
                expand=True
            )
        )
        
        # Tab Masiva
        tab_masiva = ft.Tab(
            text="Carga Masiva",
            icon=ft.Icons.UPLOAD_FILE,
            content=ft.Container(
                content=ft.Column([
                    # Card cargar archivo
                    ft.Container(
                        content=ft.Column([
                            ft.Row([
                                ft.Icon(ft.Icons.INFO_OUTLINE, size=18, color=ft.Colors.PRIMARY),
                                ft.Text("Carga masiva de códigos", 
                                       size=14, 
                                       weight=ft.FontWeight.W_500,
                                       color=ft.Colors.ON_SURFACE),
                            ], spacing=8),
                            ft.Container(height=8),
                            ft.Text(
                                "Selecciona un archivo Excel con 2 columnas:\n• Columna 1: Código EPS (código de la glosa)\n• Columna 2: Código Homólogo (código DGH)",
                                size=12,
                                color=ft.Colors.ON_SURFACE_VARIANT
                            ),
                            ft.Container(height=16),
                            ft.Row([
                                ft.OutlinedButton(
                                    content=ft.Row([
                                        ft.Icon(ft.Icons.FOLDER_OPEN, size=16),
                                        ft.Text("Seleccionar archivo", size=13)
                                    ], spacing=6),
                                    style=ft.ButtonStyle(
                                        shape=ft.RoundedRectangleBorder(radius=8),
                                        padding=ft.padding.symmetric(horizontal=16, vertical=12)
                                    ),
                                    on_click=lambda e: self.file_picker.pick_files(
                                        allowed_extensions=["xlsx", "xls"],
                                        dialog_title="Seleccionar archivo de homologación"
                                    )
                                ),
                                ft.Container(width=12),
                                self.archivo_nombre_text
                            ], alignment=ft.MainAxisAlignment.START),
                        ], spacing=0),
                        bgcolor=ft.Colors.SURFACE,
                        border_radius=12,
                        border=ft.border.all(1, ft.Colors.OUTLINE),
                        padding=24
                    ),
                    
                    ft.Container(height=16),
                    
                    # Card verificación y resultados
                    ft.Container(
                        content=ft.Column([
                            ft.Row([
                                ft.Text("Verificación", 
                                       size=14, 
                                       weight=ft.FontWeight.W_500,
                                       color=ft.Colors.ON_SURFACE),
                                ft.Container(expand=True),
                                self.resumen_validos,
                                ft.Container(width=16),
                                self.resumen_duplicados,
                                ft.Container(width=16),
                                self.resumen_errores,
                            ], alignment=ft.MainAxisAlignment.START),
                            ft.Container(height=12),
                            ft.Divider(height=1, color=ft.Colors.OUTLINE),
                            ft.Container(height=8),
                            ft.ListView(controls=[self.tabla_verificacion], expand=True, auto_scroll=False),
                            ft.Container(height=12),
                            ft.Row([
                                self.masiva_status_text,
                                ft.Container(expand=True),
                                self.btn_agregar_masivo
                            ], alignment=ft.MainAxisAlignment.END)
                        ], spacing=0, expand=True),
                        bgcolor=ft.Colors.SURFACE,
                        border_radius=12,
                        border=ft.border.all(1, ft.Colors.OUTLINE),
                        padding=24,
                        expand=True
                    )
                ], spacing=0, expand=True),
                padding=ft.padding.only(top=16),
                expand=True
            )
        )
        
        # Tabs container
        self.tabs = ft.Tabs(
            selected_index=0,
            tabs=[tab_individual, tab_masiva],
            expand=True,
            indicator_color=eps_color,
            label_color=eps_color,
            unselected_label_color=ft.Colors.ON_SURFACE_VARIANT
        )
        
        return ft.Column([
            # Header con nombre de EPS
            ft.Container(
                content=ft.Row([
                    ft.IconButton(
                        icon=ft.Icons.ARROW_BACK_IOS_NEW,
                        icon_color=ft.Colors.ON_SURFACE_VARIANT,
                        icon_size=18,
                        tooltip="Volver a EPS",
                        on_click=lambda e: self._volver_a_selector()
                    ),
                    ft.Container(
                        content=ft.Text(
                            (self.current_eps or "H")[0].upper(),
                            size=14,
                            weight=ft.FontWeight.BOLD,
                            color=ft.Colors.SURFACE
                        ),
                        width=32,
                        height=32,
                        border_radius=8,
                        bgcolor=eps_color,
                        alignment=ft.alignment.center
                    ),
                    ft.Text(f"Homologación {(self.current_eps or '').upper()}", 
                           size=18,
                           weight=ft.FontWeight.W_500,
                           color=ft.Colors.ON_SURFACE),
                    ft.Container(expand=True),
                    self.stats_text
                ], alignment=ft.MainAxisAlignment.START, spacing=8),
                padding=ft.padding.symmetric(horizontal=24, vertical=16),
            ),
            
            # Tabs con contenido
            ft.Container(
                content=self.tabs,
                expand=True,
                padding=ft.padding.symmetric(horizontal=24, vertical=0)
            )
        ], expand=True, spacing=0)
    
    def _on_buscar(self, e):
        """Callback de búsqueda"""
        self._cargar_tabla(filtro=e.control.value)
    
    def _cargar_tabla(self, filtro=None):
        """Carga datos en la tabla"""
        if not self.service or self.tabla is None:  # type: ignore
            return
            
        self.tabla.rows.clear()  # type: ignore
        df = self.service.listar(filtro=filtro, limite=100)
        
        for _, row in df.iterrows():
            codigo_erp = str(row.get('Código Servicio de la ERP', ''))
            codigo_dgh = str(row.get('Código producto en DGH', ''))
            
            # Crear celdas según columnas de la EPS
            celdas = [
                ft.DataCell(ft.Text(codigo_erp, size=13, color=ft.Colors.ON_SURFACE_VARIANT)),
                ft.DataCell(ft.Text(codigo_dgh, size=13, color=ft.Colors.ON_SURFACE_VARIANT)),
            ]
            
            # Solo agregar COD_SERV_FACT si es Mutualser
            if self.mostrar_cod_serv_fact:
                cod_serv_fact = str(row.get('COD_SERV_FACT', ''))
                celdas.append(ft.DataCell(ft.Text(cod_serv_fact, size=13, color=ft.Colors.ON_SURFACE_VARIANT)))
            
            # Botón de eliminar
            celdas.append(ft.DataCell(
                ft.IconButton(
                    icon=ft.Icons.DELETE_OUTLINE,
                    icon_color=ft.Colors.ON_SURFACE_VARIANT,
                    icon_size=18,
                    tooltip="Eliminar",
                    data=codigo_erp,
                    on_click=self._on_eliminar
                )
            ))
            
            self.tabla.rows.append(ft.DataRow(cells=celdas))  # type: ignore
        
        if filtro:
            self.status_text.value = f"{len(df)} resultados"  # type: ignore
            self.status_text.color = ft.Colors.ON_SURFACE_VARIANT  # type: ignore
        else:
            self.status_text.value = ""  # type: ignore
        
        self.page.update()
    
    def _on_agregar(self, e):
        """Callback para agregar código"""
        if not self.service:
            return
            
        codigo_erp = self.codigo_erp_field.value.strip() if self.codigo_erp_field else ""  # type: ignore
        codigo_dgh = self.codigo_dgh_field.value.strip() if self.codigo_dgh_field else ""  # type: ignore
        
        if not codigo_erp or not codigo_dgh:
            self.status_text.value = "❌ Completa ambos campos"  # type: ignore
            self.status_text.color = ft.Colors.RED  # type: ignore
            self.page.update()
            return
        
        if self.service.agregar(codigo_erp, codigo_dgh):  # type: ignore
            self.status_text.value = f"✅ Código {codigo_erp} agregado"  # type: ignore
            self.status_text.color = ft.Colors.GREEN  # type: ignore
            self.codigo_erp_field.value = ""  # type: ignore
            self.codigo_dgh_field.value = ""  # type: ignore
            self._cargar_tabla()
            self._actualizar_estadisticas()
        else:
            self.status_text.value = f"⚠️ El código {codigo_erp} ya existe"  # type: ignore
            self.status_text.color = ft.Colors.ORANGE  # type: ignore
        
        self.page.update()
    
    def _on_eliminar(self, e):
        """Callback para eliminar código"""
        if not self.service:
            return
            
        codigo = e.control.data
        
        def confirmar(e):
            self.page.close(dialog)
            if self.service.eliminar(codigo):  # type: ignore
                self.status_text.value = f"✅ Código {codigo} eliminado"  # type: ignore
                self.status_text.color = ft.Colors.GREEN  # type: ignore
                self._cargar_tabla()
                self._actualizar_estadisticas()
            else:
                self.status_text.value = f"❌ Error eliminando {codigo}"  # type: ignore
                self.status_text.color = ft.Colors.RED  # type: ignore
            self.page.update()
        
        dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text("Eliminar código", size=16, weight=ft.FontWeight.W_500),
            content=ft.Text(f"¿Eliminar el código {codigo}?", size=14),
            actions=[
                ft.TextButton("Cancelar", style=ft.ButtonStyle(color=ft.Colors.ON_SURFACE_VARIANT),
                             on_click=lambda e: self.page.close(dialog)),
                ft.TextButton("Eliminar", style=ft.ButtonStyle(color=ft.Colors.RED),
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
                    color=ft.Colors.ON_SURFACE_VARIANT
                )
            )
        else:
            for eps_info in eps_list:
                self.eps_cards_column.controls.append(
                    self._create_eps_card(eps_info)
                )
        
        self.page.update()
    
    # ==================== MÉTODOS PARA CARGA MASIVA ====================
    
    def _on_archivo_seleccionado(self, e):
        """Callback cuando se selecciona un archivo para carga masiva"""
        if not e.files or len(e.files) == 0:
            return
        
        archivo = e.files[0]
        self.archivo_carga_masiva = archivo.path
        self.archivo_nombre_text.value = archivo.name
        self.archivo_nombre_text.italic = False
        self.archivo_nombre_text.color = ft.Colors.ON_SURFACE
        
        # Leer y verificar el archivo
        self._verificar_archivo_masivo()
        self.page.update()
    
    def _verificar_archivo_masivo(self):
        """Verifica el archivo de carga masiva"""
        if not self.archivo_carga_masiva or not self.service:
            return
        
        try:
            # Leer archivo Excel
            self.df_carga_masiva = pd.read_excel(self.archivo_carga_masiva)
            
            if self.df_carga_masiva.empty:
                self._mostrar_alerta_masiva("Archivo vacío", "El archivo seleccionado no contiene datos.", "error")
                return
            
            # Verificar con el servicio
            self.resultado_verificacion = self.service.verificar_carga_masiva(self.df_carga_masiva)
            
            # Actualizar resumen
            num_validos = len(self.resultado_verificacion['validos'])
            num_duplicados_archivo = len(self.resultado_verificacion['duplicados_archivo'])
            num_duplicados_carga = len(self.resultado_verificacion['duplicados_carga'])
            num_errores = len(self.resultado_verificacion['errores'])
            
            self.resumen_validos.value = f"✅ {num_validos} válidos"
            self.resumen_duplicados.value = f"⚠️ {num_duplicados_archivo + num_duplicados_carga} duplicados"
            self.resumen_errores.value = f"❌ {num_errores} errores"
            
            # Cargar tabla de verificación
            self._cargar_tabla_verificacion()
            
            # Habilitar/deshabilitar botón
            self.btn_agregar_masivo.disabled = num_validos == 0
            
            # Mostrar alertas si hay problemas
            if num_duplicados_archivo > 0 or num_duplicados_carga > 0:
                self._mostrar_alerta_masiva(
                    "Códigos duplicados encontrados",
                    f"Se encontraron {num_duplicados_archivo} códigos que ya existen en el archivo de homologación y {num_duplicados_carga} códigos duplicados en el archivo de carga.\n\nEstos serán omitidos.",
                    "warning"
                )
            
            if num_errores > 0:
                errores_texto = "\n".join(self.resultado_verificacion['errores'][:5])
                if num_errores > 5:
                    errores_texto += f"\n... y {num_errores - 5} errores más"
                self._mostrar_alerta_masiva(
                    "Errores en el archivo",
                    f"Se encontraron {num_errores} errores:\n\n{errores_texto}",
                    "error"
                )
            
            self.masiva_status_text.value = f"Archivo verificado: {len(self.df_carga_masiva)} registros"
            self.masiva_status_text.color = ft.Colors.ON_SURFACE_VARIANT
            
        except Exception as ex:
            self._mostrar_alerta_masiva(
                "Error leyendo archivo",
                f"No se pudo leer el archivo:\n{str(ex)}",
                "error"
            )
            self.masiva_status_text.value = "❌ Error al leer archivo"
            self.masiva_status_text.color = ft.Colors.RED
        
        self.page.update()
    
    def _cargar_tabla_verificacion(self):
        """Carga la tabla de verificación con los resultados"""
        if self.tabla_verificacion is None:  # type: ignore
            return
        self.tabla_verificacion.rows.clear()  # type: ignore
        
        if not self.resultado_verificacion:
            return
        
        # Agregar válidos
        for codigo_eps, codigo_homologo in self.resultado_verificacion['validos'][:50]:
            self.tabla_verificacion.rows.append(  # type: ignore
                ft.DataRow(cells=[
                    ft.DataCell(ft.Container(
                        content=ft.Icon(ft.Icons.CHECK_CIRCLE, size=16, color=ft.Colors.GREEN),
                        tooltip="Válido para agregar"
                    )),
                    ft.DataCell(ft.Text(codigo_eps, size=12, color=ft.Colors.ON_SURFACE)),
                    ft.DataCell(ft.Text(codigo_homologo, size=12, color=ft.Colors.ON_SURFACE)),
                    ft.DataCell(ft.Text("Listo para agregar", size=11, color=ft.Colors.GREEN)),
                ])
            )
        
        # Agregar duplicados del archivo
        for dup in self.resultado_verificacion['duplicados_archivo'][:20]:
            self.tabla_verificacion.rows.append(  # type: ignore
                ft.DataRow(cells=[
                    ft.DataCell(ft.Container(
                        content=ft.Icon(ft.Icons.WARNING_AMBER, size=16, color=ft.Colors.ORANGE),
                        tooltip="Ya existe en archivo"
                    )),
                    ft.DataCell(ft.Text(dup['codigo'], size=12, color=ft.Colors.ON_SURFACE_VARIANT)),
                    ft.DataCell(ft.Text(dup['homologo_nuevo'], size=12, color=ft.Colors.ON_SURFACE_VARIANT)),
                    ft.DataCell(ft.Text(f"Ya existe en homologación", size=11, color=ft.Colors.ORANGE)),
                ])
            )
        
        # Agregar duplicados de la carga
        for dup in self.resultado_verificacion['duplicados_carga'][:10]:
            self.tabla_verificacion.rows.append(  # type: ignore
                ft.DataRow(cells=[
                    ft.DataCell(ft.Container(
                        content=ft.Icon(ft.Icons.CONTENT_COPY, size=16, color=ft.Colors.ORANGE),
                        tooltip="Duplicado en carga"
                    )),
                    ft.DataCell(ft.Text(dup['codigo'], size=12, color=ft.Colors.ON_SURFACE_VARIANT)),
                    ft.DataCell(ft.Text(dup.get('homologo', '-'), size=12, color=ft.Colors.ON_SURFACE_VARIANT)),
                    ft.DataCell(ft.Text(f"Duplicado fila {dup['fila_original']} y {dup['fila_duplicada']}", size=11, color=ft.Colors.ORANGE)),
                ])
            )
        
        # Mostrar mensaje si hay más registros
        total_mostrados = min(50, len(self.resultado_verificacion['validos'])) + \
                          min(20, len(self.resultado_verificacion['duplicados_archivo'])) + \
                          min(10, len(self.resultado_verificacion['duplicados_carga']))
        total_registros = len(self.resultado_verificacion['validos']) + \
                          len(self.resultado_verificacion['duplicados_archivo']) + \
                          len(self.resultado_verificacion['duplicados_carga'])
        
        if total_mostrados < total_registros:
            self.masiva_status_text.value = f"Mostrando {total_mostrados} de {total_registros} registros"  # type: ignore
    
    def _on_agregar_masivo(self, e):
        """Callback para agregar códigos masivamente"""
        if not self.service or not self.resultado_verificacion:
            return
        
        validos = self.resultado_verificacion['validos']
        if not validos:
            self._mostrar_alerta_masiva(
                "Sin códigos válidos",
                "No hay códigos válidos para agregar.",
                "warning"
            )
            return
        
        # Confirmar antes de agregar
        def confirmar(e):
            self.page.close(dialog)
            self._ejecutar_carga_masiva()
        
        dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text("Confirmar carga masiva", size=16, weight=ft.FontWeight.W_500),
            content=ft.Text(
                f"¿Agregar {len(validos)} códigos al archivo de homologación?\n\nEsta acción no se puede deshacer.",
                size=14
            ),
            actions=[
                ft.TextButton("Cancelar", 
                             style=ft.ButtonStyle(color=ft.Colors.ON_SURFACE_VARIANT),
                             on_click=lambda e: self.page.close(dialog)),
                ft.ElevatedButton("Agregar", 
                                 bgcolor=ft.Colors.PRIMARY,
                                 color=ft.Colors.SURFACE,
                                 on_click=confirmar)
            ],
            actions_alignment=ft.MainAxisAlignment.END,
            shape=ft.RoundedRectangleBorder(radius=12)
        )
        self.page.open(dialog)
    
    def _ejecutar_carga_masiva(self):
        """Ejecuta la carga masiva de códigos"""
        if not self.service or not self.resultado_verificacion:
            return
        
        validos = self.resultado_verificacion['validos']
        resultado = self.service.agregar_masivo(validos)
        
        if resultado['agregados'] > 0:
            self._mostrar_alerta_masiva(
                "Carga completada",
                f"Se agregaron {resultado['agregados']} códigos correctamente al archivo de homologación.",
                "success"
            )
            
            # Limpiar estado
            self.archivo_carga_masiva = None
            self.df_carga_masiva = None
            self.resultado_verificacion = None
            self.archivo_nombre_text.value = "Ningún archivo seleccionado"  # type: ignore
            self.archivo_nombre_text.italic = True  # type: ignore
            self.archivo_nombre_text.color = ft.Colors.ON_SURFACE_VARIANT  # type: ignore
            if self.tabla_verificacion:  # type: ignore
                self.tabla_verificacion.rows.clear()  # type: ignore
            self.resumen_validos.value = "0 válidos"  # type: ignore
            self.resumen_duplicados.value = "0 duplicados"  # type: ignore
            self.resumen_errores.value = "0 errores"  # type: ignore
            self.btn_agregar_masivo.disabled = True  # type: ignore
            self.masiva_status_text.value = ""  # type: ignore
            
            # Actualizar tabla principal y estadísticas
            self._cargar_tabla()
            self._actualizar_estadisticas()
        else:
            errores_texto = "\n".join(resultado.get('errores', ['Error desconocido']))
            self._mostrar_alerta_masiva(
                "Error en carga",
                f"No se pudieron agregar los códigos:\n{errores_texto}",
                "error"
            )
        
        self.page.update()
    
    def _mostrar_alerta_masiva(self, titulo, mensaje, tipo="info"):
        """Muestra un diálogo de alerta para la carga masiva"""
        iconos = {
            "success": (ft.Icons.CHECK_CIRCLE, ft.Colors.GREEN),
            "warning": (ft.Icons.WARNING_AMBER, ft.Colors.ORANGE),
            "error": (ft.Icons.ERROR, ft.Colors.RED),
            "info": (ft.Icons.INFO, ft.Colors.PRIMARY)
        }
        icono, color = iconos.get(tipo, iconos["info"])
        
        dialog = ft.AlertDialog(
            modal=True,
            title=ft.Row([
                ft.Icon(icono, size=24, color=color),
                ft.Container(width=8),
                ft.Text(titulo, size=16, weight=ft.FontWeight.W_500)
            ]),
            content=ft.Text(mensaje, size=13),
            actions=[
                ft.TextButton("Aceptar", 
                             style=ft.ButtonStyle(color=color),
                             on_click=lambda e: self.page.close(dialog))
            ],
            actions_alignment=ft.MainAxisAlignment.END,
            shape=ft.RoundedRectangleBorder(radius=12)
        )
        self.page.open(dialog)
    
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
