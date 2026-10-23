"""
Procesador específico para archivos de Sanitas EPS.

Sanitas envía UN archivo .xlsx por correo (el PDF adjunto se ignora).
Cada fila representa una glosa con:
- N° Factura en columna NUMERO DE FACTURA -> CRNCXC (FC0000+numero).
- Código de objeción (CRNCONOBJ, 6 caracteres) = GENERAL mapeado (2 letras)
  + ESPECIFICO (2 dígitos, cero a la izquierda) + APLICACIÓN (2 dígitos,
  cero a la izquierda; "01" si vacía). GENERAL numérico 1-6 se mapea a
  FA/TA/SO/AU/CO/CL. Ej: 2 + 6 + (vacía) -> "TA0601".
- Observación = columna OBSERVACIONES; si vacía -> "MVC EN <procedimiento>".
- Homologación de CODIGO PROCEDIMIENTO PRESTADOR en dos vías: filas INSUMOS
  por cascada en sanitas_homologador.xlsx (CUM/IUM RDA/CODIGO PRODUCTO);
  resto por homologador normal sanitas_homologador_2.xlsx (ERP→DGH).
  Sin match se conserva el original.
- Fecha de objeción = fecha de recepción del correo (email_date).

El resultado homologado se guarda en SANITAS_GLOSAS_<ts>.xlsx y las
objeciones en Objeciones_SANITAS_<ts>.xlsx con el mismo set de columnas
que Mutualser/Coosalud + CRNCLAOBJ (siempre vacía).
"""
import os
from datetime import datetime
from typing import Any

import pandas as pd

from app.config.settings import logger

from .base_processor import BaseProcessor

# Mapeo de CODIGO CONCEPTO GENERAL numérico -> letras (regla confirmada).
# Si GENERAL ya trae letras se conserva (upper). Si es un número fuera de
# 1-6 se conserva el valor original sin mapear.
CONCEPTO_GENERAL_NUMERICO = {
    "1": "FA",
    "2": "TA",
    "3": "SO",
    "4": "AU",
    "5": "CO",
    "6": "CL",
}

# TODO (confirmar con el usuario): etiqueta exacta de insumos.
# Solo las filas donde NOMBRE PROCEDIMIENTO normalizado (strip, upper,
# espacios colapsados) == este valor homologan su código de servicio vía
# dict del homologador; las demás filas conservan el código original.
INSUMOS_PROCEDIMIENTO_LABEL = "INSUMOS Y MEDICAMENTOS INTRAHOSPITALARIOS"

# TODO (confirmar con el usuario): columnas candidatas por dato.
# Mapeo tolerante (exacto insensible a mayúsculas/espacios; primero el
# nombre exacto esperado). Si falta alguna requerida se registra el error
# explícito "Falta columna X (candidatas: ...)".
FACTURA_CANDIDATES = ["NUMERO DE FACTURA", "NUMERO FACTURA", "N° FACTURA", "FACTURA"]
VALOR_CANDIDATES = ["VALOR GLOSADO GLOSA", "VALOR GLOSADO", "VALOR", "VLR GLOSADO", "VALOR OBJETADO"]
SERVICIO_NOMBRE_CANDIDATES = ["NOMBRE PROCEDIMIENTO", "PROCEDIMIENTO", "SERVICIO"]
# Columna del código de servicio a homologar en el xlsx de Sanitas
# (confirmada): CODIGO PROCEDIMIENTO PRESTADOR. Se mantienen alias
# anteriores como fallback tolerante.
SERVICIO_CODIGO_CANDIDATES = [
    "CODIGO PROCEDIMIENTO PRESTADOR",
    "CÓDIGO PROCEDIMIENTO PRESTADOR",
    "CODIGO SERVICIO",
    "CÓDIGO SERVICIO",
    "CODIGO PROCEDIMIENTO",
    "CÓDIGO PROCEDIMIENTO",
    "CODIGO DEL SERVICIO",
    "COD_SERV_FACT",
    "COD SERVICIO",
]
COD_GENERAL_CANDIDATES = [
    "CODIGO CONCEPTO GENERAL",
    "CÓDIGO CONCEPTO GENERAL",
    "COD CONCEPTO GENERAL",
    "CONCEPTO GENERAL",
]
COD_ESPECIFICO_CANDIDATES = [
    "CODIGO CONCEPTO ESPECIFICO",
    "CÓDIGO CONCEPTO ESPECÍFICO",
    "CÓDIGO CONCEPTO ESPECIFICO",
    "COD CONCEPTO ESPECIFICO",
    "CONCEPTO ESPECIFICO",
]
COD_APLICACION_CANDIDATES = [
    "CODIGO CONCEPTO APLICACIÓN",
    "CODIGO CONCEPTO APLICACION",
    "CÓDIGO CONCEPTO APLICACIÓN",
    "CÓDIGO CONCEPTO APLICACION",
    "COD CONCEPTO APLICACION",
    "CONCEPTO APLICACION",
]
OBSERVACIONES_CANDIDATES = [
    "OBSERVACIONES",
    "OBSERVACION",
    "OBSERVACIÓN",
    "JUSTIFICACION",
    "JUSTIFICACIÓN",
]

# Homologador de insumos "sanitas_homologador.xlsx"
# (settings.HOMOLOGADOR_FILES["sanitas_insumos"]) con columnas literales
# "CUM" / "IUM RDA" / "CODIGO PRODUCTO". Solo filas INSUMOS homologan por
# cascada CUM -> CODIGO PRODUCTO, IUM RDA -> CODIGO PRODUCTO, o el propio
# CODIGO PRODUCTO si la clave aparece ahí.
INSUMOS_CUM_CANDIDATES = ["CUM"]
INSUMOS_IUM_CANDIDATES = ["IUM RDA", "IUMRDA", "IUM_RDA", "IUM", "RDA"]
INSUMOS_PRODUCTO_CANDIDATES = ["CODIGO PRODUCTO", "CÓDIGO PRODUCTO", "COD PRODUCTO"]

# Homologador normal (settings.HOMOLOGADOR_FILES["sanitas"]:
# sanitas_homologador_2.xlsx con columnas "CODIGO PROCEDIMIENTO PRESTADOR"
# / "CODIGO HOMOLOGO") para filas NO insumos. Se acepta layout estilo
# mutualser (ERP/DGH) como fallback.
HOMOLOGADOR_ERP_COL = "Código Servicio de la ERP"
HOMOLOGADOR_DGH_COL = "Código producto en DGH"
HOMOLOGADOR_COD_FACT_COL = "COD_SERV_FACT"

# Columnas de salida del archivo de objeciones: mismo set que
# Mutualser/Coosalud + CRNCLAOBJ (siempre vacía).
OBJECIONES_COLUMNS = [
    "CDCONSEC",
    "CDFECDOC",
    "CRNCXC",
    "CROFECOBJ",
    "CROREFERE",
    "CROOBSERV",
    "CROCLAOBJ",
    "CRNCLAOBJ",
    "GENUSUARIO4",
    "CRNCONOBJ",
    "SLNSERPRO",
    "CTNCENCOS",
    "IDRIPS",
    "CROVALOBJ",
    "CRDOBSERV",
]

GENUSUARIO4_FIJO = 1103858268


class SanitasProcessor(BaseProcessor):
    """Procesador de archivos de glosas de Sanitas EPS."""

    def __init__(self, homologador_path: str | None = None, homologador_insumos_path: str | None = None):
        super().__init__(homologador_path or "")
        self.sanitas_df: pd.DataFrame | None = None
        self._last_objeciones_df: pd.DataFrame | None = None
        self.homologador_insumos_path = homologador_insumos_path or ""
        self.insumos_df: pd.DataFrame | None = None
        # Dicts de la vía insumos (claves flexibles -> CODIGO PRODUCTO).
        self._cum_dict: dict[str, str] = {}
        self._ium_dict: dict[str, str] = {}
        self._producto_dict: dict[str, str] = {}

    # ==================== HOMOLOGADOR ====================

    def load_homologador(self) -> bool:
        """Carga el homologador (columnas con strip, sin fallback)."""
        if not self.homologador_path:
            self.errors.append("No se especificó ruta de homologador")
            return False
        if not os.path.exists(self.homologador_path):
            self.errors.append(
                f"Archivo de homologador no encontrado: {self.homologador_path}"
            )
            logger.error("Homologador Sanitas no encontrado: %s", self.homologador_path)
            return False
        try:
            df = pd.read_excel(self.homologador_path)
            df.columns = [str(c).strip() for c in df.columns]
            self.homologador_df = df
            logger.info("Homologador Sanitas cargado: %s registros", len(df))
            return True
        except Exception as e:
            self.errors.append(f"Error al cargar homologador: {str(e)}")
            logger.error("Error cargando homologador Sanitas: %s", e)
            return False

    def load_homologador_insumos(self) -> bool:
        """Carga sanitas_homologador.xlsx (CUM / IUM RDA / CODIGO PRODUCTO).

        Precomputa los 3 dicts de la cascada INSUMOS con claves flexibles.
        Sin el archivo se retorna False (el llamador decide si es fatal).
        """
        if not self.homologador_insumos_path:
            self.errors.append("No se especificó ruta de homologador de insumos")
            return False
        if not os.path.exists(self.homologador_insumos_path):
            self.errors.append(
                "Archivo de homologador de insumos no encontrado: "
                f"{self.homologador_insumos_path}"
            )
            logger.error(
                "Homologador insumos Sanitas no encontrado: %s",
                self.homologador_insumos_path,
            )
            return False
        try:
            df = pd.read_excel(self.homologador_insumos_path)
            df.columns = [str(c).strip() for c in df.columns]
            norm = {str(c).strip().upper(): c for c in df.columns}

            def _col(cands: list[str], logical: str) -> str | None:
                for cand in cands:
                    if cand.upper() in norm:
                        return norm[cand.upper()]
                self.errors.append(
                    f"Homologador insumos sin columna {logical} "
                    f"(candidatas: {', '.join(cands)})"
                )
                return None

            col_cum = _col(INSUMOS_CUM_CANDIDATES, "CUM")
            col_ium = _col(INSUMOS_IUM_CANDIDATES, "IUM RDA")
            col_prod = _col(INSUMOS_PRODUCTO_CANDIDATES, "CODIGO PRODUCTO")
            if col_cum is None or col_ium is None or col_prod is None:
                return False

            cum: dict[str, str] = {}
            ium: dict[str, str] = {}
            prod: dict[str, str] = {}
            for _, row in df.iterrows():
                producto = "" if pd.isna(row[col_prod]) else str(row[col_prod]).strip()
                if producto:
                    prod.setdefault(self._clave_lookup(producto), producto)
                for col, dest in ((col_cum, cum), (col_ium, ium)):
                    clave = self._clave_lookup(row[col])
                    if clave and producto:
                        dest.setdefault(clave, producto)

            self.insumos_df = df
            self._cum_dict = cum
            self._ium_dict = ium
            self._producto_dict = prod
            logger.info(
                "Homologador insumos Sanitas cargado: %s CUM, %s IUM, %s productos",
                len(cum),
                len(ium),
                len(prod),
            )
            return True
        except Exception as e:
            self.errors.append(f"Error al cargar homologador de insumos: {str(e)}")
            logger.error("Error cargando homologador insumos Sanitas: %s", e)
            return False

    # ==================== TEMPLATE METHOD ====================

    def identify_files(self, file_paths: list[str]) -> list[str]:
        """Retorna solo los .xlsx (el PDF se ignora).

        Sanitas envía UN xlsx por correo (no pares DETALLE+GLOSAS).
        """
        paths = list(file_paths or [])
        xlsx = [f for f in paths if str(f).lower().endswith(".xlsx")]
        ignorados = len(paths) - len(xlsx)
        if ignorados:
            logger.info("Sanitas: %s archivos no-xlsx ignorados (PDF se ignora)", ignorados)
        logger.info("Sanitas: %s xlsx identificados", len(xlsx))
        return xlsx

    def validate_files(
        self, identified_files: list[str] | list[dict[str, str]] | dict[str, Any]
    ) -> bool:
        """Valida que cada xlsx identificado exista en disco."""
        if isinstance(identified_files, dict):
            paths: list[Any] = list(identified_files.values())
        elif isinstance(identified_files, list):
            paths = []
            for item in identified_files:
                if isinstance(item, dict):
                    found = None
                    for value in item.values():
                        if isinstance(value, str) and value.lower().endswith(
                            (".xlsx", ".xls", ".xlsm", ".csv")
                        ):
                            found = value
                            break
                    if found is None:
                        self.errors.append(f"Entrada sin ruta de archivo válida: {item}")
                        continue
                    paths.append(found)
                else:
                    paths.append(item)
        else:
            self.errors.append("Entradas de archivos no válidas para Sanitas")
            return False

        if not paths:
            self.errors.append("No se encontraron archivos xlsx de Sanitas")
            return False

        ok = True
        for path in paths:
            if not isinstance(path, str) or not os.path.exists(path):
                self.errors.append(f"Archivo Sanitas no existe: {path}")
                ok = False
        return ok

    def extract_data(
        self, identified_files: list[str] | list[dict[str, str]] | dict[str, Any]
    ) -> dict[str, pd.DataFrame]:
        """Lee y concatena los xlsx de Sanitas en un solo DataFrame."""
        if isinstance(identified_files, dict):
            paths = list(identified_files.values())
        else:
            paths = []
            for item in identified_files or []:
                if isinstance(item, dict):
                    for value in item.values():
                        if isinstance(value, str):
                            paths.append(value)
                            break
                else:
                    paths.append(item)

        frames = []
        for path in paths:
            try:
                df = pd.read_excel(path)
                frames.append(df)
            except Exception as e:
                self.errors.append(f"Error al leer {path}: {str(e)}")
                continue

        if not frames:
            return {}
        combined = pd.concat(frames, ignore_index=True)
        self.sanitas_df = combined
        logger.info("Sanitas extract: %s filas de %s archivos", len(combined), len(frames))
        return {"sanitas": combined}

    # ==================== HELPERS ====================

    def _resolve_column(
        self, df: pd.DataFrame, candidates: list[str], logical: str
    ) -> str | None:
        """Mapeo tolerante: exacto insensible a mayúsculas/espacios.

        El nombre exacto esperado va primero en `candidates`. Si no hay
        match, registra el error explícito y retorna None.
        """
        norm = {str(c).strip().upper(): c for c in df.columns}
        for cand in candidates:
            key = str(cand).strip().upper()
            if key in norm:
                return norm[key]
        self.errors.append(f"Falta columna {logical} (candidatas: {', '.join(candidates)})")
        return None

    def _resolve_column_optional(
        self, df: pd.DataFrame, candidates: list[str]
    ) -> str | None:
        """Mapeo tolerante sin error si no existe (supuesto TODO)."""
        norm = {str(c).strip().upper(): c for c in df.columns}
        for cand in candidates:
            key = str(cand).strip().upper()
            if key in norm:
                return norm[key]
        return None

    def _find_homolog_column(
        self, keywords: list[str], exact_match: str | None = None
    ) -> str | None:
        if self.homologador_df is None:
            return None
        if exact_match:
            for col in self.homologador_df.columns:
                if str(col).strip() == exact_match:
                    return col
        for col in self.homologador_df.columns:
            col_lower = str(col).lower()
            if all(kw in col_lower for kw in keywords):
                return col
        return None

    def _build_homologation_dict(self) -> dict[str, str]:
        """Construye {codigo_erp: codigo_dgh} estilo mutualser.

        Sin homologador cargado retorna {} con warning (se continúa sin
        homologar, conservando códigos originales).
        """
        if self.homologador_df is None:
            self.warnings.append("No hay archivo de homologación cargado")
            return {}

        erp_col = self._find_homolog_column(
            keywords=["codigo", "procedimiento", "prestador"],
            exact_match="CODIGO PROCEDIMIENTO PRESTADOR",
        )
        dgh_col = self._find_homolog_column(
            keywords=["codigo", "homologo"], exact_match="CODIGO HOMOLOGO"
        )
        if erp_col is None or dgh_col is None:
            # Fallback: layout estilo mutualser (ERP/DGH).
            erp_col = self._find_homolog_column(
                keywords=["codigo", "servicio", "erp"], exact_match=HOMOLOGADOR_ERP_COL
            )
            dgh_col = self._find_homolog_column(
                keywords=["codigo", "dgh"], exact_match=HOMOLOGADOR_DGH_COL
            )
        if erp_col is None or dgh_col is None:
            self.warnings.append(
                "Homologador Sanitas sin columnas ERP/DGH esperadas; se continúa sin homologar"
            )
            logger.warning("Homologador Sanitas sin columnas ERP/DGH esperadas")
            return {}

        validos_cod_fact: set | None = None
        if HOMOLOGADOR_COD_FACT_COL in self.homologador_df.columns:
            validos_cod_fact = set(
                self.homologador_df[HOMOLOGADOR_COD_FACT_COL]
                .dropna()
                .astype(str)
                .str.strip()
                .str.upper()
                .tolist()
            )
            validos_cod_fact.discard("0")
            validos_cod_fact.discard("")

        homolog_dict: dict[str, str] = {}
        for _, row in self.homologador_df.iterrows():
            codigo_erp = self._normalize_code(row[erp_col])
            codigo_dgh = self._normalize_code(row[dgh_col])
            if not codigo_erp or codigo_erp in ("NAN", "NONE", ""):
                continue
            if not codigo_dgh or codigo_dgh in ("0", "NAN", "NONE", ""):
                continue
            if validos_cod_fact is not None and codigo_dgh not in validos_cod_fact:
                continue
            homolog_dict[codigo_erp] = codigo_dgh

        logger.info("Sanitas: %s códigos en homologador", len(homolog_dict))
        return homolog_dict

    @staticmethod
    def _solo_digitos(valor: Any) -> str:
        """Extrae solo los dígitos de un valor ("" si no hay)."""
        if pd.isna(valor):
            return ""
        return "".join(ch for ch in str(valor) if ch.isdigit())

    @staticmethod
    def _clave_lookup(valor: Any) -> str:
        """Clave flexible para la cascada de insumos.

        Strip + upper + sin espacios/puntos/guiones, para que formatos
        como "1 234", "1.234" o "1-234" matcheen igual.
        """
        if pd.isna(valor):
            return ""
        return "".join(
            ch for ch in str(valor).strip().upper() if ch not in (" ", ".", "-")
        )

    @staticmethod
    def _normalizar_procedimiento(valor: Any) -> str:
        if pd.isna(valor):
            return ""
        return " ".join(str(valor).strip().upper().split())

    # ==================== HOMOLOGATE ====================

    def homologate(self, data: dict[str, pd.DataFrame]) -> pd.DataFrame:
        """Homologa filas de Sanitas y retorna DataFrame (contrato Base).

        Calcula por fila: CRNCXC, CRNCONOBJ (6 caracteres: GENERAL mapeado
        + ESPECIFICO 2 dígitos + APLICACIÓN 2 dígitos), CRDOBSERV (con
        fallback "MVC EN <procedimiento>" si vacía), SLNSERPRO (INSUMOS por
        cascada CUM/IUM/CODIGO PRODUCTO del archivo de insumos; resto por
        homologador normal; si nada matchea conserva el original) y
        CROVALOBJ.
        """
        df: pd.DataFrame | None = None
        if isinstance(data, dict):
            if isinstance(data.get("sanitas"), pd.DataFrame):
                df = data["sanitas"]
            else:
                for value in data.values():
                    if isinstance(value, pd.DataFrame):
                        df = value
                        break

        if df is None or df.empty:
            self.errors.append("Faltan datos para homologar (Sanitas)")
            return pd.DataFrame()

        work = df.copy()
        work.columns = [str(c).strip() for c in work.columns]

        col_factura = self._resolve_column(work, FACTURA_CANDIDATES, "NUMERO DE FACTURA")
        col_valor = self._resolve_column(work, VALOR_CANDIDATES, "VALOR GLOSADO")
        col_nombre = self._resolve_column(
            work, SERVICIO_NOMBRE_CANDIDATES, "NOMBRE PROCEDIMIENTO"
        )
        col_gen = self._resolve_column(
            work, COD_GENERAL_CANDIDATES, "CODIGO CONCEPTO GENERAL"
        )
        col_esp = self._resolve_column(
            work, COD_ESPECIFICO_CANDIDATES, "CODIGO CONCEPTO ESPECIFICO"
        )
        col_apl = self._resolve_column(
            work, COD_APLICACION_CANDIDATES, "CODIGO CONCEPTO APLICACIÓN"
        )
        col_obs = self._resolve_column(work, OBSERVACIONES_CANDIDATES, "OBSERVACIONES")
        col_cod_serv = self._resolve_column_optional(work, SERVICIO_CODIGO_CANDIDATES)

        if any(
            c is None
            for c in (col_factura, col_valor, col_nombre, col_gen, col_esp, col_apl, col_obs)
        ):
            return pd.DataFrame()

        assert col_factura and col_valor and col_nombre
        assert col_gen and col_esp and col_apl and col_obs

        homolog_dict = self._build_homologation_dict()

        # CRNCXC con helper compartido (FC0000+numero).
        work["CRNCXC"] = work[col_factura].apply(self._formatear_crncxc)
        work["_FACTURA"] = work[col_factura]
        if "fecha_correo" not in work.columns:
            work["fecha_correo"] = ""

        # CRNCONOBJ de 6 caracteres: GENERAL (2 letras, numérico 1-6
        # mapeado) + ESPECIFICO (2 dígitos, cero a la izquierda) +
        # APLICACIÓN (2 dígitos, cero a la izquierda; "01" si vacía).
        # Ej: GENERAL=2, ESPECIFICO=6, APLICACIÓN vacía -> "TA0601".
        def _codigo(row: pd.Series) -> str:
            gen = self._normalize_code(row[col_gen])
            gen = CONCEPTO_GENERAL_NUMERICO.get(gen, gen)
            esp = self._solo_digitos(row[col_esp]) or "00"
            apl = self._solo_digitos(row[col_apl]) or "01"
            return f"{gen}{esp.zfill(2)}{apl.zfill(2)}"

        work["CRNCONOBJ"] = work.apply(_codigo, axis=1)

        # CRDOBSERV: OBSERVACIONES; si vacía -> "MVC EN <procedimiento>".
        def _observacion(row: pd.Series) -> str:
            raw = row[col_obs]
            obs = "" if pd.isna(raw) else str(raw).strip()
            if obs:
                return obs
            nombre_raw = row[col_nombre]
            nombre = "" if pd.isna(nombre_raw) else str(nombre_raw).strip()
            return f"MVC EN {nombre}".strip()

        work["CRDOBSERV"] = work.apply(_observacion, axis=1)

        # SLNSERPRO: INSUMOS por cascada (CUM -> producto, IUM RDA ->
        # producto, producto directo); resto por homologador normal; si nada
        # matchea se conserva el original.
        sln: list[str] = []
        homologados = 0
        for _, row in work.iterrows():
            nombre_norm = self._normalizar_procedimiento(row[col_nombre])
            original = self._normalize_code(row[col_cod_serv]) if col_cod_serv else ""
            nuevo = ""
            if nombre_norm == INSUMOS_PROCEDIMIENTO_LABEL and original:
                clave = self._clave_lookup(original)
                if clave in self._cum_dict:
                    nuevo = self._cum_dict[clave]
                elif clave in self._ium_dict:
                    nuevo = self._ium_dict[clave]
                elif clave in self._producto_dict:
                    nuevo = self._producto_dict[clave]
            elif original and original in homolog_dict:
                nuevo = homolog_dict[original]
            if nuevo:
                sln.append(nuevo)
                homologados += 1
            else:
                sln.append(original)
        work["SLNSERPRO"] = sln
        logger.info(
            "Sanitas homologación: %s filas, %s homologadas",
            len(work),
            homologados,
        )

        # CROVALOBJ preservando decimales.
        work["CROVALOBJ"] = work[col_valor].apply(self._obtener_valor_numerico)

        return work

    # ==================== OBJECIONES ====================

    def _procesar_au_ta(self, df_obj: pd.DataFrame) -> pd.DataFrame:
        """Unifica AU/TA como Coosalud: combina en fila AU con // y elimina TA."""
        logger.info("Sanitas procesando AU/TA")
        if "CRNCXC" not in df_obj.columns or "SLNSERPRO" not in df_obj.columns:
            return df_obj

        filas_eliminar: list[Any] = []
        procesadas = 0

        for (_, _), grupo in df_obj.groupby(["CRNCXC", "SLNSERPRO"]):
            if len(grupo) < 2:
                continue
            filas_au = [
                i for i, r in grupo.iterrows()
                if str(r.get("CRNCONOBJ", "")).upper().startswith("AU")
            ]
            filas_ta = [
                i for i, r in grupo.iterrows()
                if str(r.get("CRNCONOBJ", "")).upper().startswith("TA")
            ]
            if filas_au and filas_ta:
                idx_au = filas_au[0]
                for idx_ta in filas_ta:
                    obs_ta = str(df_obj.at[idx_ta, "CRDOBSERV"]).strip()
                    if obs_ta:
                        obs_au = str(df_obj.at[idx_au, "CRDOBSERV"]).strip()
                        obs_au_clean = "" if obs_au.lower() == "nan" else obs_au
                        obs_ta_clean = "" if obs_ta.lower() == "nan" else obs_ta
                        if obs_ta_clean:
                            df_obj.at[idx_au, "CRDOBSERV"] = (
                                f"{obs_au_clean} // {obs_ta_clean}"
                                if obs_au_clean
                                else obs_ta_clean
                            )
                    filas_eliminar.append(idx_ta)
                    procesadas += 1

        if filas_eliminar:
            df_obj = df_obj.drop(filas_eliminar).reset_index(drop=True)
            logger.info("Sanitas: %s filas TA procesadas", procesadas)
        return df_obj

    def _build_objeciones_df(
        self, detalle_df: pd.DataFrame, email_date: str | None = None
    ) -> pd.DataFrame:
        """Construye el DataFrame de objeciones (mismo set + CRNCLAOBJ)."""
        hoy_doc = (
            datetime.now().strftime("%#d/%#m/%Y")
            if os.name == "nt"
            else datetime.now().strftime("%-d/%-m/%Y")
        )
        hoy_dmy = datetime.now().strftime("%d/%m/%Y")

        df_obj = pd.DataFrame()

        if "CRNCXC" in detalle_df.columns and detalle_df["CRNCXC"].notna().any():
            facturas = detalle_df["CRNCXC"]
        elif "_FACTURA" in detalle_df.columns:
            facturas = detalle_df["_FACTURA"]
        else:
            facturas = None

        if facturas is not None:
            mapa = {f: i + 1 for i, f in enumerate(pd.unique(facturas))}
            df_obj["CDCONSEC"] = facturas.map(mapa)
        else:
            df_obj["CDCONSEC"] = range(1, len(detalle_df) + 1)

        df_obj["CDFECDOC"] = hoy_doc
        df_obj["CRNCXC"] = detalle_df["CRNCXC"] if "CRNCXC" in detalle_df.columns else ""

        # CROFECOBJ: fecha de recepción del correo por fila (DD/MM/AAAA).
        if "fecha_correo" in detalle_df.columns and (
            detalle_df["fecha_correo"].astype(str).str.strip() != ""
        ).any():
            df_obj["CROFECOBJ"] = detalle_df["fecha_correo"].apply(
                lambda v: self._formatear_fecha_dmy(v) or hoy_dmy
            )
        elif email_date:
            df_obj["CROFECOBJ"] = self._formatear_fecha_dmy(email_date) or hoy_dmy
        else:
            df_obj["CROFECOBJ"] = hoy_dmy

        df_obj["CROREFERE"] = ""
        df_obj["CROOBSERV"] = df_obj["CROFECOBJ"].apply(
            lambda fecha: f"REG, GLOSA SEGÚN RAD N. {fecha}" if fecha else ""
        )
        df_obj["CROCLAOBJ"] = 0
        df_obj["CRNCLAOBJ"] = ""
        df_obj["GENUSUARIO4"] = GENUSUARIO4_FIJO
        df_obj["CRNCONOBJ"] = detalle_df["CRNCONOBJ"] if "CRNCONOBJ" in detalle_df.columns else ""
        df_obj["SLNSERPRO"] = detalle_df["SLNSERPRO"] if "SLNSERPRO" in detalle_df.columns else ""
        df_obj["CTNCENCOS"] = ""
        df_obj["IDRIPS"] = ""
        df_obj["CROVALOBJ"] = detalle_df["CROVALOBJ"] if "CROVALOBJ" in detalle_df.columns else 0.0
        if "CRDOBSERV" in detalle_df.columns:
            df_obj["CRDOBSERV"] = detalle_df["CRDOBSERV"].fillna("")
        else:
            df_obj["CRDOBSERV"] = ""

        df_obj = self._procesar_au_ta(df_obj)
        return df_obj[OBJECIONES_COLUMNS]

    def _generar_archivo_objeciones(
        self,
        detalle_df: pd.DataFrame,
        output_dir: str,
        email_date: str | None = None,
    ) -> str | None:
        """Genera Objeciones_SANITAS_<ts>.xlsx a partir del detalle."""
        if detalle_df is None or detalle_df.empty:
            self.errors.append("No hay datos para generar objeciones (Sanitas)")
            return None
        try:
            logger.info("Sanitas generando Objeciones.xlsx")
            df_obj = self._build_objeciones_df(detalle_df, email_date)
            self._last_objeciones_df = df_obj
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = os.path.join(output_dir, f"Objeciones_SANITAS_{timestamp}.xlsx")
            with pd.ExcelWriter(output_path, engine="openpyxl") as writer:
                df_obj.to_excel(writer, sheet_name="OBJECIONES", index=False)
            logger.info(
                "Sanitas objeciones generadas: %s (%s registros)", output_path, len(df_obj)
            )
            return output_path
        except Exception as e:
            self.errors.append(f"Error generando objeciones Sanitas: {str(e)}")
            logger.error("Error generando objeciones Sanitas: %s", e)
            return None

    def save_to_excel(self, data: dict[str, pd.DataFrame], output_path: str) -> bool:
        """Guarda el consolidado Sanitas (hoja Glosas, sin columnas internas)."""
        try:
            df = data.get("detalle") if isinstance(data, dict) else data
            if df is None:
                self.errors.append("Sin datos de detalle para guardar (Sanitas)")
                return False
            clean = self._drop_internal_columns(df)
            with pd.ExcelWriter(output_path, engine="openpyxl") as writer:
                clean.to_excel(writer, sheet_name="Glosas", index=False)
            logger.info("Sanitas archivo guardado: %s", output_path)
            return True
        except Exception as e:
            self.errors.append(f"Error al guardar archivo Sanitas: {str(e)}")
            return False

    # ==================== FLUJO PRINCIPAL ====================

    def process_glosas(
        self,
        file_paths: list[str],
        output_dir: str | None = None,
        email_date: str | None = None,
        attachment_service: Any = None,
    ) -> tuple[dict[str, pd.DataFrame] | None, str]:
        """Procesa los xlsx de Sanitas (patrón CoosaludProcessor.process_glosas).

        Args:
            file_paths: Rutas a los xlsx (un xlsx por correo; PDF se ignora).
            output_dir: Directorio de salida (opcional).
            email_date: Fecha de recepción del correo '%Y-%m-%d %H:%M:%S'.
            attachment_service: Metadatos con fecha individual por archivo.

        Returns:
            Tupla (dict {"detalle", "glosa", "objeciones"}, mensaje).
        """
        self.errors = []
        self.warnings = []
        self._last_objeciones_df = None

        logger.info("SANITAS procesador glosas: inicio")

        if self.homologador_path:
            logger.info("Sanitas cargando homologador")
            if not self.load_homologador():
                return None, f"[ERROR] Error: {'; '.join(self.errors)}"
        else:
            self.warnings.append("Sin archivo de homologación; se continúa sin homologar")
            logger.warning("Sanitas sin archivo de homologación")

        # Homologador de insumos (CUM/IUM): si falta, se avisa y las filas
        # INSUMOS conservan el original (no es fatal).
        if self.homologador_insumos_path:
            logger.info("Sanitas cargando homologador de insumos")
            n_err = len(self.errors)
            if not self.load_homologador_insumos():
                self.warnings.extend(self.errors[n_err:])
                del self.errors[n_err:]
                logger.warning("Sanitas sin homologador de insumos")
        else:
            self.warnings.append("Sin homologador de insumos; INSUMOS conserva original")
            logger.warning("Sanitas sin homologador de insumos")

        xlsx = self.identify_files(file_paths or [])
        if not xlsx:
            self.errors.append("No se encontraron archivos xlsx de Sanitas")
            return None, f"[ERROR] Error: {'; '.join(self.errors)}"

        if not self.validate_files(xlsx):
            return None, f"[ERROR] Error: {'; '.join(self.errors)}"

        # Lectura por archivo para asignar fecha de correo individual.
        frames = []
        archivos_error = 0
        for path in xlsx:
            try:
                df = pd.read_excel(path)
                metadata = None
                if attachment_service is not None:
                    try:
                        metadata = attachment_service.get_file_metadata(path)
                    except Exception:
                        metadata = None
                if metadata and metadata.get("email_date"):
                    raw_date = metadata["email_date"]
                elif email_date:
                    raw_date = email_date
                else:
                    raw_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                df["fecha_correo"] = raw_date
                frames.append(df)
            except Exception as e:
                archivos_error += 1
                self.warnings.append(f"Error en {os.path.basename(path)}: {str(e)}")
                continue

        if not frames:
            self.errors.append("No se pudo procesar ningún archivo xlsx")
            return None, f"[ERROR] Error: {'; '.join(self.errors)}"

        combined = pd.concat(frames, ignore_index=True)
        logger.info("Sanitas: %s filas combinadas de %s archivos", len(combined), len(frames))
        if archivos_error:
            logger.warning("Sanitas archivos con error: %s", archivos_error)

        detalle = self.homologate({"sanitas": combined})
        if detalle is None or detalle.empty:
            return None, f"[ERROR] Error: {'; '.join(self.errors) or 'sin datos homologados'}"

        objeciones_df = self._build_objeciones_df(detalle, email_date)
        result_data: dict[str, pd.DataFrame] = {
            "detalle": detalle,
            "glosa": objeciones_df,
            "objeciones": objeciones_df,
        }

        if output_dir:
            try:
                os.makedirs(output_dir, exist_ok=True)
            except Exception as exc:
                logger.warning("No se pudo crear directorio Sanitas %s: %s", output_dir, exc)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_files = []

            output_path = os.path.join(output_dir, f"SANITAS_GLOSAS_{timestamp}.xlsx")
            logger.info("Sanitas guardando consolidado")
            if self.save_to_excel({"detalle": detalle}, output_path):
                output_files.append(os.path.basename(output_path))

            obj_path = self._generar_archivo_objeciones(detalle, output_dir, email_date)
            if obj_path:
                output_files.append(os.path.basename(obj_path))
                # Reusar el df ya procesado (con AU/TA) para el retorno.
                if self._last_objeciones_df is not None:
                    result_data["glosa"] = self._last_objeciones_df
                    result_data["objeciones"] = self._last_objeciones_df

            if output_files:
                files_str = ", ".join(output_files)
                return result_data, f"[OK] Procesado exitosamente. Archivos: {files_str}"
            return result_data, f"[WARNING] Procesado pero error al guardar: {'; '.join(self.errors)}"

        return result_data, f"[OK] Procesados {len(xlsx)} archivos xlsx"
