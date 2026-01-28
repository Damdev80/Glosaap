"""
Componente de tabla de datos con pandas
Con soporte de temas claro/oscuro
"""
import flet as ft
from app.ui.styles import FONT_SIZES


class DataTable:
    """Componente para mostrar datos de pandas en una tabla"""
    
    def __init__(self, dataframe, max_rows=100):
        self.df = dataframe
        self.max_rows = max_rows
    
    def build(self):
        """Construye la tabla de Flet desde el DataFrame"""
        if self.df is None or self.df.empty:
            return ft.Text(
                "No hay datos para mostrar", 
                size=FONT_SIZES["body"], 
                color=ft.Colors.ON_SURFACE_VARIANT
            )
        
        # Limitar filas
        display_df = self.df.head(self.max_rows)
        
        # Crear columnas
        columns = [
            ft.DataColumn(
                ft.Text(
                    str(col), 
                    weight=ft.FontWeight.BOLD, 
                    size=FONT_SIZES["small"]
                )
            ) 
            for col in display_df.columns
        ]
        
        # Crear filas
        rows = []
        for idx, row in display_df.iterrows():
            cells = [
                ft.DataCell(
                    ft.Text(
                        str(val)[:50], 
                        size=FONT_SIZES["caption"]
                    )
                ) 
                for val in row
            ]
            rows.append(ft.DataRow(cells=cells))
        
        return ft.DataTable(
            columns=columns,
            rows=rows,
            border=ft.border.all(1, ft.Colors.OUTLINE),
            border_radius=10,
            horizontal_lines=ft.BorderSide(1, ft.Colors.OUTLINE_VARIANT),
            heading_row_color=ft.Colors.SURFACE_CONTAINER_HIGHEST,
            heading_row_height=50,
            data_row_max_height=40,
        )
    
    def get_info_widget(self):
        """Retorna un widget con información del dataset"""
        if self.df is None or self.df.empty:
            return None
        
        info_text = (
            f"📊 {len(self.df)} filas × {len(self.df.columns)} columnas | "
            f"Mostrando primeras {min(self.max_rows, len(self.df))} filas"
        )
        
        return ft.Container(
            content=ft.Text(
                info_text,
                size=FONT_SIZES["small"],
                color=ft.Colors.PRIMARY,
                weight=ft.FontWeight.W_500
            ),
            padding=10,
            bgcolor=ft.Colors.PRIMARY_CONTAINER,
            border_radius=5
        )
