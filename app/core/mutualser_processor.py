"""
Procesador específico para MUTUALSER
Maneja la extracción, homologación y generación de archivos de objeciones
"""
import os
from datetime import datetime
from typing import Any

import pandas as pd

from app.config.settings import HOMOLOGADOR_FILES, logger
from app.service.processors.base_processor import BaseProcessor


class MutualserProcessor(BaseProcessor):
    """
    Procesador para archivos de MUTUALSER bajo contrato BaseProcessor.
    Mantiene compatibilidad con procesar_archivo / procesar_multiples_archivos
    / exportar_consolidado usados por EmailService.procesar_mutualser.
    """

    COLUMNAS_REQUERIDAS = [
        'Número de factura', 'Número de glosa', 'Tecnología',
        'Cantidad facturada', 'Valor Facturado', 'Cantidad glosada',
        'Valor glosado', 'Concepto de glosa', 'Código de glosa',
        'Observacion', 'Fecha'
    ]

    # Fuente única de rutas (settings); el valor sigue siendo ruta de red.
    HOMOLOGACION_PATH = HOMOLOGADOR_FILES["mutualser"]

    def __init__(self, output_dir: str = 'outputs', homologacion_path: str | None = None):
        resolved = homologacion_path or self.HOMOLOGACION_PATH
        super().__init__(homologador_path=resolved)
        self.output_dir = output_dir
        # Alias legacy (es) + base (or)
        self.homologacion_path = resolved
        self.homologador_path = resolved
        self.df_consolidado: pd.DataFrame | None = None
        self.df_homologacion: pd.DataFrame | None = None
        self.homologador_df = None
        self.archivos_procesados: list = []
        self._todos_cod_serv_fact: set | None = None

        # Crear directorio si no existe (funciona con rutas de red)
        try:
            os.makedirs(output_dir, exist_ok=True)
        except Exception as e:
            logger.warning("No se pudo crear directorio %s: %s", output_dir, e)

        self._cargar_homologacion()

    # Alias para compatibilidad: errores (legacy) <-> errors (Base)
    @property
    def errores(self) -> list:
        return self.errors

    @errores.setter
    def errores(self, value: list) -> None:
        self.errors = value

    # ==================== HOMOLOGACIÓN ====================

    def _cargar_homologacion(self):
        """Carga el archivo de homologación (falla explícito, sin fallback)."""
        try:
            path = self.homologacion_path or self.homologador_path
            if not path or not os.path.exists(path):
                logger.error("Homologador Mutualser no encontrado: %s", path)
                self.df_homologacion = None
                self.homologador_df = None
                self._todos_cod_serv_fact = None
                return
            df = pd.read_excel(path)
            df.columns = df.columns.str.strip()
            self.df_homologacion = df
            self.homologador_df = df
            self.homologacion_path = path
            self.homologador_path = path
            if 'COD_SERV_FACT' in df.columns:
                codigos = set(
                    df['COD_SERV_FACT'].dropna().astype(str).str.strip().tolist()
                )
                codigos.discard('0')
                codigos.discard('')
                self._todos_cod_serv_fact = codigos
                logger.info("Códigos de homologación cargados: %s", len(codigos))
            else:
                logger.warning("Columna 'COD_SERV_FACT' no encontrada en homologación")
                self._todos_cod_serv_fact = None
            logger.info("Homologación cargada: %s registros", len(df))
        except Exception as e:
            logger.error("Error cargando homologación: %s", e)
            self.df_homologacion = None
            self.homologador_df = None
            self._todos_cod_serv_fact = None

    def load_homologador(self) -> bool:
        """Carga homologador con reporte explícito (contrato Base)."""
        path = self.homologador_path or self.homologacion_path
        if not path:
            self.errors.append("No se especificó ruta de homologador")
            return False
        if not os.path.exists(path):
            self.errors.append(f"Archivo de homologador no encontrado: {path}")
            logger.error("Archivo de homologador no encontrado: %s", path)
            self.df_homologacion = None
            self.homologador_df = None
            return False
        try:
            df = pd.read_excel(path)
            df.columns = df.columns.str.strip()
            self.df_homologacion = df
            self.homologador_df = df
            self.homologacion_path = path
            self.homologador_path = path
            if 'COD_SERV_FACT' in df.columns:
                codigos = set(
                    df['COD_SERV_FACT'].dropna().astype(str).str.strip().tolist()
                )
                codigos.discard('0')
                codigos.discard('')
                self._todos_cod_serv_fact = codigos
            logger.info("Homologador cargado: %s registros", len(df))
            return True
        except Exception as e:
            self.errors.append(f"Error al cargar homologador: {str(e)}")
            logger.error("Error al cargar homologador: %s", e)
            self.df_homologacion = None
            self.homologador_df = None
            return False

    def _buscar_codigo_homologado(self, codigo_tecnologia):
        """
        Busca código homologado:
        1. Buscar en 'Código Servicio de la ERP'
        2. Tomar 'Código producto en DGH' de esa fila
        3. Verificar si existe en COD_SERV_FACT
        """
        if self.df_homologacion is None or pd.isna(codigo_tecnologia):
            return ''

        try:
            codigo_str = self._normalize_code(codigo_tecnologia)
            if not codigo_str or codigo_str == 'NAN':
                return ''

            col_erp = 'Código Servicio de la ERP'
            col_producto = 'Código producto en DGH'

            for col in [col_erp, col_producto, 'COD_SERV_FACT']:
                if col not in self.df_homologacion.columns:
                    return ''

            codigo_numerico = ''.join(filter(str.isdigit, codigo_str))

            mask = self.df_homologacion[col_erp].astype(str).str.strip().str.upper() == codigo_str
            resultado = self.df_homologacion[mask]

            if resultado.empty and codigo_numerico:
                mask = (
                    self.df_homologacion[col_erp].astype(str).str.replace(r'\D', '', regex=True)
                    == codigo_numerico
                )
                resultado = self.df_homologacion[mask]

            if not resultado.empty:
                codigo_producto = resultado.iloc[0][col_producto]

                if pd.notna(codigo_producto):
                    cod_str = self._normalize_code(codigo_producto)

                    if cod_str and cod_str != '0' and cod_str != 'NAN':
                        if self._todos_cod_serv_fact and cod_str in self._todos_cod_serv_fact:
                            return cod_str

                        if self._todos_cod_serv_fact:
                            cod_numerico = ''.join(filter(str.isdigit, cod_str))
                            if cod_numerico:
                                for cod in self._todos_cod_serv_fact:
                                    if ''.join(filter(str.isdigit, cod)) == cod_numerico:
                                        return cod

            return ''

        except Exception as e:
            logger.warning("Error homologando %s: %s", codigo_tecnologia, e)
            return ''

    def _aplicar_homologacion(self):
        """Aplica homologación a todos los registros (legacy, mantiene df)."""
        if self.df_consolidado is None or self.df_consolidado.empty:
            return

        if self.df_homologacion is None:
            self.df_consolidado['Codigo homologado DGH'] = ''
            return

        logger.info("Aplicando homologación a %s registros", len(self.df_consolidado))

        codigos = []
        encontrados = 0

        for _, row in self.df_consolidado.iterrows():  # pyright: ignore[reportGeneralTypeIssues]
            codigo = self._buscar_codigo_homologado(row.get('Tecnología'))
            codigos.append(codigo)
            if codigo:
                encontrados += 1

        self.df_consolidado['Codigo homologado DGH'] = codigos
        self.df_consolidado['Tecnologia NO homologada'] = self.df_consolidado.apply(
            lambda r: r['Tecnología'] if not r.get('Codigo homologado DGH') else '', axis=1
        )

        logger.info("Homologados: %s/%s", encontrados, len(self.df_consolidado))

    # ==================== CONTRATO BASE ====================

    def identify_files(
        self, file_paths: list[str]
    ) -> dict[str, Any] | list[dict[str, str]]:
        """Identifica TODOS los archivos Excel/CSV válidos de Mutualser."""
        validos = [
            f for f in file_paths
            if str(f).lower().endswith(('.xlsx', '.xls', '.xlsm', '.xlsb', '.csv'))
        ]
        logger.info("Mutualser: %s archivos identificados de %s", len(validos), len(file_paths))
        return {"archivos": validos}

    def validate_files(
        self, identified_files: dict[str, Any] | list[dict[str, str]]
    ) -> bool:
        """Valida que existan archivos por procesar."""
        if isinstance(identified_files, list):
            archivos = []
            for item in identified_files:
                if isinstance(item, dict):
                    archivos.extend([v for v in item.values() if isinstance(v, str)])
                elif isinstance(item, str):
                    archivos.append(item)
        elif isinstance(identified_files, dict):
            if "archivos" in identified_files:
                archivos = identified_files["archivos"]
            elif "detalle" in identified_files or "glosa" in identified_files:
                archivos = [v for v in identified_files.values() if isinstance(v, str)]
            else:
                archivos = list(identified_files.values())
        else:
            self.errors.append("Formato de archivos identificados no válido")
            return False

        if not archivos:
            self.errors.append("No se encontraron archivos para procesar")
            return False

        faltantes = [a for a in archivos if not os.path.exists(a)]
        if faltantes:
            # En tests con rutas ficticias se advierte pero no se bloquea si hay
            # al menos la estructura; en producción los archivos existen.
            # Para contrato Base se exige existencia.
            for f in faltantes:
                self.errors.append(f"Archivo no existe: {f}")
            return False
        return True

    def extract_data(
        self, identified_files: dict[str, Any] | list[dict[str, str]]
    ) -> dict[str, pd.DataFrame]:
        """Extrae y consolida datos de todos los archivos identificados."""
        if isinstance(identified_files, list):
            archivos: list[str] = []
            for item in identified_files:
                if isinstance(item, dict):
                    archivos.extend([v for v in item.values() if isinstance(v, str)])
                elif isinstance(item, str):
                    archivos.append(item)
        elif isinstance(identified_files, dict):
            if "archivos" in identified_files:
                archivos = list(identified_files["archivos"])
            else:
                archivos = [v for v in identified_files.values() if isinstance(v, str)]
        else:
            self.errors.append("Formato de archivos identificados no válido")
            return {}

        dfs = []
        for file_path in archivos:
            df = self.procesar_archivo(file_path)
            if df is not None and not df.empty:
                dfs.append(df)

        if not dfs:
            return {}

        consolidado = pd.concat(dfs, ignore_index=True)
        self.df_consolidado = consolidado
        return {"consolidado": consolidado, "detalle": consolidado}

    def homologate(self, data: dict[str, pd.DataFrame]) -> pd.DataFrame:
        """Homologa el consolidado y retorna DataFrame (contrato Base)."""
        df = data.get("consolidado", data.get("detalle"))
        if df is None or df.empty:
            self.errors.append("Faltan datos para homologar")
            return pd.DataFrame()

        self.df_consolidado = df.copy()
        self._aplicar_homologacion()
        result = self.df_consolidado
        if result is None:
            return pd.DataFrame()
        return result

    # ==================== PROCESAMIENTO DE ARCHIVOS ====================

    def procesar_archivo(self, file_path):
        """Procesa un archivo individual"""
        try:
            if not str(file_path).lower().endswith(('.xlsx', '.xls', '.xlsm', '.xlsb', '.csv')):
                self.errors.append(f"Formato no soportado: {file_path}")
                return None

            is_excel = str(file_path).lower().endswith(('.xlsx', '.xls', '.xlsm', '.xlsb'))
            df_raw = (
                pd.read_excel(file_path, header=None)
                if is_excel else pd.read_csv(file_path, header=None)
            )

            # Buscar fila de encabezados
            header_row_idx: int | None = None
            fecha_documento: str | None = None

            for idx, row in df_raw.iterrows():
                idx_int = int(idx) if isinstance(idx, (int, float)) else idx  # type: ignore
                row_str = ' '.join([str(c) for c in row if pd.notna(c)]).upper()

                if 'FECHA' in row_str and fecha_documento is None:
                    for cell in row:
                        if pd.notna(cell) and ('/' in str(cell) or '-' in str(cell)):
                            try:
                                fecha_documento = pd.to_datetime(cell).strftime('%Y-%m-%d')
                                break
                            except Exception:
                                pass

                if 'NUMERO DE FACTURA' in row_str or 'NÚMERO DE FACTURA' in row_str:
                    header_row_idx = idx_int  # type: ignore
                    break
                elif 'DETALLE DE GLOSA' in row_str:
                    header_row_idx = idx_int + 1  # type: ignore
                    break

            if header_row_idx is None:
                raise Exception("No se encontró tabla de detalles")

            df = (
                pd.read_excel(file_path, header=header_row_idx)
                if is_excel else pd.read_csv(file_path, header=header_row_idx)
            )
            df.columns = df.columns.str.strip()

            # Mapear columnas (sin prints para velocidad)
            df_extraido = self._mapear_columnas(df, fecha_documento, verbose=False)

            if df_extraido.empty:
                return None

            self.archivos_procesados.append(file_path)

            return df_extraido

        except Exception as e:
            self.errors.append(f"Error en {file_path}: {str(e)}")
            return None

    def _mapear_columnas(self, df, fecha_documento, verbose=True):
        """Mapea columnas del archivo a las requeridas"""
        if verbose:
            logger.debug("Columnas disponibles: %s", list(df.columns))

        df_extraido = pd.DataFrame()
        columnas_no_encontradas = []

        for col_req in self.COLUMNAS_REQUERIDAS:
            col_encontrada = self._buscar_columna(df, col_req)

            if col_encontrada:
                df_extraido[col_req] = df[col_encontrada]
            elif col_req == 'Fecha' and fecha_documento:
                df_extraido[col_req] = fecha_documento
            else:
                df_extraido[col_req] = None
                columnas_no_encontradas.append(col_req)

        if columnas_no_encontradas and verbose:
            logger.warning("Columnas no encontradas: %s", columnas_no_encontradas)

        # Limpiar filas
        filas_antes = len(df_extraido)
        df_extraido = df_extraido[df_extraido['Número de factura'].notna()].copy()
        df_extraido = df_extraido[~df_extraido['Número de factura'].astype(str).str.upper().str.contains('TOTAL|SUMA', na=False)]
        filas_despues = len(df_extraido)

        if verbose:
            logger.debug("Limpieza: %s -> %s registros", filas_antes, filas_despues)

        return df_extraido

    def _buscar_columna(self, df, col_requerida):
        """Busca columna de forma flexible"""
        col_clean = col_requerida.lower().replace('ó', 'o').replace('á', 'a').replace('é', 'e').replace('í', 'i').replace('ú', 'u')

        for col_df in df.columns:
            col_df_clean = str(col_df).lower().strip().replace('ó', 'o').replace('á', 'a').replace('é', 'e').replace('í', 'i').replace('ú', 'u')
            if col_clean in col_df_clean or col_df_clean in col_clean:
                return col_df
        return None

    def procesar_multiples_archivos(self, file_paths):
        """Procesa múltiples archivos"""
        total = len(file_paths)
        logger.info("Iniciando procesamiento de %s archivos", total)

        dfs = []

        for i, file_path in enumerate(file_paths):
            if (i + 1) % 10 == 0 or i == 0:
                logger.info("Progreso: %s/%s (%.1f%%)", i + 1, total, (i + 1) / total * 100 if total else 0)

            df = self.procesar_archivo(file_path)
            if df is not None and not df.empty:
                dfs.append(df)

        if dfs:
            logger.info("Consolidando %s DataFrames", len(dfs))
            self.df_consolidado = pd.concat(dfs, ignore_index=True)
            logger.info("Consolidado final: %s registros", len(self.df_consolidado))
            return self.df_consolidado

        logger.warning("No se pudo procesar ningun archivo")
        return None

    # ==================== GENERACIÓN DE OBJECIONES ====================

    def _generar_archivo_objeciones(self):
        """Genera archivo Objeciones.xlsx"""
        if self.df_consolidado is None or self.df_consolidado.empty:
            return None

        try:
            logger.info("Generando Objeciones.xlsx")

            df_obj = pd.DataFrame()

            # Columnas básicas
            facturas = self.df_consolidado['Número de factura'] if 'Número de factura' in self.df_consolidado.columns else pd.Series(dtype=object)
            factura_consecutivo = {f: i + 1 for i, f in enumerate(facturas.unique())}

            df_obj['CDCONSEC'] = facturas.map(factura_consecutivo)
            # Formato D/M/A (día/mes/año sin ceros a la izquierda)
            df_obj['CDFECDOC'] = datetime.now().strftime('%#d/%#m/%Y') if os.name == 'nt' else datetime.now().strftime('%-d/%-m/%Y')
            df_obj['CRNCXC'] = (self.df_consolidado['Número de factura'] if 'Número de factura' in self.df_consolidado.columns else pd.Series(dtype=object)).apply(self._formatear_crncxc)
            df_obj['CROFECOBJ'] = (self.df_consolidado['Fecha'] if 'Fecha' in self.df_consolidado.columns else pd.Series(dtype=object)).apply(self._formatear_fecha_dmy)
            df_obj['CROREFERE'] = ''
            df_obj['CROOBSERV'] = self.df_consolidado['REG GLOSA'] if 'REG GLOSA' in self.df_consolidado.columns else ''
            df_obj['CROCLAOBJ'] = 0
            df_obj['GENUSUARIO4'] = 1103858268
            df_obj['CRNCONOBJ'] = self.df_consolidado['Código de glosa'] if 'Código de glosa' in self.df_consolidado.columns else ''
            df_obj['SLNSERPRO'] = self.df_consolidado['Codigo homologado DGH'] if 'Codigo homologado DGH' in self.df_consolidado.columns else ''
            df_obj['CTNCENCOS'] = ''
            df_obj['IDRIPS'] = ''
            df_obj['CROVALOBJ'] = (self.df_consolidado['Valor glosado'] if 'Valor glosado' in self.df_consolidado.columns else pd.Series(dtype=float)).apply(self._obtener_valor_numerico)
            df_obj['CRDOBSERV'] = self.df_consolidado.apply(self._combinar_observaciones, axis=1)

            # Procesar AU/TA
            df_obj = self._procesar_au_ta(df_obj)

            # Exportar
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            output_path = os.path.join(self.output_dir, f"Objeciones_{timestamp}.xlsx")

            with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
                df_obj.to_excel(writer, sheet_name='OBJECIONES', index=False)

            logger.info("Generado: %s (%s registros)", output_path, len(df_obj))
            return output_path

        except Exception as e:
            logger.error("Error generando objeciones: %s", e)
            return None

    def _procesar_au_ta(self, df_obj):
        """Procesa filas AU/TA: combina con // y elimina duplicados"""
        logger.info("Procesando AU/TA")

        filas_eliminar = []
        procesadas = 0

        if 'CRNCXC' not in df_obj.columns or 'SLNSERPRO' not in df_obj.columns:
            return df_obj

        for (_factura, _tec), grupo in df_obj.groupby(['CRNCXC', 'SLNSERPRO']):
            if len(grupo) < 2:
                continue

            filas_au = [i for i, r in grupo.iterrows() if str(r.get('CRNCONOBJ', '')).upper().startswith('AU')]
            filas_ta = [i for i, r in grupo.iterrows() if str(r.get('CRNCONOBJ', '')).upper().startswith('TA')]

            if filas_au and filas_ta:
                idx_au = filas_au[0]

                for idx_ta in filas_ta:
                    obs_ta = str(df_obj.at[idx_ta, 'CRDOBSERV']).strip()
                    if obs_ta and obs_ta.lower() != 'nan':
                        obs_au = str(df_obj.at[idx_au, 'CRDOBSERV']).strip()
                        if obs_au.lower() == 'nan':
                            obs_au = ''
                        df_obj.at[idx_au, 'CRDOBSERV'] = f"{obs_au} // {obs_ta}" if obs_au else obs_ta

                    filas_eliminar.append(idx_ta)
                    procesadas += 1

        if filas_eliminar:
            df_obj = df_obj.drop(filas_eliminar).reset_index(drop=True)
            logger.info("%s filas TA procesadas", procesadas)

        return df_obj

    # ==================== UTILIDADES DE FORMATO ====================
    # Unificadas con Coosalud vía BaseProcessor (mismo contrato).

    def _formatear_crncxc(self, valor):
        return super()._formatear_crncxc(valor)

    def _formatear_fecha_dmy(self, fecha):
        return super()._formatear_fecha_dmy(fecha)

    def _obtener_valor_numerico(self, valor):
        return super()._obtener_valor_numerico(valor)

    def _combinar_observaciones(self, row):
        partes = []
        for col in ['Concepto de glosa', 'Observacion']:
            val = row.get(col, '')
            if pd.notna(val) and str(val).strip():
                partes.append(str(val).strip())
        return ' - '.join(partes)

    # ==================== EXPORTACIÓN ====================

    def exportar_consolidado(self, nombre_archivo=None):
        """Exporta consolidado y genera objeciones"""
        if self.df_consolidado is None or self.df_consolidado.empty:
            logger.error("No hay datos para exportar")
            return None

        try:
            # Filtrar filas vacías (sin Tecnología o sin Número de factura)
            filas_antes = len(self.df_consolidado)
            self.df_consolidado = self.df_consolidado[
                self.df_consolidado['Tecnología'].notna() &
                self.df_consolidado['Número de factura'].notna()
            ].copy()
            filas_despues = len(self.df_consolidado)

            if filas_antes != filas_despues:
                logger.info(
                    "Filtrado: %s -> %s registros (eliminadas %s filas vacías)",
                    filas_antes, filas_despues, filas_antes - filas_despues,
                )

            if self.df_consolidado.empty:
                logger.error("No hay datos válidos después del filtrado")
                return None

            # Homologar
            self._aplicar_homologacion()

            # Generar REG GLOSA
            self.df_consolidado['REG GLOSA'] = self.df_consolidado['Número de glosa'].apply(
                lambda x: f"REG, GLOSA SEGUN RAD N. {x}" if pd.notna(x) else ""
            )

            # Exportar consolidado
            if nombre_archivo is None:
                nombre_archivo = f"MUTUALSER_consolidado_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"

            output_path = os.path.join(self.output_dir, nombre_archivo)
            clean = self._drop_internal_columns(self.df_consolidado)
            clean.to_excel(output_path, index=False)
            logger.info("Consolidado: %s", output_path)

            # Generar objeciones
            objeciones_path = self._generar_archivo_objeciones()

            return (output_path, objeciones_path)

        except Exception as e:
            logger.error("Error exportando consolidado: %s", e)
            return None

    def get_resumen(self):
        """Obtiene resumen del procesamiento"""
        if self.df_consolidado is None:
            return {'total_registros': 0, 'archivos_procesados': 0, 'errores': len(self.errors)}

        return {
            'total_registros': len(self.df_consolidado),
            'archivos_procesados': len(self.archivos_procesados),
            'errores': len(self.errors),
            'facturas_unicas': self.df_consolidado['Número de factura'].nunique() if 'Número de factura' in self.df_consolidado.columns else 0,
            'codigos_homologados': (self.df_consolidado['Codigo homologado DGH'] != '').sum() if 'Codigo homologado DGH' in self.df_consolidado.columns else 0
        }
