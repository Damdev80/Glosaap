"""
Procesador de datos con pandas
Maneja la lectura y consolidación de archivos Excel/CSV
"""
import pandas as pd
import os


class DataProcessor:
    """Clase para procesar archivos de datos con pandas"""
    
    def __init__(self):
        self.df = None
        self.source_files = []
    
    def process_files(self, file_paths):
        """
        Procesa múltiples archivos Excel/CSV y los consolida en un DataFrame
        
        Args:
            file_paths: Lista de rutas de archivos
            
        Returns:
            pd.DataFrame o None si no hay datos
        """
        dfs = []
        self.source_files = []
        
        for file_path in file_paths:
            try:
                if not os.path.exists(file_path):
                    continue
                    
                if file_path.endswith(('.xlsx', '.xls')):
                    df = pd.read_excel(file_path)
                    dfs.append(df)
                    self.source_files.append(file_path)
                elif file_path.endswith('.csv'):
                    df = pd.read_csv(file_path)
                    dfs.append(df)
                    self.source_files.append(file_path)
            except Exception as e:
                print(f"Error procesando {file_path}: {e}")
        
        if dfs:
            self.df = pd.concat(dfs, ignore_index=True)
            return self.df
        
        return None
    
    def get_summary(self):
        """Obtiene un resumen del DataFrame actual"""
        if self.df is None or self.df.empty:
            return None
            
        return {
            "rows": len(self.df),
            "columns": len(self.df.columns),
            "column_names": list(self.df.columns),
            "files_processed": len(self.source_files),
            "memory_usage": self.df.memory_usage(deep=True).sum(),
        }
    
    def get_preview(self, n_rows=100):
        """Obtiene una vista previa de n filas"""
        if self.df is None or self.df.empty:
            return None
        return self.df.head(n_rows)
    
    def export_to_excel(self, output_path):
        """Exporta el DataFrame consolidado a Excel"""
        if self.df is not None and not self.df.empty:
            self.df.to_excel(output_path, index=False)
            return True
        return False
    
    def filter_data(self, column, value):
        """Filtra datos por columna y valor"""
        if self.df is None or self.df.empty:
            return None
        if column not in self.df.columns:
            return None
        return self.df[self.df[column] == value]
