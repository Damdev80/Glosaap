"""Procesador específico para Previsora Seguros SOAT.

Entrada: uno o varios PDF por correo ("Liquidación de reclamaciones").
Cada PDF puede traer una o varias liquidaciones agrupadas. Por cada
ítem se extrae:
- Nro Factura (adicional, ej. FC515083) -> CRNCXC (FC0000+numero).
- Cant. / Código / Procedimiento / % / Cobrado / Objeción / Liquidado
  (columnas marcadas en rojo) + Observación del ítem.
- Nro Radicado y Siniestro SISE como contexto por sección.

Salida (fase 1, objeciones aún NO): PREVISORA_REGISTRO_<ts>.xlsx con
exactamente NRO_FACTURA + columnas rojas + OBSERVACION. Sin homologador
(aún no lo pasan): SLNSERPRO conserva el código original con warning.
Fecha de objeción futura = fecha de recepción del correo (email_date).

Sigue el Template Method de BaseProcessor: identify_files (TODOS los
PDF, nunca solo el primero), validate_files, extract_data, homologate
(retorna pd.DataFrame). Sin print en loops; usa app.config.settings.logger.
"""
import os
import re
from datetime import datetime
from typing import Any

import pandas as pd

from app.config.settings import logger

from .base_processor import BaseProcessor

# Columnas del Excel de registro a entregar (rojo + factura adicional).
REGISTRO_COLUMNS = [
    "NRO_FACTURA",
    "CANT",
    "CODIGO",
    "PROCEDIMIENTO",
    "PORCENTAJE",
    "COBRADO",
    "OBJECION",
    "LIQUIDADO",
    "OBSERVACION",
]

# Homologador futuro (aún no lo pasan): previsora_homologacion.xlsx con
# "CODIGO PREVISORA" / "CODIGO HOMOLOGO" (acepta layout ERP/DGH fallback).
HOMOLOGADOR_PREV_COL = "CODIGO PREVISORA"
HOMOLOGADOR_HOMO_COL = "CODIGO HOMOLOGO"
HOMOLOGADOR_ERP_COL = "Código Servicio de la ERP"
HOMOLOGADOR_DGH_COL = "Código producto en DGH"

GENUSUARIO4_FIJO = 1103858268


class PrevisoraProcessor(BaseProcessor):
    """Procesa PDFs de liquidación de Previsora a Excel de registro."""

    def __init__(self, homologador_path: str | None = None):
        super().__init__(homologador_path or "")
        self.previsora_df: pd.DataFrame | None = None
        self._dict_cache: dict[str, str] | None = None

    # ==================== HOMOLOGADOR (futuro) ====================

    def load_homologador(self) -> bool:
        """Carga el homologador con strip; sin archivo se continúa sin homologar."""
        if not self.homologador_path:
            self.errors.append("No se especificó ruta de homologador")
            return False
        if not os.path.exists(self.homologador_path):
            self.errors.append(
                f"Archivo de homologador no encontrado: {self.homologador_path}"
            )
            logger.error("Homologador Previsora no encontrado: %s", self.homologador_path)
            return False
        try:
            df = pd.read_excel(self.homologador_path)
            df.columns = [str(c).strip() for c in df.columns]
            self.homologador_df = df
            self._dict_cache = None
            logger.info("Homologador Previsora cargado: %s registros", len(df))
            return True
        except Exception as e:
            self.errors.append(f"Error al cargar homologador: {str(e)}")
            logger.error("Error cargando homologador Previsora: %s", e)
            return False

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
        """{codigo_previsora: codigo_dgh}; vacío si no hay homologador."""
        if self.homologador_df is None:
            return {}
        prev_col = self._find_homolog_column(
            keywords=["codigo", "previsora"], exact_match=HOMOLOGADOR_PREV_COL
        )
        homo_col = self._find_homolog_column(
            keywords=["codigo", "homologo"], exact_match=HOMOLOGADOR_HOMO_COL
        )
        if prev_col is None or homo_col is None:
            prev_col = self._find_homolog_column(
                keywords=["codigo", "servicio", "erp"], exact_match=HOMOLOGADOR_ERP_COL
            )
            homo_col = self._find_homolog_column(
                keywords=["codigo", "dgh"], exact_match=HOMOLOGADOR_DGH_COL
            )
        if prev_col is None or homo_col is None:
            self.warnings.append(
                "Homologador Previsora sin columnas esperadas; se conserva original"
            )
            return {}
        homolog_dict: dict[str, str] = {}
        for _, row in self.homologador_df.iterrows():
            codigo_prev = self._normalize_code(row[prev_col])
            codigo_dgh = self._normalize_code(row[homo_col])
            if not codigo_prev or codigo_prev in ("NAN", "NONE", ""):
                continue
            if not codigo_dgh or codigo_dgh in ("0", "NAN", "NONE", ""):
                continue
            homolog_dict[codigo_prev] = codigo_dgh
        return homolog_dict

    def homologar_codigo_servicio(self, codigo: Any) -> str:
        """Homologa un código o retorna '' si no hay match / homologador."""
        original = self._normalize_code(codigo)
        if not original:
            return ""
        if self._dict_cache is None:
            self._dict_cache = self._build_homologation_dict()
        return self._dict_cache.get(original, "")

    # ==================== TEMPLATE METHOD ====================

    def identify_files(self, file_paths: list[str]) -> list[str]:
        """Retorna TODOS los .pdf (Previsora envía PDF, no xlsx)."""
        paths = list(file_paths or [])
        pdfs = [f for f in paths if str(f).lower().endswith(".pdf")]
        ignorados = len(paths) - len(pdfs)
        if ignorados:
            logger.info("Previsora: %s archivos no-pdf ignorados", ignorados)
        logger.info("Previsora: %s pdf identificados", len(pdfs))
        return pdfs

    def validate_files(
        self, identified_files: list[str] | list[dict[str, str]] | dict[str, Any]
    ) -> bool:
        """Valida que cada pdf identificado exista en disco."""
        if isinstance(identified_files, dict):
            paths: list[Any] = list(identified_files.values())
        elif isinstance(identified_files, list):
            paths = []
            for item in identified_files:
                if isinstance(item, dict):
                    found = None
                    for value in item.values():
                        if isinstance(value, str) and value.lower().endswith(".pdf"):
                            found = value
                            break
                    if found is None:
                        self.errors.append(f"Entrada sin ruta PDF válida: {item}")
                        continue
                    paths.append(found)
                else:
                    paths.append(item)
        else:
            self.errors.append("Entradas de archivos no válidas para Previsora")
            return False

        if not paths:
            self.errors.append("No se encontraron archivos pdf de Previsora")
            return False

        ok = True
        for path in paths:
            if not isinstance(path, str) or not os.path.exists(path):
                self.errors.append(f"Archivo Previsora no existe: {path}")
                ok = False
        return ok

    # ==================== PARSEO PDF ====================

    @staticmethod
    def _extraer_texto_pdf(path: str) -> str:
        """Extrae el texto de todas las páginas del PDF."""
        try:
            from pypdf import PdfReader
        except ImportError as e:
            raise RuntimeError(
                "Falta dependencia pypdf (pip install pypdf) para leer PDFs de Previsora"
            ) from e
        reader = PdfReader(path)
        textos = []
        for page in reader.pages:
            try:
                textos.append(page.extract_text() or "")
            except Exception:
                textos.append("")
        return "\n".join(textos)

    @staticmethod
    def _normalizar_espacios(texto: str) -> str:
        return re.sub(r"[ \t\xa0]+", " ", texto or "")

    @staticmethod
    def _normalizar_factura(valor: str) -> str:
        """Normaliza Nro Factura: upper sin espacios/guiones (FC 515083 -> FC515083)."""
        return re.sub(r"[\s\-]+", "", (valor or "").strip().upper())

    @classmethod
    def _seccionar_por_factura(
        cls, texto: str
    ) -> tuple[list[tuple[str, str, str, str]], str]:
        """Divide el texto por cada Nro Factura.

        Retorna (secciones, huerfano): cada sección es (factura, radicado,
        siniestro, bloque_texto); huerfano es el texto antes de la primera
        factura (ítems cuyo encabezado quedó en otra página).
        Acepta variantes de rótulo (Nro/No./N°/NUMERO DE FACTURA) y como
        fallback un FC+dígitos suelto en el texto. Si no hay factura,
        retorna ([], "") (el llamador registra error).
        """
        patron_factura = re.compile(
            r"(?:Nro\.?\s*Factura|No\.?\s*Factura|N[°º]\s*Factura|"
            r"Num(?:ero)?\.?\s*(?:de\s*)?Factura|"
            r"Factura\s*(?:No\.?|Nro\.?|N[°º])?)\s*[:\-]?\s*([A-Z]{0,3}\s*\d[\d\-]*)",
            re.IGNORECASE,
        )
        matches = list(patron_factura.finditer(texto or ""))
        if not matches:
            suelto = re.search(r"\b(FC\s*\d{4,})\b", texto or "", re.IGNORECASE)
            if suelto:
                return [(cls._normalizar_factura(suelto.group(1)), "", "", texto)], ""
            return [], ""
        secciones = []
        for i, m in enumerate(matches):
            factura = cls._normalizar_factura(m.group(1))
            inicio = m.start()
            fin = matches[i + 1].start() if i + 1 < len(matches) else len(texto)
            bloque = texto[inicio:fin]
            rad = re.search(
                r"Nro\.?\s*Radicado\s*([A-Z0-9\/\-]+)", bloque, re.IGNORECASE
            )
            sin = re.search(
                r"Siniestro(?:\s*SISE)?\s*(\d+)", bloque, re.IGNORECASE
            )
            secciones.append(
                (
                    factura,
                    rad.group(1).strip() if rad else "",
                    sin.group(1).strip() if sin else "",
                    bloque,
                )
            )
        huerfano = texto[: matches[0].start()]
        return secciones, huerfano

    HEADER_ITEM_RE = (
        r"Cant(?:idad)?\.?\s*C[óo]d(?:igo)?\.?\s*Procedimiento\s*%\s*"
        r"Cobrado\s*Objeci[óo]n\s*Liquidado"
    )

    # Líneas de encabezado/pie de página que contaminan datos y observaciones.
    COLA_PATTERNS = [
        r"^\s*Nro\s*Radicado",
        r"^\s*Liquidaci[óo]n de reclamaciones",
        r"^\s*Previsora Seguros SOAT.*$",
        r"^\s*No\.?\s*Egreso.*$",
        r"^\s*Amparo\s*$",
        r"^\s*Fecha\s*(Siniestro|Aviso|recepci[oó]n|formalizaci[oó]n|liquidaci[oó]n)",
        r"^\s*Poliza",
        r"^\s*Id\s*(tomador|beneficiario|accidentado|reclamante)",
        r"^\s*Nombre\s*(tomador|beneficiario|accidentado|reclamante)",
        r"^\s*Diagnosticos",
        r"^\s*C[óo]digo ciudad",
        r"^\s*Antes de imprimir",
        r"^\s*En caso de presentarse",
        r"^\s*carterasoat",
        r"^\s*Miguel Angel Valois",
        r"^\s*VICEPRESIDENTE",
        r"^\s*Revis[óo]\s*:",
        r"^\s*Coordinador",
        r"^\s*VTC Valor total",
        r"^\s*\d+\s+Objeci[óo]n\s+\$",
        r"^\s*\d+\s+Pago\s+neto",
    ]

    @classmethod
    def _cortar_cola(cls, texto: str) -> str:
        """Corta encabezados de la siguiente liquidación y pies de página."""
        if not texto:
            return ""
        cortes = []
        for patron in cls.COLA_PATTERNS:
            m = re.search(patron, texto, re.IGNORECASE | re.MULTILINE)
            if m:
                cortes.append(m.start())
        if cortes:
            texto = texto[: min(cortes)]
        lineas = [
            ln
            for ln in texto.splitlines()
            if not re.match(
                r"^\s*(Liquidaci[óo]n de reclamaciones|Previsora Seguros SOAT.*"
                r"|No\.?\s*Egreso.*)\s*$",
                ln,
                re.IGNORECASE,
            )
        ]
        return "\n".join(lineas)

    @classmethod
    def _extraer_campo(
        cls, chunk: str, patrones: list[str], grupo: int = 1, default: str = ""
    ) -> str:
        """Primer match de una lista de patrones tolerantes en un chunk."""
        for patron in patrones:
            m = re.search(patron, chunk, re.IGNORECASE | re.DOTALL)
            if m:
                try:
                    return cls._normalizar_espacios(m.group(grupo)).strip()
                except IndexError:
                    return ""
        return default

    @classmethod
    def _parse_bloque_items(
        cls, bloque: str, factura: str, radicado: str, siniestro: str
    ) -> list[dict[str, Any]]:
        """Parsea los ítems de un bloque (formato real Previsora).

        Cada ítem viene precedido por su línea de encabezado
        "Cant. Código Procedimiento % Cobrado Objecion Liquidado" y los
        valores van desnudos debajo, con "Observación:" después. Si el
        bloque no trae esa estructura pero sí "Cant <n>" adyacente, se usa
        el parser por chunks como fallback.
        """
        partes = re.split(cls.HEADER_ITEM_RE, bloque or "", flags=re.IGNORECASE)
        filas: list[dict[str, Any]] = []
        patron_valores = re.compile(
            r"\s*(\d+)\s+(\S+)\s+(.+?)\s+([\d\.,]+\s*%?)\s+"
            r"\$?\s*([\d\.,]+)\s+\$?\s*([\d\.,]+)\s+\$?\s*([\d\.,]+)\s*\Z",
            re.IGNORECASE | re.DOTALL,
        )
        for parte in partes[1:]:
            parte = cls._cortar_cola(parte)
            obs_split = re.split(
                r"Observaci[óo]n\s*:?", parte, maxsplit=1, flags=re.IGNORECASE
            )
            datos = cls._cortar_cola(obs_split[0])
            obs_raw = obs_split[1] if len(obs_split) > 1 else ""
            observacion = cls._normalizar_espacios(
                cls._cortar_cola(obs_raw)
            ).strip()
            m = patron_valores.match(datos)
            if not m:
                continue
            filas.append(
                {
                    "NRO_FACTURA": factura,
                    "CANT": m.group(1).strip(),
                    "CODIGO": m.group(2).strip(),
                    "PROCEDIMIENTO": cls._normalizar_espacios(m.group(3)).strip(),
                    "PORCENTAJE": cls._normalizar_espacios(m.group(4)).strip(),
                    "COBRADO": m.group(5).strip(),
                    "OBJECION": m.group(6).strip(),
                    "LIQUIDADO": m.group(7).strip(),
                    "OBSERVACION": (
                        observacion if observacion and observacion != ":" else ""
                    ),
                    "NRO_RADICADO": radicado,
                    "SINIESTRO": siniestro,
                }
            )
        if filas:
            return filas
        return cls._parse_bloque_items_adyacente(bloque, factura, radicado, siniestro)

    @classmethod
    def _parse_bloque_items_adyacente(
        cls, bloque: str, factura: str, radicado: str, siniestro: str
    ) -> list[dict[str, Any]]:
        """Fallback: ítems con "Cant <n>" adyacente (un chunk por ítem)."""
        marcas = list(
            re.finditer(r"Cant(?:idad)?\.?\s*\d+", bloque or "", re.IGNORECASE)
        )
        patron_obs = re.compile(
            r"Observaci[óo]n\s*:?\s*(.+?)(?=\s*Cant(?:idad)?\.?\s*\d+|\Z)",
            re.IGNORECASE | re.DOTALL,
        )
        filas: list[dict[str, Any]] = []
        for i, marca in enumerate(marcas):
            fin = marcas[i + 1].start() if i + 1 < len(marcas) else len(bloque)
            chunk = bloque[marca.start():fin]
            cant = cls._extraer_campo(chunk, [r"Cant(?:idad)?\.?\s*(\d+)"])
            codigo = cls._extraer_campo(
                chunk,
                [r"C[óo]digo\s*(\S+)", r"C[óo]d\.?\s*(\S+)", r"Cod(?:igo)?\.?\s*(\S+)"],
            )
            if not codigo:
                continue
            procedimiento = cls._extraer_campo(
                chunk,
                [
                    r"Procedimiento\s*(.+?)\s*(?:%|Cobrado|Valor|Objeci|Objetado|Glosa|Liquidado|Neto|Observaci)",
                    r"Descripci[óo]n\s*(.+?)\s*(?:%|Cobrado|Valor|Objeci|Objetado|Glosa|Liquidado|Neto|Observaci)",
                    r"Servicio\s*(.+?)\s*(?:%|Cobrado|Valor|Objeci|Objetado|Glosa|Liquidado|Neto|Observaci)",
                    r"Concepto\s*(.+?)\s*(?:%|Cobrado|Valor|Objeci|Objetado|Glosa|Liquidado|Neto|Observaci)",
                ],
            )
            porcentaje = cls._extraer_campo(chunk, [r"%\s*([\d\.,]+\s*%?)"])
            cobrado = cls._extraer_campo(
                chunk,
                [r"(?:Valor\s+|Vlr\.?\s+|Vr\.?\s+)?Cobrado\s*\$?\s*([\d\.,]+)"],
            )
            objecion = cls._extraer_campo(
                chunk,
                [r"(?:Valor\s+)?(?:Objeci[óo]n|Objetado|Glosa)\s*\$?\s*([\d\.,]+)"],
            )
            liquidado = cls._extraer_campo(
                chunk,
                [r"(?:Valor\s+)?(?:Liquidado|Neto)\s*\$?\s*([\d\.,]+)"],
            )
            obs_m = patron_obs.search(chunk)
            observacion = cls._normalizar_espacios(obs_m.group(1)).strip() if obs_m else ""
            filas.append(
                {
                    "NRO_FACTURA": factura,
                    "CANT": cant,
                    "CODIGO": codigo,
                    "PROCEDIMIENTO": procedimiento,
                    "PORCENTAJE": porcentaje,
                    "COBRADO": cobrado,
                    "OBJECION": objecion,
                    "LIQUIDADO": liquidado,
                    "OBSERVACION": observacion,
                    "NRO_RADICADO": radicado,
                    "SINIESTRO": siniestro,
                }
            )
        return filas

    def _parse_pdf(self, path: str, debug_dir: str | None = None) -> pd.DataFrame:
        """Extrae las filas de un PDF de liquidación."""
        texto = self._extraer_texto_pdf(path)
        if not texto or not texto.strip():
            self.errors.append(f"PDF sin texto extraíble: {os.path.basename(path)}")
            return pd.DataFrame()
        secciones, huerfano = self._seccionar_por_factura(texto)
        if not secciones:
            self.errors.append(
                f"Sin Nro Factura en {os.path.basename(path)}; se omite el archivo"
            )
            muestra = self._normalizar_espacios(texto)[:400]
            logger.warning("Previsora sin factura en %s; inicio texto: %s",
                           os.path.basename(path), muestra)
            self._guardar_debug(path, texto, debug_dir)
            return pd.DataFrame()
        todas: list[dict[str, Any]] = []
        if huerfano and re.search(
            self.HEADER_ITEM_RE, huerfano, re.IGNORECASE
        ):
            primera = secciones[0]
            huerfanas = self._parse_bloque_items(
                huerfano, primera[0], primera[1], primera[2]
            )
            if huerfanas:
                self.warnings.append(
                    f"Bloque inicial sin encabezado en {os.path.basename(path)}; "
                    f"se asigna a factura {primera[0]}"
                )
                todas.extend(huerfanas)
        for factura, radicado, siniestro, bloque in secciones:
            items = self._parse_bloque_items(bloque, factura, radicado, siniestro)
            if not items:
                self.warnings.append(
                    f"Factura {factura} sin ítems Cant/Código en {os.path.basename(path)}"
                )
                continue
            todas.extend(items)
        if not todas:
            self._guardar_debug(path, texto, debug_dir)
            return pd.DataFrame()
        return pd.DataFrame(todas)

    @staticmethod
    def _guardar_debug(path: str, texto: str, debug_dir: str | None) -> None:
        """Vuelca el texto extraído a PREVISORA_DEBUG_<archivo>.txt.

        Solo para diagnóstico cuando el parseo da cero filas: con ese txt
        se ajusta el parser al formato real sin pedir el PDF.
        """
        if not debug_dir:
            return
        try:
            os.makedirs(debug_dir, exist_ok=True)
            base = os.path.splitext(os.path.basename(path))[0]
            debug_path = os.path.join(debug_dir, f"PREVISORA_DEBUG_{base}.txt")
            with open(debug_path, "w", encoding="utf-8") as f:
                f.write(texto or "")
            logger.warning("Previsora debug guardado: %s", debug_path)
        except Exception as e:
            logger.warning("Previsora no pudo guardar debug: %s", e)

    def extract_data(
        self, identified_files: list[str] | list[dict[str, str]] | dict[str, Any]
    ) -> dict[str, pd.DataFrame]:
        """Extrae y concatena las filas de TODOS los PDFs."""
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
                df = self._parse_pdf(path)
                if df is not None and not df.empty:
                    frames.append(df)
            except Exception as e:
                self.errors.append(f"Error al leer {path}: {str(e)}")
                continue

        if not frames:
            return {}
        combined = pd.concat(frames, ignore_index=True)
        self.previsora_df = combined
        logger.info("Previsora extract: %s filas de %s archivos", len(combined), len(frames))
        return {"previsora": combined}

    # ==================== HOMOLOGATE ====================

    def homologate(self, data: dict[str, pd.DataFrame]) -> pd.DataFrame:
        """Normaliza filas de Previsora y retorna DataFrame (contrato Base).

        Calcula por fila: CRNCXC (FC0000+factura), SLNSERPRO (homologado o
        código original; aún sin tabla se conserva original), CROVALOBJ
        (numérico de OBJECION), CRDOBSERV (OBSERVACION). Conserva las
        columnas del registro para el Excel de entrega.
        """
        df: pd.DataFrame | None = None
        if isinstance(data, dict):
            if isinstance(data.get("previsora"), pd.DataFrame):
                df = data["previsora"]
            else:
                for value in data.values():
                    if isinstance(value, pd.DataFrame):
                        df = value
                        break

        if df is None or df.empty:
            self.errors.append("Faltan datos para homologar (Previsora)")
            return pd.DataFrame()

        work = df.copy()
        work.columns = [str(c).strip() for c in work.columns]
        requeridas = ["NRO_FACTURA", "CANT", "CODIGO", "PROCEDIMIENTO"]
        faltantes = [c for c in requeridas if c not in work.columns]
        if faltantes:
            self.errors.append(f"Faltan columnas {', '.join(faltantes)} (Previsora)")
            return pd.DataFrame()

        work["CRNCXC"] = work["NRO_FACTURA"].apply(self._formatear_crncxc)
        work["_FACTURA"] = work["NRO_FACTURA"]
        if "fecha_correo" not in work.columns:
            work["fecha_correo"] = ""

        sln: list[str] = []
        homologados = 0
        for _, row in work.iterrows():
            original = self._normalize_code(row.get("CODIGO"))
            nuevo = self.homologar_codigo_servicio(row.get("CODIGO"))
            if nuevo:
                sln.append(nuevo)
                homologados += 1
            else:
                sln.append(original)
        work["SLNSERPRO"] = sln
        if self.homologador_df is None:
            self.warnings.append(
                "Sin tabla de homologación de Previsora; SLNSERPRO conserva original"
            )
        logger.info(
            "Previsora homologación: %s filas, %s homologadas",
            len(work),
            homologados,
        )

        col_obj = "OBJECION" if "OBJECION" in work.columns else None
        work["CROVALOBJ"] = (
            work[col_obj].apply(self._obtener_valor_numerico) if col_obj else 0.0
        )
        if "OBSERVACION" in work.columns:
            work["CRDOBSERV"] = work["OBSERVACION"].fillna("")
        else:
            work["CRDOBSERV"] = ""
        return work

    # ==================== SALIDA ====================

    def save_to_excel(self, data: dict[str, pd.DataFrame], output_path: str) -> bool:
        """Guarda el registro Previsora (hoja Registro, sin columnas internas)."""
        try:
            df = data.get("detalle") if isinstance(data, dict) else data
            if df is None or (isinstance(df, pd.DataFrame) and df.empty):
                self.errors.append("Sin datos de detalle para guardar (Previsora)")
                return False
            cols = [c for c in REGISTRO_COLUMNS if c in df.columns]
            export = df[cols].copy() if cols else self._drop_internal_columns(df)
            with pd.ExcelWriter(output_path, engine="openpyxl") as writer:
                export.to_excel(writer, sheet_name="Registro", index=False)
            logger.info("Previsora archivo guardado: %s", output_path)
            return True
        except Exception as e:
            self.errors.append(f"Error al guardar archivo Previsora: {str(e)}")
            return False

    # ==================== FLUJO PRINCIPAL ====================

    def process_glosas(
        self,
        file_paths: list[str],
        output_dir: str | None = None,
        email_date: str | None = None,
        attachment_service: Any = None,
    ) -> tuple[dict[str, pd.DataFrame] | None, str]:
        """Procesa los PDFs de Previsora a Excel de registro.

        Args:
            file_paths: Rutas a los PDFs (uno o varios por correo agrupado).
            output_dir: Directorio de salida (opcional).
            email_date: Fecha de recepción del correo '%Y-%m-%d %H:%M:%S'.
            attachment_service: Metadatos con fecha individual por archivo.

        Returns:
            Tupla (dict {"detalle"}, mensaje). Objeciones aún NO (fase 2).
        """
        self.errors = []
        self.warnings = []
        self._dict_cache = None

        logger.info("PREVISORA procesador glosas: inicio")

        if self.homologador_path:
            logger.info("Previsora cargando homologador")
            if not self.load_homologador():
                self.warnings.append("Se continúa sin homologar (Previsora)")
        else:
            self.warnings.append(
                "Sin archivo de homologación; SLNSERPRO conserva original"
            )

        pdfs = self.identify_files(file_paths or [])
        if not pdfs:
            self.errors.append("No se encontraron archivos pdf de Previsora")
            return None, f"[ERROR] Error: {'; '.join(self.errors)}"

        if not self.validate_files(pdfs):
            return None, f"[ERROR] Error: {'; '.join(self.errors)}"

        frames = []
        archivos_error = 0
        debug_dir = output_dir
        for path in pdfs:
            try:
                df = self._parse_pdf(path, debug_dir=debug_dir)
                if df is None or df.empty:
                    continue
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
            self.errors.append("No se pudo procesar ningún archivo pdf")
            detalle_problema = "; ".join(self.warnings[:3])
            mensaje = f"[ERROR] Error: {'; '.join(self.errors)}"
            if detalle_problema:
                mensaje += f" | Pistas: {detalle_problema}"
            return None, mensaje

        combined = pd.concat(frames, ignore_index=True)
        logger.info("Previsora: %s filas combinadas de %s archivos", len(combined), len(frames))
        if archivos_error:
            logger.warning("Previsora archivos con error: %s", archivos_error)

        detalle = self.homologate({"previsora": combined})
        if detalle is None or detalle.empty:
            return None, f"[ERROR] Error: {'; '.join(self.errors) or 'sin datos homologados'}"

        result_data: dict[str, pd.DataFrame] = {"detalle": detalle}

        if output_dir:
            try:
                os.makedirs(output_dir, exist_ok=True)
            except Exception as exc:
                logger.warning("No se pudo crear directorio Previsora %s: %s", output_dir, exc)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = os.path.join(output_dir, f"PREVISORA_REGISTRO_{timestamp}.xlsx")
            logger.info("Previsora guardando registro")
            if self.save_to_excel({"detalle": detalle}, output_path):
                return result_data, (
                    f"[OK] Procesado exitosamente. Archivos: {os.path.basename(output_path)}"
                )
            return result_data, f"[WARNING] Procesado pero error al guardar: {'; '.join(self.errors)}"

        return result_data, f"[OK] Procesados {len(pdfs)} archivos pdf"
