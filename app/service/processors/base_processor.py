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
    6. Guardar resultados (save_result / save_results)

Ejemplo de uso:
    ```python
    from app.service.processors.coosalud_processor import CoosaludProcessor

    processor = CoosaludProcessor(homologador_path="ruta/homologador.xlsx")
    processor.load_homologador()

    files = processor.identify_files(["archivo1.xlsx", "archivo2.xlsx"])
    if processor.validate_files(files):
        data = processor.extract_data(files)
        result = processor.homologate(data)
        processor.save_result(result, "salida.xlsx")
    ```

Author: Glosaap Team
Version: 1.1.0
"""
import os
import pandas as pd
from datetime import datetime
from abc import ABC, abstractmethod
from typing import List, Dict, Tuple, Optional, Union, Any

from app.config.settings import logger


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

    Example:
        ```python
        class MyEpsProcessor(BaseProcessor):
            def identify_files(self, file_paths):
                # Implementación específica
                pass
        ```
    """

    #: Columnas internas que nunca deben exportarse al Excel entregado.
    INTERNAL_COLUMNS = ["_FACTURA", "fecha_correo"]

    def __init__(self, homologador_path: Optional[str] = None):
        """
        Inicializa el procesador base.

        Args:
            homologador_path: Ruta al archivo Excel de homologación.
                Si es None, deberá configurarse antes de procesar.
        """
        self.homologador_path = homologador_path
        self.homologador_df = None
        self.processing_date = datetime.now().strftime("%Y-%m-%d")
        self.errors: List[str] = []
        self.warnings: List[str] = []

    # ==================== HELPERS COMPARTIDOS ====================

    def _normalize_code(self, code) -> str:
        """Normaliza un codigo: strip, upper, sin ceros/prefijos espurios.

        Maneja floats/ints (elimina .0), strings y NaN de forma uniforme
        para Mutualser y Coosalud.
        """
        if pd.isna(code):
            return ""
        if isinstance(code, (int, float)):
            try:
                return str(int(code)).strip().upper()
            except (ValueError, OverflowError):
                return str(code).strip().upper()
        return str(code).strip().upper()

    def _formatear_crncxc(self, valor) -> str:
        """Formatea factura a CRNCXC como FC0000{digitos}.

        Extrae solo digitos para unificar Mutualser y Coosalud.
        Ej: "12345" -> "FC000012345", "FC12345" -> "FC000012345".
        """
        if pd.isna(valor) or not valor:
            return ""
        valor_str = str(valor).strip()
        if valor_str.upper().startswith("FC"):
            numeros = valor_str[2:]
        else:
            numeros = valor_str
        numeros = "".join(filter(str.isdigit, numeros))
        if not numeros:
            return ""
        return f"FC0000{numeros}"

    def _formatear_fecha_dmy(self, fecha) -> str:
        """Convierte fecha a formato D/M/A (DD/MM/YYYY)."""
        if pd.isna(fecha) or not fecha:
            return ""
        try:
            if isinstance(fecha, (pd.Timestamp, datetime)):
                return fecha.strftime("%d/%m/%Y")
            fecha_dt = pd.to_datetime(str(fecha), errors="coerce")
            return fecha_dt.strftime("%d/%m/%Y") if pd.notna(fecha_dt) else ""
        except Exception:
            return ""

    def _obtener_valor_numerico(self, valor) -> float:
        """Convierte valor a float preservando decimales.

        Maneja formato colombiano (1.234,56) e internacional (1,234.56).
        No usa replace('.','') que destruye decimales.
        """
        if pd.isna(valor) or valor == "":
            return 0.0
        try:
            if isinstance(valor, (int, float)):
                return float(valor)
            valor_str = str(valor).strip().replace("$", "").replace(" ", "")
            if not valor_str:
                return 0.0
            if "," in valor_str and "." in valor_str:
                pos_coma = valor_str.rfind(",")
                pos_punto = valor_str.rfind(".")
                if pos_coma > pos_punto:
                    # Coma al final = decimal (colombiano): 1.234,56 -> 1234.56
                    valor_str = valor_str.replace(".", "").replace(",", ".")
                else:
                    # Punto al final = decimal (internacional): 1,234.56 -> 1234.56
                    valor_str = valor_str.replace(",", "")
            elif "," in valor_str:
                if valor_str.count(",") > 1:
                    valor_str = valor_str.replace(",", "")
                else:
                    partes = valor_str.split(",")
                    if len(partes) == 2 and len(partes[1]) <= 2:
                        valor_str = valor_str.replace(",", ".")
                    else:
                        valor_str = valor_str.replace(",", "")
            elif "." in valor_str:
                if valor_str.count(".") > 1:
                    valor_str = valor_str.replace(".", "")
            return float(valor_str) if valor_str else 0.0
        except Exception:
            return 0.0

    def _drop_internal_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """Retorna copia sin columnas internas (_FACTURA, fecha_correo)."""
        if df is None or df.empty:
            return df
        cols = [c for c in self.INTERNAL_COLUMNS if c in df.columns]
        if cols:
            return df.drop(columns=cols)
        return df

    def load_homologador(self) -> bool:
        """
        Carga el archivo de homologación desde Excel.

        Returns:
            bool: True si se cargó correctamente, False si hubo error.
        """
        if not self.homologador_path:
            self.errors.append("No se especificó ruta de homologador")
            return False

        if not os.path.exists(self.homologador_path):
            self.errors.append(f"Archivo de homologador no encontrado: {self.homologador_path}")
            return False

        try:
            self.homologador_df = pd.read_excel(self.homologador_path)
            logger.info("Homologador cargado: %s registros", len(self.homologador_df))
            return True
        except Exception as e:
            self.errors.append(f"Error al cargar homologador: {str(e)}")
            return False

    @abstractmethod
    def identify_files(
        self, file_paths: List[str]
    ) -> Union[Dict[str, Any], List[Dict[str, str]]]:
        """
        Identifica y clasifica los archivos de entrada.

        Debe emparejar TODOS los pares DETALLE+GLOSA por número de factura,
        nunca solo el primero. Puede retornar una lista de pares
        (List[Dict]) o un dict con todos los pares.

        Args:
            file_paths: Lista de rutas absolutas a los archivos a procesar.

        Returns:
            Lista de pares o diccionario con todos los pares identificados.
        """
        pass

    @abstractmethod
    def validate_files(
        self, identified_files: Union[Dict[str, Any], List[Dict[str, str]]]
    ) -> bool:
        """
        Valida que los archivos identificados sean correctos.

        Acepta tanto un par único (Dict con detalle/glosa) como múltiples
        pares (List) para compatibilidad entre EPS.

        Args:
            identified_files: Archivos identificados por identify_files().

        Returns:
            bool: True si todos los archivos son válidos.
        """
        pass

    @abstractmethod
    def extract_data(
        self, identified_files: Union[Dict[str, Any], List[Dict[str, str]]]
    ) -> Dict[str, pd.DataFrame]:
        """
        Extrae los datos de los archivos identificados.

        Args:
            identified_files: Archivos identificados por identify_files().

        Returns:
            Dict[str, pd.DataFrame]: Diccionario con DataFrames extraídos.
        """
        pass

    @abstractmethod
    def homologate(self, data: Dict[str, pd.DataFrame]) -> pd.DataFrame:
        """
        Realiza el proceso de homologación.

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
        if "HOMOLOGADO" in df.columns:
            return df[df["HOMOLOGADO"] == False][[code_column]].drop_duplicates()
        return pd.DataFrame()

    def process(self, file_paths: List[str]) -> Tuple[Optional[pd.DataFrame], List[str], List[str]]:
        """
        Proceso principal de procesamiento (Template Method).

        Flujo: load -> identify -> validate -> extract -> homologate.
        Si no hay homologador se continúa con advertencia (los registros
        quedan como no homologados) en lugar de fallar.

        Args:
            file_paths: Lista de rutas a los archivos

        Returns:
            Tupla con (DataFrame resultado, lista de errores, lista de advertencias)
        """
        self.errors = []
        self.warnings = []

        # 1. Cargar homologador (tolerante: continuar sin homologación)
        if self.homologador_path:
            if not self.load_homologador():
                self.warnings.append("Se continúa sin homologación: " + "; ".join(self.errors))
                logger.warning("Se continúa sin homologador cargado")
        else:
            self.warnings.append("Sin archivo de homologación; se continúa sin homologar")
            logger.warning("Sin homologador configurado; se continúa sin homologar")

        # 2. Identificar archivos (TODOS los pares)
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

        # 5. Homologar (retorna DataFrame según contrato)
        result = self.homologate(data)

        return result, self.errors, self.warnings

    def save_result(self, df: pd.DataFrame, output_path: str) -> bool:
        """
        Guarda el resultado en un archivo Excel.

        Quita columnas internas (_FACTURA, fecha_correo) antes de exportar.

        Args:
            df: DataFrame a guardar
            output_path: Ruta de salida

        Returns:
            True si se guardó correctamente, False en caso contrario
        """
        try:
            clean = self._drop_internal_columns(df)
            clean.to_excel(output_path, index=False)
            logger.info("Archivo guardado: %s", output_path)
            return True
        except Exception as e:
            self.errors.append(f"Error al guardar archivo: {str(e)}")
            return False

    def save_results(self, df: pd.DataFrame, output_path: str) -> bool:
        """Alias plural de save_result para compatibilidad."""
        return self.save_result(df, output_path)
