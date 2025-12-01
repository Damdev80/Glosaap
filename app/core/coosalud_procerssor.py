"""
Coosalud EPS configuration module.
Manejo de extraccion de homologaciones y devoluciones de Coosalud EPS.
"""

import pandas as pd
import os 
from datetime import datetime


class CoosaludProcessor:
    """Procesador especifico para Coosalud EPS"""

    COLUMNAS_REQUIRIDAS = [
        "NUMERO DE FACTURA",
        "FECHA DE FACTURA",
        "CODIGO CONCEPTO GENERAL",
        "VALOR TOTAL NEGOCIADO GLOSA",
        "VALOR GLOSADO PRESTADOR",
        "CODIGO PROCEDIMIENTO",
        "OBSERVACIONES",
    ]
    
    # Ruta de red para homologación
    HOMOLOGACION_PATH = r"\\minerva\Cartera\GLOSAAP\HOMOLOGADOR\coosalud_homologacion.xlsx"
    
    def __init__(self, output_dir='outputs', homologacion_path=None):
        self.output_dir = output_dir
        self.homologacion_path = homologacion_path or self.HOMOLOGACION_PATH
        self.df_consolidado = None
        self.df_homologacion = None
        self.archivos_procesados = []
        self.errores = []
        
        os.makedirs(output_dir, exist_ok=True)
        self._cargar_homologacion()
    
    def _cargar_homologacion(self):
        """Carga el archivo de homologación"""
        try:
            if not os.path.exists(self.homologacion_path):
                print(f"⚠️ Archivo de homologación no encontrado: {self.homologacion_path}")
                self.df_homologacion = None
                return
            
            self.df_homologacion = pd.read_excel(self.homologacion_path)
            self.df_homologacion.columns = self.df_homologacion.columns.str.strip()
            print(f"✅ Homologación Coosalud cargada: {len(self.df_homologacion)} registros")
            
        except Exception as e:
            print(f"⚠️ Error cargando homologación Coosalud: {e}")
            self.df_homologacion = None
