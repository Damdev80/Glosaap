"""
Vista de Homologador Manual
Permite homologar archivos Excel seleccionando EPS y columna
"""
import flet as ft
import pandas as pd
import os
import threading
from datetime import datetime
from app.ui.styles import COLORS


class HomologadorManualView:
    """Vista para homologar archivos Excel manualmente"""
    
    # Rutas de archivos de homologación por EPS
    HOMOLOGACION_PATHS = {
        "MUTUALSER": r"\\MINERVA\Cartera\GLOSAAP\HOMOLOGADOR\mutualser_homologacion.xlsx",
        "COOSALUD": r"\\MINERVA\Cartera\GLOSAAP\HOMOLOGADOR\coosalud_homologacion.xlsx"
    }
    
    # Ruta de salida
    OUTPUT_PATH = r"\\MINERVA\Cartera\GLOSAAP\RESULTADO DE HOMOLAGADOR MANUAL"
    
    # Assets directory
    ASSETS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "assets"))
    
    def __init__(self, page: ft.Page, on_back=None):
        self.page = page
        self.on_back = on_back
        
        # Estado
        self.selected_eps = None
        self.archivo_path = None
        self.df_archivo = None
        self.columnas_disponibles = []
        self.columna_seleccionada = None
        self.df_homologacion = None
        self._todos_cod_serv_fact = None
        
        # Componentes UI
        self.eps_dropdown = None
        self.archivo_text = None
        self.columna_dropdown = None
        self.btn_homologar = None
        self.status_text = None
        self.progress_bar = None
        self.preview_table = None
        
        self.container = self._build()
    
    def _build(self):
        """Construye la interfaz"""
        
        # Dropdown de EPS
        self.eps_dropdown = ft.Dropdown(
            label="Seleccionar EPS",
            width=300,
            options=[
                ft.dropdown.Option("MUTUALSER", "MUTUALSER"),
                ft.dropdown.Option("COOSALUD", "COOSALUD"),
            ],
            on_change=self._on_eps_change,
            border_color=COLORS["primary"],
            focused_border_color=COLORS["primary"]
        )
        
        # Selector de archivo
        self.archivo_text = ft.Text(
            "Ningún archivo seleccionado",
            size=13,
            color=COLORS["text_secondary"],
            width=250,
            overflow=ft.TextOverflow.ELLIPSIS
        )
        
        self.file_picker = ft.FilePicker(on_result=self._on_file_selected)
        self.page.overlay.append(self.file_picker)
        
        btn_seleccionar = ft.ElevatedButton(
            "📂 Seleccionar Archivo",
            on_click=lambda e: self.file_picker.pick_files(
                allowed_extensions=["xlsx", "xls"],
                dialog_title="Seleccionar archivo Excel"
            ),
            bgcolor=COLORS["primary"],
            color=COLORS["bg_white"],
            height=40
        )
        
        # Dropdown de columnas
        self.columna_dropdown = ft.Dropdown(
            label="Columna a homologar",
            width=300,
            options=[],
            on_change=self._on_columna_change,
            disabled=True,
            border_color=COLORS["primary"],
            focused_border_color=COLORS["primary"]
        )
        
        # Botón homologar
        self.btn_homologar = ft.ElevatedButton(
            "🔄 Homologar",
            on_click=self._on_homologar,
            bgcolor=COLORS["success"],
            color=COLORS["bg_white"],
            disabled=True,
            height=45,
            width=200
        )
        
        # Status
        self.status_text = ft.Text(
            "",
            size=13,
            color=COLORS["text_secondary"],
            text_align=ft.TextAlign.CENTER
        )
        
        self.progress_bar = ft.ProgressBar(
            width=400,
            visible=False,
            color=COLORS["primary"]
        )
        
        # Preview table
        self.preview_table = ft.DataTable(
            columns=[
                ft.DataColumn(ft.Text("Original", weight=ft.FontWeight.BOLD)),
                ft.DataColumn(ft.Text("Homologado", weight=ft.FontWeight.BOLD)),
            ],
            rows=[],
            border=ft.border.all(1, COLORS["border"]),
            border_radius=8,
            visible=False,
            column_spacing=50
        )
        
        # Logo EPS (se actualiza al seleccionar)
        self.eps_logo = ft.Image(
            src=os.path.join(self.ASSETS_DIR, "img", "eps", "mutualser.png"),
            width=120,
            height=60,
            fit=ft.ImageFit.CONTAIN,
            visible=False
        )
        
        return ft.Container(
            content=ft.Column([
                # Header
                ft.Container(
                    content=ft.Row([
                        ft.IconButton(
                            icon=ft.Icons.ARROW_BACK,
                            icon_color=COLORS["text_secondary"],
                            on_click=lambda e: self.on_back() if self.on_back else None
                        ),
                        ft.Image(
                            src=os.path.join(self.ASSETS_DIR, "img", "homologador_manual.png"),
                            width=30,
                            height=30,
                            fit=ft.ImageFit.CONTAIN
                        ),
                        ft.Text(
                            "Homologador Manual",
                            size=22,
                            weight=ft.FontWeight.W_600,
                            color=COLORS["text_primary"]
                        ),
                        ft.Container(expand=True),
                        self.eps_logo
                    ], alignment=ft.MainAxisAlignment.START),
                    padding=ft.padding.symmetric(horizontal=20, vertical=15),
                    bgcolor=COLORS["bg_white"],
                    border=ft.border.only(bottom=ft.BorderSide(1, COLORS["border"]))
                ),
                
                # Contenido principal
                ft.Container(
                    content=ft.Column([
                        # Paso 1: Seleccionar EPS
                        ft.Container(
                            content=ft.Column([
                                ft.Row([
                                    ft.Container(
                                        content=ft.Text("1", color=COLORS["bg_white"], size=14, weight=ft.FontWeight.BOLD),
                                        width=28, height=28,
                                        border_radius=14,
                                        bgcolor=COLORS["primary"],
                                        alignment=ft.alignment.center
                                    ),
                                    ft.Text("Seleccionar EPS", size=15, weight=ft.FontWeight.W_600, color=COLORS["text_primary"])
                                ], spacing=10),
                                ft.Container(height=10),
                                self.eps_dropdown
                            ]),
                            padding=20,
                            bgcolor=COLORS["bg_white"],
                            border_radius=10,
                            border=ft.border.all(1, COLORS["border"])
                        ),
                        
                        # Paso 2: Seleccionar archivo
                        ft.Container(
                            content=ft.Column([
                                ft.Row([
                                    ft.Container(
                                        content=ft.Text("2", color=COLORS["bg_white"], size=14, weight=ft.FontWeight.BOLD),
                                        width=28, height=28,
                                        border_radius=14,
                                        bgcolor=COLORS["primary"],
                                        alignment=ft.alignment.center
                                    ),
                                    ft.Text("Cargar archivo Excel", size=15, weight=ft.FontWeight.W_600, color=COLORS["text_primary"])
                                ], spacing=10),
                                ft.Container(height=10),
                                ft.Row([
                                    btn_seleccionar,
                                    ft.Container(width=15),
                                    self.archivo_text
                                ], alignment=ft.MainAxisAlignment.START)
                            ]),
                            padding=20,
                            bgcolor=COLORS["bg_white"],
                            border_radius=10,
                            border=ft.border.all(1, COLORS["border"])
                        ),
                        
                        # Paso 3: Seleccionar columna
                        ft.Container(
                            content=ft.Column([
                                ft.Row([
                                    ft.Container(
                                        content=ft.Text("3", color=COLORS["bg_white"], size=14, weight=ft.FontWeight.BOLD),
                                        width=28, height=28,
                                        border_radius=14,
                                        bgcolor=COLORS["primary"],
                                        alignment=ft.alignment.center
                                    ),
                                    ft.Text("Seleccionar columna a homologar", size=15, weight=ft.FontWeight.W_600, color=COLORS["text_primary"])
                                ], spacing=10),
                                ft.Container(height=10),
                                self.columna_dropdown
                            ]),
                            padding=20,
                            bgcolor=COLORS["bg_white"],
                            border_radius=10,
                            border=ft.border.all(1, COLORS["border"])
                        ),
                        
                        # Botón y status
                        ft.Container(height=10),
                        ft.Row([self.btn_homologar], alignment=ft.MainAxisAlignment.CENTER),
                        ft.Container(height=10),
                        self.progress_bar,
                        self.status_text,
                        
                        # Preview
                        ft.Container(height=10),
                        ft.Container(
                            content=self.preview_table,
                            alignment=ft.alignment.center
                        )
                        
                    ], spacing=15, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                    padding=25,
                    expand=True,
                    alignment=ft.alignment.top_center
                )
            ], spacing=0),
            bgcolor=COLORS["bg_light"],
            expand=True,
            visible=False
        )
    
    def _on_eps_change(self, e):
        """Cuando se selecciona una EPS"""
        self.selected_eps = e.control.value
        
        # Mostrar logo
        if self.selected_eps == "MUTUALSER":
            self.eps_logo.src = os.path.join(self.ASSETS_DIR, "img", "eps", "mutualser.png")
            self.eps_logo.visible = True
        elif self.selected_eps == "COOSALUD":
            self.eps_logo.src = os.path.join(self.ASSETS_DIR, "img", "eps", "coosalud.png")
            self.eps_logo.visible = True
        
        # Cargar archivo de homologación
        self._cargar_homologacion()
        self._update_button_state()
        self.page.update()
    
    def _cargar_homologacion(self):
        """Carga el archivo de homologación de la EPS seleccionada"""
        if not self.selected_eps:
            return
        
        path = self.HOMOLOGACION_PATHS.get(self.selected_eps)
        if not path or not os.path.exists(path):
            self.status_text.value = f"❌ Archivo de homologación no encontrado: {path}"
            self.status_text.color = COLORS["error"]
            self.df_homologacion = None
            self.page.update()
            return
        
        try:
            self.df_homologacion = pd.read_excel(path)
            self.df_homologacion.columns = self.df_homologacion.columns.str.strip()
            
            # Pre-calcular COD_SERV_FACT solo para MUTUALSER
            if self.selected_eps == "MUTUALSER" and 'COD_SERV_FACT' in self.df_homologacion.columns:
                self._todos_cod_serv_fact = set(
                    self.df_homologacion['COD_SERV_FACT']
                    .dropna().astype(str).str.strip().tolist()
                )
                self._todos_cod_serv_fact.discard('0')
                self._todos_cod_serv_fact.discard('')
            else:
                # COOSALUD no usa COD_SERV_FACT (por ahora)
                self._todos_cod_serv_fact = None
            
            self.status_text.value = f"✅ Homologación {self.selected_eps} cargada: {len(self.df_homologacion)} registros"
            self.status_text.color = COLORS["success"]
            
        except Exception as ex:
            self.status_text.value = f"❌ Error cargando homologación: {ex}"
            self.status_text.color = COLORS["error"]
            self.df_homologacion = None
    
    def _on_file_selected(self, e: ft.FilePickerResultEvent):
        """Cuando se selecciona un archivo"""
        if not e.files or len(e.files) == 0:
            return
        
        self.archivo_path = e.files[0].path
        self.archivo_text.value = os.path.basename(self.archivo_path)
        self.archivo_text.color = COLORS["text_primary"]
        
        # Cargar archivo y obtener columnas
        try:
            self.df_archivo = pd.read_excel(self.archivo_path)
            self.columnas_disponibles = list(self.df_archivo.columns)
            
            # Actualizar dropdown de columnas
            self.columna_dropdown.options = [
                ft.dropdown.Option(col, col) for col in self.columnas_disponibles
            ]
            self.columna_dropdown.disabled = False
            self.columna_dropdown.value = None
            self.columna_seleccionada = None
            
            self.status_text.value = f"📄 Archivo cargado: {len(self.df_archivo)} filas, {len(self.columnas_disponibles)} columnas"
            self.status_text.color = COLORS["text_secondary"]
            
        except Exception as ex:
            self.status_text.value = f"❌ Error leyendo archivo: {ex}"
            self.status_text.color = COLORS["error"]
            self.columna_dropdown.disabled = True
        
        self._update_button_state()
        self.page.update()
    
    def _on_columna_change(self, e):
        """Cuando se selecciona una columna"""
        self.columna_seleccionada = e.control.value
        self._update_button_state()
        self.page.update()
    
    def _update_button_state(self):
        """Actualiza el estado del botón de homologar"""
        self.btn_homologar.disabled = not (
            self.selected_eps and
            self.archivo_path and
            self.df_archivo is not None and
            self.columna_seleccionada and
            self.df_homologacion is not None
        )
    
    def _buscar_codigo_homologado(self, codigo):
        """Busca código homologado usando las reglas de la EPS"""
        if self.df_homologacion is None or pd.isna(codigo):
            return ''
        
        try:
            codigo_str = str(codigo).strip()
            if not codigo_str or codigo_str == 'nan':
                return ''
            
            col_erp = 'Código Servicio de la ERP'
            col_producto = 'Código producto en DGH'
            
            # Verificar columnas
            if col_erp not in self.df_homologacion.columns or col_producto not in self.df_homologacion.columns:
                return ''
            
            codigo_numerico = ''.join(filter(str.isdigit, codigo_str))
            
            # Buscar en Código Servicio de la ERP
            mask = self.df_homologacion[col_erp].astype(str).str.strip() == codigo_str
            resultado = self.df_homologacion[mask]
            
            if resultado.empty and codigo_numerico:
                mask = self.df_homologacion[col_erp].astype(str).str.replace(r'\D', '', regex=True) == codigo_numerico
                resultado = self.df_homologacion[mask]
            
            if not resultado.empty:
                codigo_producto = resultado.iloc[0][col_producto]
                
                if pd.notna(codigo_producto):
                    cod_str = str(codigo_producto).strip()
                    
                    if cod_str and cod_str != '0' and cod_str != 'nan':
                        # COOSALUD: Homologación directa sin verificar COD_SERV_FACT
                        if self.selected_eps == "COOSALUD":
                            return cod_str
                        
                        # MUTUALSER: Verificar si existe en COD_SERV_FACT
                        if self._todos_cod_serv_fact and cod_str in self._todos_cod_serv_fact:
                            return cod_str
                        
                        # Búsqueda flexible para MUTUALSER
                        if self._todos_cod_serv_fact:
                            cod_numerico = ''.join(filter(str.isdigit, cod_str))
                            if cod_numerico:
                                for cod in self._todos_cod_serv_fact:
                                    if ''.join(filter(str.isdigit, cod)) == cod_numerico:
                                        return cod
            
            return ''
            
        except Exception as e:
            print(f"⚠️ Error homologando {codigo}: {e}")
            return ''
    
    def _on_homologar(self, e):
        """Ejecuta la homologación"""
        def worker():
            try:
                self.btn_homologar.disabled = True
                self.progress_bar.visible = True
                self.status_text.value = "🔄 Homologando..."
                self.status_text.color = COLORS["text_secondary"]
                self.page.update()
                
                # Hacer copia del dataframe
                df_resultado = self.df_archivo.copy()
                
                # Homologar cada valor de la columna seleccionada
                total = len(df_resultado)
                homologados = 0
                no_homologados = 0
                preview_data = []
                
                for idx, valor in enumerate(df_resultado[self.columna_seleccionada]):
                    codigo_homologado = self._buscar_codigo_homologado(valor)
                    
                    if codigo_homologado:
                        df_resultado.at[idx, self.columna_seleccionada] = codigo_homologado
                        homologados += 1
                        if len(preview_data) < 5:
                            preview_data.append((str(valor), codigo_homologado))
                    else:
                        no_homologados += 1
                        if len(preview_data) < 5 and str(valor).strip():
                            preview_data.append((str(valor), "❌ No encontrado"))
                    
                    # Actualizar progreso cada 100 registros
                    if idx % 100 == 0:
                        self.progress_bar.value = idx / total
                        self.page.update()
                
                # Guardar archivo
                os.makedirs(self.OUTPUT_PATH, exist_ok=True)
                
                nombre_original = os.path.splitext(os.path.basename(self.archivo_path))[0]
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                nombre_salida = f"{nombre_original}_homologado_{self.selected_eps}_{timestamp}.xlsx"
                ruta_salida = os.path.join(self.OUTPUT_PATH, nombre_salida)
                
                df_resultado.to_excel(ruta_salida, index=False)
                
                # Mostrar preview
                self.preview_table.rows = [
                    ft.DataRow(cells=[
                        ft.DataCell(ft.Text(orig, size=12)),
                        ft.DataCell(ft.Text(hom, size=12, color=COLORS["success"] if "❌" not in hom else COLORS["error"]))
                    ]) for orig, hom in preview_data
                ]
                self.preview_table.visible = True
                
                # Status final
                self.progress_bar.visible = False
                self.status_text.value = f"✅ ¡Homologación completada!\n📊 {homologados} homologados | {no_homologados} sin homologar\n📁 Guardado en: {nombre_salida}"
                self.status_text.color = COLORS["success"]
                self.btn_homologar.disabled = False
                self.page.update()
                
                # Abrir carpeta de destino
                import subprocess
                subprocess.Popen(f'explorer "{self.OUTPUT_PATH}"')
                
            except Exception as ex:
                self.progress_bar.visible = False
                self.status_text.value = f"❌ Error: {ex}"
                self.status_text.color = COLORS["error"]
                self.btn_homologar.disabled = False
                self.page.update()
        
        threading.Thread(target=worker, daemon=True).start()
    
    def show(self):
        """Muestra la vista"""
        self.container.visible = True
        self.page.update()
    
    def hide(self):
        """Oculta la vista"""
        self.container.visible = False
        self.page.update()
