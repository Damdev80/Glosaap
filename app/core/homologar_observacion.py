"""
Script para homologar códigos del archivo de observación.

Delega la regla de negocio (ERP -> DGH validado en COD_SERV_FACT) al
módulo compartido app/core/homologacion_lookup.py (misma que
MutualserProcessor).

FLUJO DE HOMOLOGACIÓN:
1. Tomar código de la columna "Tecnología"
2. Buscar ese código en "Código Servicio de la ERP" (archivo de homologación)
3. De esa fila, tomar el valor de "Código producto en DGH"
4. Buscar ese valor en TODA la columna "COD_SERV_FACT"
5. Si existe → devolverlo, si no → dejar en blanco
"""

import logging
import os
from datetime import datetime

import pandas as pd

from app.config.settings import HOMOLOGADOR_FILES
from app.core.homologacion_lookup import buscar_codigo_homologado, cargar_homologador_df

logger = logging.getLogger(__name__)


class HomologadorObservacion:
    """Clase para homologar códigos del archivo de observación"""

    def __init__(self, homologacion_path=None):
        """
        Inicializa el homologador

        Args:
            homologacion_path: Ruta al archivo de homologación (por defecto
                el de Mutualser desde settings, fuente única).
        """
        # Ruta por defecto desde settings (fuente única, sin hardcodear UNC).
        self.homologacion_path = homologacion_path or HOMOLOGADOR_FILES["mutualser"]
        self.df_homologacion = None
        self.todos_cod_serv_fact = set()

        # Cargar archivo de homologación
        self._cargar_homologacion()

    def _cargar_homologacion(self):
        """Carga el archivo de homologación (falla explícito, sin fallback)."""
        df, fact = cargar_homologador_df(self.homologacion_path)
        if df is None:
            if not os.path.exists(self.homologacion_path or ""):
                logger.warning(
                    "Archivo de homologación no encontrado: %s", self.homologacion_path
                )
            return
        self.df_homologacion = df
        self.todos_cod_serv_fact = fact or set()
        logger.info("Archivo de homologación cargado: %s registros", len(df))
        logger.info("COD_SERV_FACT únicos: %s", len(self.todos_cod_serv_fact))

    def _buscar_codigo_homologado(self, codigo_tecnologia):
        """
        Busca el código homologado según las reglas de negocio
        (ver módulo homologacion_lookup).
        """
        if self.df_homologacion is None or pd.isna(codigo_tecnologia):
            return ""
        try:
            return buscar_codigo_homologado(
                self.df_homologacion, self.todos_cod_serv_fact, codigo_tecnologia
            )
        except Exception as e:
            logger.warning("Error buscando código %s: %s", codigo_tecnologia, e)
            return ""

    def homologar_archivo(self, archivo_entrada, archivo_salida=None):
        """
        Homologa los códigos del archivo de observación

        Args:
            archivo_entrada: Ruta del archivo Excel a homologar
            archivo_salida: Ruta del archivo de salida (opcional)

        Returns:
            Ruta del archivo generado o None si hay error
        """
        try:
            logger.info("=" * 70)
            logger.info("HOMOLOGANDO ARCHIVO DE OBSERVACIÓN")
            logger.info("=" * 70)

            # Leer archivo
            logger.info("Leyendo: %s", archivo_entrada)
            df = pd.read_excel(archivo_entrada)
            df.columns = df.columns.str.strip()

            logger.info("Registros: %s", len(df))
            logger.info("Columnas: %s", list(df.columns))

            # Verificar columna Tecnología
            if "Tecnología" not in df.columns:
                logger.error("Columna 'Tecnología' no encontrada")
                return None

            # Homologar cada código
            logger.info("Homologando códigos...")
            codigos_homologados = []
            tecnologias_no_homologadas = []
            total = len(df)
            encontrados = 0

            for _idx, row in df.iterrows():
                tecnologia = row.get("Tecnología")
                codigo_homologado = self._buscar_codigo_homologado(tecnologia)
                codigos_homologados.append(codigo_homologado)

                if codigo_homologado:
                    encontrados += 1
                else:
                    if pd.notna(tecnologia) and str(tecnologia).strip():
                        tecnologias_no_homologadas.append(str(tecnologia).strip())

                # Mostrar progreso cada 10%
                if (len(codigos_homologados)) % max(1, total // 10) == 0:
                    porcentaje = (len(codigos_homologados) / total) * 100
                    logger.info(
                        "Progreso: %.0f%% (%s/%s)",
                        porcentaje,
                        len(codigos_homologados),
                        total,
                    )

            # Actualizar columna de código homologado
            df["Codigo homologado DGH"] = codigos_homologados

            # Agregar columna de tecnologías NO homologadas
            df["Tecnologia NO homologada"] = df.apply(
                lambda row: row["Tecnología"]
                if (pd.isna(row["Codigo homologado DGH"]) or row["Codigo homologado DGH"] == "")
                and pd.notna(row["Tecnología"])
                else "",
                axis=1,
            )

            # Generar archivo de salida
            if archivo_salida is None:
                nombre_base = os.path.splitext(os.path.basename(archivo_entrada))[0]
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                directorio = os.path.dirname(archivo_entrada)
                archivo_salida = os.path.join(
                    directorio, f"{nombre_base}_HOMOLOGADO_{timestamp}.xlsx"
                )

            # Guardar
            df.to_excel(archivo_salida, index=False)

            logger.info("=" * 70)
            logger.info("HOMOLOGACIÓN COMPLETADA")
            logger.info("=" * 70)
            logger.info("Total de registros: %s", total)
            logger.info("Códigos homologados: %s", encontrados)
            logger.info("Sin homologar: %s", total - encontrados)
            logger.info("Archivo generado: %s", archivo_salida)

            return archivo_salida

        except Exception as e:
            logger.exception("Error homologando archivo: %s", e)
            return None


def main():
    """Función principal para ejecutar desde línea de comandos"""
    import sys

    # Rutas por defecto (homologador en la red, fuente única en settings)
    archivo_observacion = "app/archivos_sep/MUTUAL SER SEP.xlsx"
    archivo_homologacion = HOMOLOGADOR_FILES["mutualser"]

    # Permitir pasar archivo como argumento
    if len(sys.argv) > 1:
        archivo_observacion = sys.argv[1]
    if len(sys.argv) > 2:
        archivo_homologacion = sys.argv[2]

    # Crear homologador y procesar
    homologador = HomologadorObservacion(homologacion_path=archivo_homologacion)
    resultado = homologador.homologar_archivo(archivo_observacion)

    if resultado:
        logger.info("¡Proceso completado!")
        logger.info("Archivo: %s", resultado)
    else:
        logger.error("El proceso falló")


if __name__ == "__main__":
    main()
