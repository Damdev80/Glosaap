"""Lookup compartido de homologación ERP -> DGH (capa core).

Fuente única de la regla de negocio usada por MutualserProcessor y
HomologadorObservacion (antes duplicada en ambos):

1. Buscar el código en "Código Servicio de la ERP".
2. Tomar "Código producto en DGH" de esa fila.
3. Validarlo contra TODA la columna "COD_SERV_FACT".
"""
import logging

import pandas as pd

logger = logging.getLogger(__name__)

COL_ERP = "Código Servicio de la ERP"
COL_DGH = "Código producto en DGH"
COL_FACT = "COD_SERV_FACT"


def normalizar_codigo(code) -> str:
    """Normaliza un código: strip, upper, maneja floats/ints y NaN."""
    if pd.isna(code):
        return ""
    if isinstance(code, (int, float)):
        try:
            return str(int(code)).strip().upper()
        except (ValueError, OverflowError):
            return str(code).strip().upper()
    return str(code).strip().upper()


def _solo_digitos(texto: str) -> str:
    return "".join(filter(str.isdigit, texto))


def cargar_homologador_df(path: str) -> tuple[pd.DataFrame | None, set | None]:
    """Carga el xlsx de homologación. Falla explícito, sin fallback.

    Returns:
        (df con columnas limpias o None, set COD_SERV_FACT o None si no
        hay columna).
    """
    import os

    if not path or not os.path.exists(path):
        logger.error("Homologador no encontrado: %s", path)
        return None, None
    try:
        df = pd.read_excel(path)
        df.columns = df.columns.str.strip()
    except Exception as e:
        logger.error("Error cargando homologación %s: %s", path, e)
        return None, None
    fact = None
    if COL_FACT in df.columns:
        fact = set(df[COL_FACT].dropna().astype(str).str.strip().tolist())
        fact.discard("0")
        fact.discard("")
        logger.info("Códigos de homologación cargados: %s", len(fact))
    else:
        logger.warning("Columna 'COD_SERV_FACT' no encontrada en homologación")
    logger.info("Homologación cargada: %s registros", len(df))
    return df, fact


def buscar_codigo_homologado(
    df: pd.DataFrame | None, fact_set: set | None, codigo
) -> str:
    """Busca el DGH validado para un código. Retorna '' si no homologa."""
    if df is None or pd.isna(codigo):
        return ""
    try:
        codigo_str = normalizar_codigo(codigo)
        if not codigo_str or codigo_str == "NAN":
            return ""

        for col in (COL_ERP, COL_DGH, COL_FACT):
            if col not in df.columns:
                return ""

        codigo_numerico = _solo_digitos(codigo_str)
        mask = df[COL_ERP].astype(str).str.strip().str.upper() == codigo_str
        resultado = df[mask]

        if resultado.empty and codigo_numerico:
            mask = (
                df[COL_ERP].astype(str).str.replace(r"\D", "", regex=True)
                == codigo_numerico
            )
            resultado = df[mask]

        if resultado.empty:
            return ""

        codigo_producto = resultado.iloc[0][COL_DGH]
        if pd.isna(codigo_producto):
            return ""
        cod_str = normalizar_codigo(codigo_producto)
        if not cod_str or cod_str in ("0", "NAN"):
            return ""
        if fact_set and cod_str in fact_set:
            return cod_str
        if fact_set:
            cod_numerico = _solo_digitos(cod_str)
            if cod_numerico:
                for cod in fact_set:
                    if _solo_digitos(cod) == cod_numerico:
                        return cod
        return ""
    except Exception as e:
        logger.warning("Error homologando %s: %s", codigo, e)
        return ""
