"""
Procesador base para archivos de EPS.

Este módulo define la clase base abstracta que todos los procesadores
de EPS deben implementar. Proporciona la estructura común y métodos
compartidos para el procesamiento de archivos de glosas y homologación.

Patrón de diseño:
    Template Method - Define el esqueleto del algoritmo de procesamiento
    en métodos abstractos que las subclases deben implementar.

Flujo de procesamiento:
    1. Cargar homologador (load_homologador)
    2. Identificar archivos (identify_files)
    3. Validar archivos (validate_files)
    4. Extraer datos (extract_data)
    5. Homologar códigos (homologate)
    6. Guardar resultados (save_results)

Ejemplo de uso:
    ```python
    from app.service.processors.coosalud_processor import CoosaludProcessor
    
    processor = CoosaludProcessor(homologador_path="ruta/homologador.xlsx")
    processor.load_homologador()
    
    files = processor.identify_files(["archivo1.xlsx", "archivo2.xlsx"])
    if processor.validate_files(files):
        data = processor.extract_data(files)
        result = processor.homologate(data)
        processor.save_results(result, "salida/")
    ```

Author: Glosaap Team
Version: 1.0.0
"""
import os
import pandas as pd
from datetime import datetime
from abc import ABC, abstractmethod
from typing import List, Dict, Tuple, Optional
    

class BaseProcessor(ABC):
    """
    Clase base abstracta para procesadores de archivos de EPS.
    
    Define la interfaz común y métodos compartidos que todos los
    procesadores de EPS deben implementar. Cada EPS tiene su propio
    formato de archivos, por lo que se requieren procesadores específicos.
    
    Attributes:
        homologador_path (str): Ruta al archivo Excel de homologación.
        homologador_df (pd.DataFrame): DataFrame con datos de homologación.
        processing_date (str): Fecha de procesamiento en formato YYYY-MM-DD.
        errors (List[str]): Lista de errores encontrados durante el proceso.
        warnings (List[str]): Lista de advertencias del proceso.
    
    Abstract Methods:
        identify_files: Identifica y clasifica archivos de entrada.
        validate_files: Valida que los archivos sean correctos.
        extract_data: Extrae datos de los archivos.
        homologate: Homologa códigos según tabla de referencia.
        save_results: Guarda los resultados procesados.
    
    Example:
        ```python
        class MyEpsProcessor(BaseProcessor):
            def identify_files(self, file_paths):
                # Implementación específica
                pass
        ```
    """
    
    def __init__(self, homologador_path: Optional[str] = None):
        """
        Inicializa el procesador base.
        
        Args:
            homologador_path: Ruta al archivo Excel de homologación.
                Si es None, deberá configurarse antes de procesar.
        
        Raises:
            No lanza excepciones directamente, pero registra errores
            en self.errors si hay problemas.
        """
        self.homologador_path = homologador_path
        self.homologador_df = None
        self.processing_date = datetime.now().strftime("%Y-%m-%d")
        self.errors = []
        self.warnings = []
        
    def load_homologador(self) -> bool:
        """
        Carga el archivo de homologación desde Excel.
        
        Lee el archivo Excel especificado en homologador_path y lo
        carga en homologador_df como DataFrame de pandas.
        
        Returns:
            bool: True si se cargó correctamente, False si hubo error.
        
        Side Effects:
            - Actualiza self.homologador_df con los datos cargados.
            - Agrega mensajes a self.errors si hay problemas.
            - Imprime mensaje de confirmación en consola.
        
        Example:
            ```python
            processor = MyProcessor("ruta/homologador.xlsx")
            if processor.load_homologador():
                print("Homologador cargado exitosamente")
            else:
                print(f"Errores: {processor.errors}")
            ```
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
        Identifica y clasifica los archivos de entrada.
        
        Analiza los nombres y contenidos de los archivos para determinar
        su tipo (detalle, glosa, etc.) y agruparlos correctamente.
        
        Args:
            file_paths: Lista de rutas absolutas a los archivos a procesar.
        
        Returns:
            Dict[str, str]: Diccionario con tipo de archivo como clave
                y ruta como valor.
                Ejemplo: {"detalle": "/ruta/detalle.xlsx", "glosa": "/ruta/glosa.xlsx"}
        
        Raises:
            NotImplementedError: Si la subclase no implementa este método.
        
        Note:
            Las subclases deben implementar la lógica específica de
            identificación según el formato de cada EPS.
        """
        pass
    
    @abstractmethod
    def validate_files(self, identified_files: Dict[str, str]) -> bool:
        """
        Valida que los archivos identificados sean correctos.
        
        Verifica que los archivos contengan las columnas requeridas,
        tengan el formato esperado y estén completos.
        
        Args:
            identified_files: Diccionario de archivos identificados
                por identify_files().
        
        Returns:
            bool: True si todos los archivos son válidos, False si hay
                problemas. Los errores se registran en self.errors.
        
        Raises:
            NotImplementedError: Si la subclase no implementa este método.
        """
        pass
    
    @abstractmethod
    def extract_data(self, identified_files: Dict[str, str]) -> Dict[str, pd.DataFrame]:
        """
        Extrae los datos de los archivos identificados.
        
        Lee los archivos Excel y extrae los datos relevantes en
        DataFrames de pandas para su posterior procesamiento.
        
        Args:
            identified_files: Diccionario de archivos identificados
                por identify_files().
            
        Returns:
            Dict[str, pd.DataFrame]: Diccionario con DataFrames extraídos.
                Las claves corresponden al tipo de archivo.
        
        Raises:
            NotImplementedError: Si la subclase no implementa este método.
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
