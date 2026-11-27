"""
Proveedor de consulta de solo lectura contra SQL Server (Dinámica Gerencial - DGH)
para el módulo de Informe de Glosas.

Las credenciales se obtienen en orden de prioridad:
1. Parámetros explícitos de instancia/llamada.
2. Almacén seguro local (CredentialManager / Windows Keyring-DPAPI).
3. Variables de entorno (GLOSA_SQL_SERVER, GLOSA_SQL_DATABASE, GLOSA_SQL_USER, GLOSA_SQL_PASSWORD).
4. Valores no secretos por defecto en settings.py.
"""
from __future__ import annotations

import os
from datetime import date, datetime, timedelta
from typing import Any

from app.config.settings import (
    DEFAULT_DGH_SQL_DATABASE,
    DEFAULT_DGH_SQL_SERVER,
    DEFAULT_DGH_SQL_USER,
    logger,
)
from app.core.date_utils import parse_email_date
from app.service.credential_manager import CredentialManager

try:
    import pyodbc
except ImportError:  # pragma: no cover
    pyodbc = None  # type: ignore[assignment]


DGH_SQL_SERVICE_KEY = "dgh_sql"

DGH_GLOSAS_COLUMN_MAPPING: dict[str, str] = {
    "id_glosa": "NumeroGlosaInterno",
    "fecha_glosa": "FechaGlosa",
    "numero_factura": "NumeroFactura",
    "entidad_eps": "Entidad",
    "codigo_glosa": "CodigoMotivoGlosa",
    "concepto_glosa": "ConceptoGlosa",
    "valor_facturado": "ValorFacturado",
    "valor_glosado": "ValorGlosado",
    "estado_glosa": "EstadoGlosa",
    "servicio_glosado": "ServicioGlosado",
    "centro_costo": "NombreCentroCosto",
    "observacion_general": "ObservacionGeneral",
}

DGH_GLOSAS_BASE_SQL = """
SELECT
    doc.CDCONSEC            AS NumeroGlosaInterno,
    rec.CROFECOBJ           AS FechaGlosa,
    cxc.CXCDOCUME           AS NumeroFactura,
    COALESCE(gco.GECNOMENT, gde.GDENOMBRE, 'SIN ENTIDAD') AS Entidad,
    con.CCOCODIGO           AS CodigoMotivoGlosa,
    con.CCONOMBRE           AS MotivoGlosa,
    det.CRDOBSERV           AS ObservacionDetalle,
    rec.CROOBSERV           AS ObservacionGeneral,
    cxc.CRNVALOR            AS ValorFacturado,
    det.CROVALOBJ           AS ValorGlosado,
    ser.SERDESSER           AS ServicioGlosado,
    cc.CCNOMBRE             AS NombreCentroCosto,
    'CONFIRMADA'            AS EstadoGlosa
FROM CRNRECOBJC rec WITH (NOLOCK)
INNER JOIN CRNDOCUME doc WITH (NOLOCK)   ON doc.OID = rec.OID
INNER JOIN CRNRECOBJD det WITH (NOLOCK)  ON det.CRNRECOBJC = rec.OID
INNER JOIN CRNCONOBJ con WITH (NOLOCK)   ON con.OID = det.CRNCONOBJ
INNER JOIN CRNCXC cxc WITH (NOLOCK)      ON cxc.OID = rec.CRNCXC
LEFT JOIN  GENDETCON gde WITH (NOLOCK)   ON gde.OID = cxc.GENDETCON
LEFT JOIN  GENCONTRA gco WITH (NOLOCK)   ON gco.OID = gde.GENCONTRA1
LEFT JOIN  SLNSERPRO ser WITH (NOLOCK)   ON ser.OID = det.SLNSERPRO
LEFT JOIN  CTNCENCOS cc WITH (NOLOCK)    ON cc.OID = COALESCE(det.CTNCENCOS, ser.CTCENCOS1)
WHERE doc.CDTIPDOC = 1
  AND rec.CROESTADO = 1
  AND con.CCOTIPCON = 0
  AND rec.CROFECOBJ >= ?
  AND rec.CROFECOBJ < ?
"""


def _parse_date_arg(value: Any) -> date:
    """Convierte fecha string o date/datetime a datetime.date para evitar error 242 de DATEFORMAT."""
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    txt = str(value or "").strip()
    if txt:
        try:
            return date.fromisoformat(txt[:10])
        except ValueError:
            pass
        for fmt in ("%d/%m/%Y", "%Y/%m/%d", "%d-%m-%Y"):
            try:
                return datetime.strptime(txt[:10], fmt).date()
            except ValueError:
                continue
        parsed = parse_email_date(txt)
        if parsed is not None:
            return parsed.date()
    raise ValueError(f"Fecha invalida para consulta SQL: {value!r}")


def _clean_text(value: Any) -> str:
    """Normaliza espacios y saltos de línea en campos descriptivos SQL."""
    if value is None:
        return ""
    return " ".join(str(value).replace("\r", " ").replace("\n", " ").split())


class DghSqlGlosasProvider:
    """Proveedor SQL Server de solo lectura para consultar glosas por rango de fechas."""

    def __init__(
        self,
        credential_manager: CredentialManager | None = None,
        server: str | None = None,
        database: str | None = None,
        username: str | None = None,
        password: str | None = None,
        timeout: int = 12,
    ):
        self._cred_manager = credential_manager
        self._explicit_server = server
        self._explicit_database = database
        self._explicit_username = username
        self._explicit_password = password
        self.timeout = int(timeout)

    def _get_cred_manager(self) -> CredentialManager | None:
        """Obtiene el CredentialManager de forma perezosa (evita I/O al importar)."""
        if self._cred_manager is None:
            try:
                self._cred_manager = CredentialManager()
            except Exception as ex:
                logger.debug("No se pudo inicializar CredentialManager: %s", ex)
                return None
        return self._cred_manager

    def get_config(self, include_password: bool = False) -> dict[str, Any]:
        """Retorna la configuración efectiva combinando parámetros, keyring y entorno."""
        stored: dict[str, Any] = {}
        cm = self._get_cred_manager()
        if cm is not None:
            try:
                stored = cm.load_credentials(DGH_SQL_SERVICE_KEY) or {}
            except Exception as ex:
                logger.debug("No se pudieron cargar credenciales SQL guardadas: %s", ex)

        server = (
            self._explicit_server
            or stored.get("server")
            or os.environ.get("GLOSA_SQL_SERVER")
            or DEFAULT_DGH_SQL_SERVER
        )
        database = (
            self._explicit_database
            or stored.get("database")
            or os.environ.get("GLOSA_SQL_DATABASE")
            or DEFAULT_DGH_SQL_DATABASE
        )
        username = (
            self._explicit_username
            or stored.get("username")
            or os.environ.get("GLOSA_SQL_USER")
            or DEFAULT_DGH_SQL_USER
        )
        password = (
            self._explicit_password
            if self._explicit_password is not None
            else (stored.get("password") or os.environ.get("GLOSA_SQL_PASSWORD") or "")
        )

        cfg: dict[str, Any] = {
            "server": str(server or "").strip(),
            "database": str(database or "").strip(),
            "username": str(username or "").strip(),
            "has_password": bool(password),
        }
        if include_password:
            cfg["password"] = str(password)
        return cfg

    def save_config(self, server: str, database: str, username: str, password: str) -> bool:
        """Persiste credenciales en Windows Keyring/DPAPI y actualiza la configuración activa."""
        srv = str(server or "").strip() or DEFAULT_DGH_SQL_SERVER
        db = str(database or "").strip() or DEFAULT_DGH_SQL_DATABASE
        usr = str(username or "").strip() or DEFAULT_DGH_SQL_USER
        pwd = str(password or "")

        if not pwd:
            existing = self.get_config(include_password=True)
            pwd = str(existing.get("password") or "")
        if not pwd:
            raise ValueError("Debe ingresar la contraseña de SQL Server.")

        cm = self._get_cred_manager()
        if cm is None:
            return False

        ok = cm.save_credentials(
            DGH_SQL_SERVICE_KEY,
            usr,
            pwd,
            server=srv,
            database=db,
        )
        if ok:
            self._explicit_server = srv
            self._explicit_database = db
            self._explicit_username = usr
            self._explicit_password = pwd
        return ok

    @staticmethod
    def _pick_odbc_driver() -> str:
        """Selecciona el mejor driver ODBC de SQL Server disponible en el equipo."""
        if pyodbc is None:
            raise RuntimeError("El paquete pyodbc no esta instalado en este entorno.")
        installed = list(pyodbc.drivers())
        preferred = (
            "ODBC Driver 18 for SQL Server",
            "ODBC Driver 17 for SQL Server",
            "ODBC Driver 13 for SQL Server",
            "SQL Server",
        )
        for cand in preferred:
            if cand in installed:
                return cand
        for drv in installed:
            if "sql server" in drv.lower():
                return drv
        raise RuntimeError(
            "No se encontro un driver ODBC para SQL Server instalado en el equipo."
        )

    def build_connection_string(
        self,
        server: str | None = None,
        database: str | None = None,
        username: str | None = None,
        password: str | None = None,
    ) -> str:
        """Construye la cadena de conexión ODBC usando el driver disponible."""
        cfg = self.get_config(include_password=True)
        srv = (server or cfg["server"]).strip()
        db = (database or cfg["database"]).strip()
        usr = (username or cfg["username"]).strip()
        pwd = password if password not in (None, "") else str(cfg.get("password") or "")

        if not pwd:
            raise RuntimeError(
                "No hay contraseña configurada para SQL Server. Usa 'Configurar SQL' para guardarla."
            )

        driver = self._pick_odbc_driver()
        conn_str = (
            f"DRIVER={{{driver}}};"
            f"SERVER={srv};"
            f"DATABASE={db};"
            f"UID={usr};"
            f"PWD={pwd};"
        )
        if "17" in driver or "18" in driver:
            conn_str += "Encrypt=no;TrustServerCertificate=yes;"
        conn_str += f"Connection Timeout={min(self.timeout, 10)};"
        return conn_str

    def test_connection(
        self,
        server: str | None = None,
        database: str | None = None,
        username: str | None = None,
        password: str | None = None,
    ) -> dict[str, Any]:
        """Verifica conectividad y fecha máxima registrada en CRNRECOBJC."""
        if pyodbc is None:
            return {
                "ok": False,
                "message": "pyodbc no esta disponible en este entorno.",
                "database": None,
                "latest_date": None,
            }
        try:
            conn_str = self.build_connection_string(
                server=server,
                database=database,
                username=username,
                password=password,
            )
            conn = pyodbc.connect(conn_str, timeout=min(self.timeout, 10))
            try:
                cur = conn.cursor()
                cur.execute(
                    "SELECT DB_NAME() AS db, MAX(CROFECOBJ) AS max_fecha "
                    "FROM CRNRECOBJC WITH (NOLOCK) WHERE CROESTADO = 1"
                )
                row = cur.fetchone()
                db_name = str(row[0]) if row and row[0] else None
                max_fecha = (
                    row[1].strftime("%Y-%m-%d")
                    if row and isinstance(row[1], (date, datetime))
                    else (str(row[1]) if row and row[1] else None)
                )
                msg = f"Conexion exitosa a {db_name or 'SQL Server'}"
                if max_fecha:
                    msg += f" (ultimo registro: {max_fecha})"
                return {
                    "ok": True,
                    "message": msg,
                    "database": db_name,
                    "latest_date": max_fecha,
                }
            finally:
                conn.close()
        except Exception as ex:
            return {
                "ok": False,
                "message": f"Error de conexion SQL: {ex}",
                "database": None,
                "latest_date": None,
            }

    @staticmethod
    def _resolve_date_params(fecha_desde: str, fecha_hasta: str) -> tuple[date, date, date]:
        """Convierte fechas de entrada en (desde, hasta_inclusivo, hasta_exclusivo)."""
        d_desde = _parse_date_arg(fecha_desde)
        d_hasta = _parse_date_arg(fecha_hasta)
        if d_hasta < d_desde:
            d_desde, d_hasta = d_hasta, d_desde
        return d_desde, d_hasta, d_hasta + timedelta(days=1)

    @staticmethod
    def _normalize_entidad_filter(entidad_filter: str | None) -> str:
        """Retorna el texto de filtro de entidad o cadena vacía si aplica a todas."""
        entidad_clean = str(entidad_filter or "").strip()
        if entidad_clean.upper() in ("", "TODAS", "ALL", "NONE"):
            return ""
        return entidad_clean

    @staticmethod
    def _build_servicios_sql(has_entidad: bool) -> str:
        """Construye la consulta SQL de glosas agrupadas por servicio (SLNSERPRO)."""
        entidad_join = (
            "INNER JOIN CRNCXC cxc WITH (NOLOCK)     ON cxc.OID = rec.CRNCXC\n"
            "LEFT JOIN  GENDETCON gde WITH (NOLOCK)  ON gde.OID = cxc.GENDETCON\n"
            "LEFT JOIN  GENCONTRA gco WITH (NOLOCK)  ON gco.OID = gde.GENCONTRA1\n"
            if has_entidad
            else ""
        )
        entidad_where = (
            "  AND COALESCE(gco.GECNOMENT, gde.GDENOMBRE, 'SIN ENTIDAD') LIKE ?\n"
            if has_entidad
            else ""
        )
        return (
            "SELECT\n"
            "    ISNULL(ser.SERDESSER, 'SIN SERVICIO ASOCIADO') AS ServicioGlosado,\n"
            "    COUNT(det.OID)                                 AS CantidadGlosas,\n"
            "    COUNT(DISTINCT rec.CRNCXC)                     AS FacturasAfectadas,\n"
            "    SUM(det.CROVALOBJ)                             AS TotalValorGlosado\n"
            "FROM CRNRECOBJC rec WITH (NOLOCK)\n"
            "INNER JOIN CRNDOCUME doc WITH (NOLOCK)   ON doc.OID = rec.OID\n"
            "INNER JOIN CRNRECOBJD det WITH (NOLOCK)  ON det.CRNRECOBJC = rec.OID\n"
            "INNER JOIN CRNCONOBJ con WITH (NOLOCK)   ON con.OID = det.CRNCONOBJ\n"
            "LEFT JOIN  SLNSERPRO ser WITH (NOLOCK)   ON ser.OID = det.SLNSERPRO\n"
            f"{entidad_join}"
            "WHERE doc.CDTIPDOC = 1\n"
            "  AND rec.CROESTADO = 1\n"
            "  AND con.CCOTIPCON = 0\n"
            "  AND rec.CROFECOBJ >= ?\n"
            "  AND rec.CROFECOBJ < ?\n"
            f"{entidad_where}"
            "GROUP BY ISNULL(ser.SERDESSER, 'SIN SERVICIO ASOCIADO')\n"
            "ORDER BY TotalValorGlosado DESC"
        )

    @staticmethod
    def _build_facturadores_sql(has_entidad: bool) -> str:
        """Construye la consulta SQL de glosas agrupadas por usuario facturador (SLNFACTUR)."""
        entidad_join = (
            "LEFT JOIN  GENDETCON gde WITH (NOLOCK)  ON gde.OID = cxc.GENDETCON\n"
            "LEFT JOIN  GENCONTRA gco WITH (NOLOCK)  ON gco.OID = gde.GENCONTRA1\n"
            if has_entidad
            else ""
        )
        entidad_where = (
            "  AND COALESCE(gco.GECNOMENT, gde.GDENOMBRE, 'SIN ENTIDAD') LIKE ?\n"
            if has_entidad
            else ""
        )
        return (
            "SELECT\n"
            "    ISNULL(usu.USUNOMBRE, 'SIN USUARIO') AS UsuarioFacturador,\n"
            "    ISNULL(usu.USUDESCRI, 'SIN NOMBRE')  AS NombreFacturador,\n"
            "    COUNT(det.OID)                       AS CantidadItemsGlosados,\n"
            "    COUNT(DISTINCT fac.OID)              AS FacturasGlosadas,\n"
            "    SUM(det.CROVALOBJ)                   AS TotalValorGlosado\n"
            "FROM CRNRECOBJC rec WITH (NOLOCK)\n"
            "INNER JOIN CRNDOCUME doc WITH (NOLOCK)   ON doc.OID = rec.OID\n"
            "INNER JOIN CRNRECOBJD det WITH (NOLOCK)  ON det.CRNRECOBJC = rec.OID\n"
            "INNER JOIN CRNCONOBJ con WITH (NOLOCK)   ON con.OID = det.CRNCONOBJ\n"
            "INNER JOIN CRNCXC cxc WITH (NOLOCK)      ON cxc.OID = rec.CRNCXC\n"
            "INNER JOIN SLNFACTUR fac WITH (NOLOCK)   ON fac.OID = cxc.SLNFACTUR\n"
            "LEFT JOIN  GENUSUARIO usu WITH (NOLOCK)  ON usu.OID = fac.GENUSUARIO1\n"
            f"{entidad_join}"
            "WHERE doc.CDTIPDOC = 1\n"
            "  AND rec.CROESTADO = 1\n"
            "  AND con.CCOTIPCON = 0\n"
            "  AND rec.CROFECOBJ >= ?\n"
            "  AND rec.CROFECOBJ < ?\n"
            f"{entidad_where}"
            "GROUP BY ISNULL(usu.USUNOMBRE, 'SIN USUARIO'), ISNULL(usu.USUDESCRI, 'SIN NOMBRE')\n"
            "ORDER BY TotalValorGlosado DESC"
        )

    @staticmethod
    def _build_conceptos_sql(has_entidad: bool) -> str:
        """Construye la consulta SQL de conceptos de objeción con clase (CRNCONOBJ)."""
        entidad_join = (
            "INNER JOIN CRNCXC cxc WITH (NOLOCK)     ON cxc.OID = rec.CRNCXC\n"
            "LEFT JOIN  GENDETCON gde WITH (NOLOCK)  ON gde.OID = cxc.GENDETCON\n"
            "LEFT JOIN  GENCONTRA gco WITH (NOLOCK)  ON gco.OID = gde.GENCONTRA1\n"
            if has_entidad
            else ""
        )
        entidad_where = (
            "  AND COALESCE(gco.GECNOMENT, gde.GDENOMBRE, 'SIN ENTIDAD') LIKE ?\n"
            if has_entidad
            else ""
        )
        return (
            "SELECT\n"
            "    con.CCOCODIGO AS CodigoConcepto,\n"
            "    con.CCONOMBRE AS NombreConcepto,\n"
            "    CASE con.CCOCLACON\n"
            "        WHEN 1 THEN 'Administrativo'\n"
            "        WHEN 2 THEN 'Asistencial'\n"
            "        ELSE 'Ninguno'\n"
            "    END AS ClaseObjecion,\n"
            "    COUNT(det.OID)             AS CantidadGlosas,\n"
            "    COUNT(DISTINCT rec.CRNCXC) AS FacturasAfectadas,\n"
            "    SUM(det.CROVALOBJ)         AS TotalValorGlosado\n"
            "FROM CRNRECOBJC rec WITH (NOLOCK)\n"
            "INNER JOIN CRNDOCUME doc WITH (NOLOCK)   ON doc.OID = rec.OID\n"
            "INNER JOIN CRNRECOBJD det WITH (NOLOCK)  ON det.CRNRECOBJC = rec.OID\n"
            "INNER JOIN CRNCONOBJ con WITH (NOLOCK)   ON con.OID = det.CRNCONOBJ\n"
            f"{entidad_join}"
            "WHERE doc.CDTIPDOC = 1\n"
            "  AND rec.CROESTADO = 1\n"
            "  AND con.CCOTIPCON = 0\n"
            "  AND rec.CROFECOBJ >= ?\n"
            "  AND rec.CROFECOBJ < ?\n"
            f"{entidad_where}"
            "GROUP BY con.CCOCODIGO, con.CCONOMBRE, con.CCOCLACON\n"
            "ORDER BY TotalValorGlosado DESC"
        )

    def fetch_records(
        self,
        fecha_desde: str,
        fecha_hasta: str,
        entidad_filter: str | None = None,
    ) -> list[dict[str, Any]]:
        """Consulta las glosas en SQL Server filtrando por rango inclusivo de fechas."""
        if pyodbc is None:
            raise RuntimeError("El paquete pyodbc no esta instalado.")

        d_desde, d_hasta, hasta_excl = self._resolve_date_params(fecha_desde, fecha_hasta)

        sql = DGH_GLOSAS_BASE_SQL
        params: list[Any] = [d_desde, hasta_excl]

        entidad_clean = self._normalize_entidad_filter(entidad_filter)
        if entidad_clean:
            sql += "  AND COALESCE(gco.GECNOMENT, gde.GDENOMBRE, 'SIN ENTIDAD') LIKE ?\n"
            params.append(f"%{entidad_clean}%")

        sql += "ORDER BY rec.CROFECOBJ DESC"

        conn_str = self.build_connection_string()
        conn = pyodbc.connect(conn_str, timeout=min(self.timeout, 10))
        try:
            cur = conn.cursor()
            cur.execute(sql, params)
            cols = [desc[0] for desc in cur.description]
            col_idx = {name: i for i, name in enumerate(cols)}

            records: list[dict[str, Any]] = []
            for row in cur.fetchall():
                motivo = _clean_text(row[col_idx["MotivoGlosa"]])
                obs_det = _clean_text(row[col_idx["ObservacionDetalle"]])
                obs_gen = _clean_text(row[col_idx["ObservacionGeneral"]])
                if obs_det and motivo and obs_det.lower() != motivo.lower():
                    concepto = f"{motivo} - {obs_det}"
                else:
                    concepto = obs_det or motivo or obs_gen

                records.append(
                    {
                        "NumeroGlosaInterno": row[col_idx["NumeroGlosaInterno"]],
                        "FechaGlosa": row[col_idx["FechaGlosa"]],
                        "NumeroFactura": row[col_idx["NumeroFactura"]],
                        "Entidad": _clean_text(row[col_idx["Entidad"]]) or "SIN ENTIDAD",
                        "CodigoMotivoGlosa": _clean_text(row[col_idx["CodigoMotivoGlosa"]]),
                        "ConceptoGlosa": concepto,
                        "ObservacionGeneral": obs_gen,
                        "ValorFacturado": row[col_idx["ValorFacturado"]],
                        "ValorGlosado": row[col_idx["ValorGlosado"]],
                        "ServicioGlosado": _clean_text(row[col_idx["ServicioGlosado"]]),
                        "NombreCentroCosto": _clean_text(row[col_idx["NombreCentroCosto"]]),
                        "EstadoGlosa": _clean_text(row[col_idx["EstadoGlosa"]]) or "CONFIRMADA",
                    }
                )
            logger.info(
                "DGH SQL consulta %s..%s -> %s registros",
                d_desde.isoformat(),
                d_hasta.isoformat(),
                len(records),
            )
            return records
        finally:
            conn.close()

    def fetch_breakdowns(
        self,
        fecha_desde: str,
        fecha_hasta: str,
        entidad_filter: str | None = None,
    ) -> dict[str, list[dict[str, Any]]]:
        """Ejecuta las 3 consultas independientes (servicios, facturadores y conceptos)."""
        if pyodbc is None:
            raise RuntimeError("El paquete pyodbc no esta instalado.")

        d_desde, d_hasta, hasta_excl = self._resolve_date_params(fecha_desde, fecha_hasta)
        entidad_clean = self._normalize_entidad_filter(entidad_filter)
        has_entidad = bool(entidad_clean)
        params: list[Any] = [d_desde, hasta_excl]
        if has_entidad:
            params.append(f"%{entidad_clean}%")

        conn_str = self.build_connection_string()
        conn = pyodbc.connect(conn_str, timeout=min(self.timeout, 10))
        try:
            cur = conn.cursor()

            # 1. Glosas por servicio
            cur.execute(self._build_servicios_sql(has_entidad), params)
            por_servicio = [
                {
                    "servicio_glosado": _clean_text(r[0]) or "SIN SERVICIO ASOCIADO",
                    "cantidad_glosas": int(r[1] or 0),
                    "facturas_afectadas": int(r[2] or 0),
                    "total_valor_glosado": r[3] or 0,
                }
                for r in cur.fetchall()
            ]

            # 2. Glosas por facturador
            cur.execute(self._build_facturadores_sql(has_entidad), params)
            por_facturador = [
                {
                    "usuario_facturador": _clean_text(r[0]) or "SIN USUARIO",
                    "nombre_facturador": _clean_text(r[1]) or "SIN NOMBRE",
                    "cantidad_items_glosados": int(r[2] or 0),
                    "facturas_glosadas": int(r[3] or 0),
                    "total_valor_glosado": r[4] or 0,
                }
                for r in cur.fetchall()
            ]

            # 3. Top conceptos de objeción
            cur.execute(self._build_conceptos_sql(has_entidad), params)
            top_conceptos = [
                {
                    "codigo_concepto": _clean_text(r[0]),
                    "nombre_concepto": _clean_text(r[1]),
                    "clase_objecion": _clean_text(r[2]) or "Ninguno",
                    "cantidad_glosas": int(r[3] or 0),
                    "facturas_afectadas": int(r[4] or 0),
                    "total_valor_glosado": r[5] or 0,
                }
                for r in cur.fetchall()
            ]

            logger.info(
                "DGH SQL desgloses %s..%s -> servicios=%s facturadores=%s conceptos=%s",
                d_desde.isoformat(),
                d_hasta.isoformat(),
                len(por_servicio),
                len(por_facturador),
                len(top_conceptos),
            )
            return {
                "por_servicio": por_servicio,
                "por_facturador": por_facturador,
                "top_conceptos": top_conceptos,
            }
        finally:
            conn.close()

    def __call__(
        self,
        fecha_desde: str,
        fecha_hasta: str,
        entidad_filter: str | None = None,
    ) -> list[dict[str, Any]]:
        """Permite registrar la instancia directamente en ExternalGlosasReportService."""
        return self.fetch_records(
            fecha_desde=fecha_desde,
            fecha_hasta=fecha_hasta,
            entidad_filter=entidad_filter,
        )
