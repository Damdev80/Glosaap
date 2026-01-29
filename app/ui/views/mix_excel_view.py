"""
Vista Mix Excel - Transferencia de datos entre archivos Excel
Estilo Minimalista con soporte de temas
"""
import flet as ft
from pathlib import Path
from app.ui.styles import FONT_SIZES, SPACING
from app.ui.components.navigation_header import NavigationHeader
from app.core.mix_excel_service import MixExcelService


class MixExcelView:
    """Vista para transferir columnas entre archivos Excel"""
    
    def __init__(self, page: ft.Page, navigation_controller=None, on_back=None):
        self.page = page
        self.navigation_controller = navigation_controller
        self.on_back = on_back
        self.nav_header = NavigationHeader(page, navigation_controller)
        self.service = MixExcelService()
        
        # File picker
        self.file_picker = ft.FilePicker(on_result=self._on_file_picked)
        self.page.overlay.append(self.file_picker)
        self.current_picker_type = None
        
        # Textos de archivos seleccionados
        self.source_file_text = ft.Text(
            "Ningún archivo seleccionado", 
            size=12, 
            color=ft.Colors.ON_SURFACE_VARIANT
        )
        self.dest_file_text = ft.Text(
            "Ningún archivo seleccionado", 
            size=12, 
            color=ft.Colors.ON_SURFACE_VARIANT
        )
        
        # Dropdowns - Origen
        self.source_ref_dropdown = self._create_dropdown("Columna referencia (factura)")
        self.source_col_dropdown = self._create_dropdown("Columna con valores")
        
        # Dropdowns - Destino
        self.dest_ref_dropdown = self._create_dropdown("Columna referencia (factura)")
        self.dest_adjacent_dropdown = self._create_dropdown("Columna adyacente (proporción)")
        self.dest_col_dropdown = self._create_dropdown("Columna destino")
        
        # Tolerancia
        self.tolerance_field = ft.TextField(
            label="Tolerancia %",
            value="5",
            width=100,
            border_color=ft.Colors.OUTLINE,
            focused_border_color=ft.Colors.PRIMARY,
            border_radius=8,
            content_padding=ft.padding.symmetric(horizontal=12, vertical=10),
            text_size=14,
            keyboard_type=ft.KeyboardType.NUMBER
        )
        
        # Status
        self.status_text = ft.Text("", size=13, color=ft.Colors.ON_SURFACE_VARIANT)
        
        # Construir vista
        self.container = self._build()
    
    def _create_dropdown(self, label: str) -> ft.Dropdown:
        """Crea un dropdown estilizado"""
        return ft.Dropdown(
            label=label,
            hint_text="Selecciona...",
            disabled=True,
            border_color=ft.Colors.OUTLINE,
            focused_border_color=ft.Colors.PRIMARY,
            border_radius=8,
            content_padding=ft.padding.symmetric(horizontal=12, vertical=8),
            text_size=13,
            expand=True
        )
    
    def _create_file_button(self, label: str, picker_type: str) -> ft.ElevatedButton:
        """Crea un botón para seleccionar archivo"""
        return ft.ElevatedButton(
            content=ft.Row([
                ft.Icon(ft.Icons.FOLDER_OPEN, size=16),
                ft.Text(label, size=13)
            ], spacing=8),
            bgcolor=ft.Colors.SURFACE_CONTAINER_HIGHEST,
            color=ft.Colors.ON_SURFACE,
            elevation=0,
            style=ft.ButtonStyle(
                shape=ft.RoundedRectangleBorder(radius=8),
                padding=ft.padding.symmetric(horizontal=16, vertical=12),
                side=ft.BorderSide(1, ft.Colors.OUTLINE)
            ),
            on_click=lambda e: self._pick_file(picker_type)
        )
    
    def _build(self):
        """Construye la vista"""
        return ft.Container(
            content=ft.Column([
                # Header
                ft.Container(
                    content=ft.Row([
                        ft.IconButton(
                            icon=ft.Icons.ARROW_BACK_IOS_NEW,
                            icon_color=ft.Colors.ON_SURFACE_VARIANT,
                            icon_size=18,
                            tooltip="Volver",
                            on_click=lambda e: self.on_back()
                        ),
                        ft.Text("Mix Excel", 
                               size=18,
                               weight=ft.FontWeight.W_500,
                               color=ft.Colors.ON_SURFACE),
                        ft.Container(expand=True),
                        ft.Text("Transferencia de datos", 
                               size=12,
                               color=ft.Colors.ON_SURFACE_VARIANT)
                    ], alignment=ft.MainAxisAlignment.START, spacing=8),
                    padding=ft.padding.symmetric(horizontal=24, vertical=16),
                ),
                
                # Contenido con scroll
                ft.Container(
                    content=ft.Column([
                        # Card Archivo Origen
                        ft.Container(
                            content=ft.Column([
                                ft.Row([
                                    ft.Icon(ft.Icons.FILE_UPLOAD, size=20, color=ft.Colors.PRIMARY),
                                    ft.Text("Archivo Origen", 
                                           size=14, 
                                           weight=ft.FontWeight.W_500,
                                           color=ft.Colors.ON_SURFACE)
                                ], spacing=8),
                                ft.Container(height=12),
                                ft.Row([
                                    self._create_file_button("Seleccionar", "source"),
                                    ft.Container(width=12),
                                    self.source_file_text
                                ], alignment=ft.MainAxisAlignment.START),
                                ft.Container(height=16),
                                ft.Divider(height=1, color=ft.Colors.OUTLINE),
                                ft.Container(height=12),
                                self.source_ref_dropdown,
                                ft.Container(height=12),
                                self.source_col_dropdown,
                            ], spacing=0),
                            bgcolor=ft.Colors.SURFACE,
                            border_radius=12,
                            border=ft.border.all(1, ft.Colors.OUTLINE),
                            padding=24
                        ),
                        
                        ft.Container(height=16),
                        
                        # Card Archivo Destino
                        ft.Container(
                            content=ft.Column([
                                ft.Row([
                                    ft.Icon(ft.Icons.FILE_DOWNLOAD, size=20, color=ft.Colors.GREEN),
                                    ft.Text("Archivo Destino", 
                                           size=14, 
                                           weight=ft.FontWeight.W_500,
                                           color=ft.Colors.ON_SURFACE)
                                ], spacing=8),
                                ft.Container(height=12),
                                ft.Row([
                                    self._create_file_button("Seleccionar", "dest"),
                                    ft.Container(width=12),
                                    self.dest_file_text
                                ], alignment=ft.MainAxisAlignment.START),
                                ft.Container(height=16),
                                ft.Divider(height=1, color=ft.Colors.OUTLINE),
                                ft.Container(height=12),
                                self.dest_ref_dropdown,
                                ft.Container(height=12),
                                self.dest_adjacent_dropdown,
                                ft.Container(height=12),
                                self.dest_col_dropdown,
                            ], spacing=0),
                            bgcolor=ft.Colors.SURFACE,
                            border_radius=12,
                            border=ft.border.all(1, ft.Colors.OUTLINE),
                            padding=24
                        ),
                        
                        ft.Container(height=16),
                        
                        # Card Configuración
                        ft.Container(
                            content=ft.Row([
                                self.tolerance_field,
                                ft.Container(width=16),
                                ft.Text(
                                    "Tolerancia para comparación de valores",
                                    size=12,
                                    color=ft.Colors.ON_SURFACE_VARIANT
                                )
                            ], alignment=ft.MainAxisAlignment.START),
                            bgcolor=ft.Colors.SURFACE,
                            border_radius=12,
                            border=ft.border.all(1, ft.Colors.OUTLINE),
                            padding=20
                        ),
                        
                        ft.Container(height=24),
                        
                        # Botón transferir y status
                        ft.Row([
                            self.status_text,
                            ft.Container(expand=True),
                            ft.ElevatedButton(
                                content=ft.Row([
                                    ft.Icon(ft.Icons.SYNC_ALT, size=18, color=ft.Colors.SURFACE),
                                    ft.Text("Transferir Datos", size=14, weight=ft.FontWeight.W_500)
                                ], spacing=8),
                                bgcolor=ft.Colors.PRIMARY,
                                color=ft.Colors.SURFACE,
                                elevation=0,
                                style=ft.ButtonStyle(
                                    shape=ft.RoundedRectangleBorder(radius=10),
                                    padding=ft.padding.symmetric(horizontal=24, vertical=14)
                                ),
                                on_click=self._on_transferir
                            )
                        ], alignment=ft.MainAxisAlignment.END)
                        
                    ], spacing=0, scroll=ft.ScrollMode.AUTO),
                    expand=True,
                    padding=ft.padding.symmetric(horizontal=24, vertical=0)
                )
            ], expand=True, spacing=0),
            bgcolor=ft.Colors.SURFACE,
            expand=True,
            visible=False
        )
    
    def _pick_file(self, picker_type: str):
        """Abre el selector de archivos"""
        self.current_picker_type = picker_type
        self.file_picker.pick_files(
            allowed_extensions=["xlsx", "xls"],
            dialog_title="Selecciona un archivo Excel"
        )
    
    def _on_file_picked(self, e):
        """Maneja la selección de archivo"""
        if e.files and len(e.files) > 0:
            file_path = e.files[0].path
            
            success, columns, message = self.service.cargar_archivo(
                file_path, 
                self.current_picker_type
            )
            
            if success:
                options = [ft.dropdown.Option(col) for col in columns]
                
                if self.current_picker_type == "source":
                    self.source_file_text.value = Path(file_path).name
                    self.source_file_text.color = ft.Colors.PRIMARY
                    self.source_ref_dropdown.options = options
                    self.source_ref_dropdown.disabled = False
                    self.source_col_dropdown.options = options
                    self.source_col_dropdown.disabled = False
                else:
                    self.dest_file_text.value = Path(file_path).name
                    self.dest_file_text.color = ft.Colors.GREEN
                    self.dest_ref_dropdown.options = options
                    self.dest_ref_dropdown.disabled = False
                    self.dest_adjacent_dropdown.options = options
                    self.dest_adjacent_dropdown.disabled = False
                    self.dest_col_dropdown.options = options
                    self.dest_col_dropdown.disabled = False
                
                self._show_status(message, ft.Colors.ON_SURFACE_VARIANT)
            else:
                self._show_status(message, ft.Colors.RED)
            
            self.page.update()
    
    def _on_transferir(self, e):
        """Ejecuta la transferencia de datos"""
        # Validaciones
        if not self.source_ref_dropdown.value or not self.source_col_dropdown.value:
            self._show_status("Selecciona las columnas del archivo origen", ft.Colors.ORANGE)
            return
        
        if not self.dest_ref_dropdown.value or not self.dest_adjacent_dropdown.value or not self.dest_col_dropdown.value:
            self._show_status("Selecciona las columnas del archivo destino", ft.Colors.ORANGE)
            return
        
        try:
            tolerance = float(self.tolerance_field.value) / 100.0
        except:
            tolerance = 0.05
        
        self._show_status("Procesando...", ft.Colors.PRIMARY)
        self.page.update()
        
        # Transferir
        success, matches, message = self.service.transferir_datos(
            source_col=self.source_col_dropdown.value,
            source_ref_col=self.source_ref_dropdown.value,
            dest_col=self.dest_col_dropdown.value,
            dest_ref_col=self.dest_ref_dropdown.value,
            dest_adjacent_col=self.dest_adjacent_dropdown.value,
            tolerance=tolerance
        )
        
        if success:
            # Guardar
            save_success, save_message = self.service.guardar_destino()
            if save_success:
                self._show_status(f"✅ {message}", ft.Colors.GREEN)
            else:
                self._show_status(f"⚠️ {save_message}", ft.Colors.RED)
        else:
            self._show_status(f"❌ {message}", ft.Colors.RED)
        
        self.page.update()
    
    def _show_status(self, message: str, color: str):
        """Muestra mensaje de estado"""
        self.status_text.value = message
        self.status_text.color = color
        self.page.update()
    
    def show(self):
        """Muestra la vista"""
        self.service.reset()
        self.source_file_text.value = "Ningún archivo seleccionado"
        self.source_file_text.color = ft.Colors.ON_SURFACE_VARIANT
        self.dest_file_text.value = "Ningún archivo seleccionado"
        self.dest_file_text.color = ft.Colors.ON_SURFACE_VARIANT
        self.source_ref_dropdown.value = None
        self.source_ref_dropdown.disabled = True
        self.source_col_dropdown.value = None
        self.source_col_dropdown.disabled = True
        self.dest_ref_dropdown.value = None
        self.dest_ref_dropdown.disabled = True
        self.dest_adjacent_dropdown.value = None
        self.dest_adjacent_dropdown.disabled = True
        self.dest_col_dropdown.value = None
        self.dest_col_dropdown.disabled = True
        self.status_text.value = ""
        self.container.visible = True
        self.page.update()
    
    def hide(self):
        """Oculta la vista"""
        self.container.visible = False
        self.page.update()
