"""
Procesador base para archivos de EPS
Define la interfaz común que todos los procesadores deben implementar
"""
import os
import pandas as pd
from datetime import datetime
from abc import ABC, abstractmethod
from typing import List, Dict, Tuple, Optional
    

class BaseProcessor(ABC):
    """Clase base abstracta para procesadores de archivos de EPS"""
    
    def __init__(self, homologador_path: str = None):
        """
        Args:
            homologador_path: Ruta al archivo de homologación de la EPS
        """
        self.homologador_path = homologador_path
        self.homologador_df = None
        self.processing_date = datetime.now().strftime("%Y-%m-%d")
        self.errors = []
        self.warnings = []
        
    def load_homologador(self) -> bool:
        """
        Carga el archivo de homologación
        
        Returns:
            True si se cargó correctamente, False en caso contrario
        """
        if not self.homologador_path:
            self.errors.append("No se especificó ruta de homologador")
            return False
            
        if not os.path.exists(self.homologador_path):
            self.errors.append(f"Archivo de homologador no encontrado: {self.homologador_path}")
            return False
            
        try:
            self.homologador_df = pd.read_excel(self.homologador_path)
            print(f"✓ Homologador cargado: {len(self.homologador_df)} registros")
            return True
        except Exception as e:
            self.errors.append(f"Error al cargar homologador: {str(e)}")
            return False
    
    @abstractmethod
    def identify_files(self, file_paths: List[str]) -> Dict[str, str]:
        """
        Identifica y clasifica los archivos de entrada
        
        Args:
            file_paths: Lista de rutas a los archivos
            
        Returns:
            Diccionario con tipo de archivo como clave y ruta como valor
            Ejemplo: {"detalle": "ruta/archivo.xlsx", "glosa": "ruta/glosa.xlsx"}
        """
        pass
    
    @abstractmethod
    def validate_files(self, identified_files: Dict[str, str]) -> bool:
        """
        Valida que los archivos identificados sean correctos
        
        Args:
            identified_files: Diccionario de archivos identificados
            
        Returns:
            True si los archivos son válidos, False en caso contrario
        """
        pass
    
    @abstractmethod
    def extract_data(self, identified_files: Dict[str, str]) -> Dict[str, pd.DataFrame]:
        """
        Extrae los datos de los archivos
        
        Args:
            identified_files: Diccionario de archivos identificados
            
        Returns:
            Diccionario con DataFrames extraídos
        """
        pass
    
    @abstractmethod
    def homologate(self, data: Dict[str, pd.DataFrame]) -> pd.DataFrame:
        """
        Realiza el proceso de homologación
        
        Args:
            data: Diccionario con DataFrames extraídos
            
        Returns:
            DataFrame con los datos homologados
        """
        pass
    
    def get_non_homologated(self, df: pd.DataFrame, code_column: str) -> pd.DataFrame:
        """
        Obtiene los códigos que no fueron homologados
        
        Args:
            df: DataFrame con los datos procesados
            code_column: Nombre de la columna con los códigos
            
        Returns:
            DataFrame con los códigos no homologados
        """
        # Implementación por defecto - las subclases pueden sobrescribir
        if "HOMOLOGADO" in df.columns:
            return df[df["HOMOLOGADO"] == False][[code_column]].drop_duplicates()
        return pd.DataFrame()
    
    def process(self, file_paths: List[str]) -> Tuple[Optional[pd.DataFrame], List[str], List[str]]:
        """
        Proceso principal de procesamiento
        
        Args:
            file_paths: Lista de rutas a los archivos
            
        Returns:
            Tupla con (DataFrame resultado, lista de errores, lista de advertencias)
        """
        self.errors = []
        self.warnings = []
        
        # 1. Cargar homologador
        if not self.load_homologador():
            return None, self.errors, self.warnings
        
        # 2. Identificar archivos
        identified = self.identify_files(file_paths)
        if not identified:
            self.errors.append("No se pudieron identificar los archivos")
            return None, self.errors, self.warnings
        
        # 3. Validar archivos
        if not self.validate_files(identified):
            return None, self.errors, self.warnings
        
        # 4. Extraer datos
        data = self.extract_data(identified)
        if not data:
            self.errors.append("No se pudieron extraer los datos")
            return None, self.errors, self.warnings
        
        # 5. Homologar
        result = self.homologate(data)
        
        return result, self.errors, self.warnings
    
    def save_result(self, df: pd.DataFrame, output_path: str) -> bool:
        """
        Guarda el resultado en un archivo Excel
        
        Args:
            df: DataFrame a guardar
            output_path: Ruta de salida
            
        Returns:
            True si se guardó correctamente, False en caso contrario
        """
        try:
            df.to_excel(output_path, index=False)
            print(f"✓ Archivo guardado: {output_path}")
            return True
        except Exception as e:
            self.errors.append(f"Error al guardar archivo: {str(e)}")
            return False
