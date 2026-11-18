"""
Cliente HTTP para la API REST de Glosaap (mercurio - red interna).

Permite consultar métricas, lotes, facturas y registrar telemetría
con manejo seguro de errores (sin bloquear la aplicación en caso de falla de red).
"""
from __future__ import annotations

import getpass
import socket
from typing import Any

import requests

from app.config.settings import (
    APP_VERSION,
    DEFAULT_GLOSAPP_API_KEY,
    DEFAULT_GLOSAPP_API_URL,
    logger,
)


class GlosappApiClient:
    """Cliente para la API REST de Glosapp."""

    def __init__(
        self,
        base_url: str | None = None,
        api_key: str | None = None,
        timeout: tuple[float, float] = (3.5, 12.0),
    ):
        """
        Args:
            base_url: URL base de la API (ej. http://10.10.10.18:8081/glosapp/api/v1).
            api_key: Clave secreta enviada en el encabezado X-API-Key.
            timeout: Tupla (connect_timeout, read_timeout) en segundos.
        """
        raw_url = (base_url or DEFAULT_GLOSAPP_API_URL).strip().rstrip("/")
        self.base_url = raw_url
        self.api_key = (api_key or DEFAULT_GLOSAPP_API_KEY).strip()
        self.timeout = timeout
        self._session = requests.Session()

    def update_credentials(self, base_url: str | None = None, api_key: str | None = None) -> None:
        """Actualiza la URL base o la API Key en caliente."""
        if base_url is not None:
            self.base_url = base_url.strip().rstrip("/")
        if api_key is not None:
            self.api_key = api_key.strip()

    def _headers(self, custom_key: str | None = None) -> dict[str, str]:
        """Construye los encabezados HTTP estándar."""
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        key = custom_key if custom_key is not None else self.api_key
        if key:
            headers["X-API-Key"] = key
        return headers

    # ==================== ESTADO Y CONECTIVIDAD ====================

    def check_health(self, base_url: str | None = None) -> dict[str, Any]:
        """
        Verifica el estado del servicio y la base de datos (sin API key).
        Llama a GET /salud.
        """
        url = (base_url or self.base_url).rstrip("/") + "/salud"
        try:
            resp = self._session.get(url, timeout=(2.5, 4.0))
            if resp.status_code == 200:
                data = resp.json()
                return {"ok": True, "status_code": 200, "data": data, "error": None}
            return {
                "ok": False,
                "status_code": resp.status_code,
                "data": None,
                "error": f"Servidor respondió con código {resp.status_code}",
            }
        except requests.exceptions.RequestException as ex:
            return {"ok": False, "status_code": 0, "data": None, "error": str(ex)}

    def validate_key(
        self, api_key: str | None = None, base_url: str | None = None
    ) -> dict[str, Any]:
        """
        Valida si la API Key es aceptada consultando GET /eps.
        """
        target_url = (base_url or self.base_url).rstrip("/") + "/eps"
        headers = self._headers(custom_key=api_key)
        try:
            resp = self._session.get(target_url, headers=headers, timeout=(3.0, 5.0))
            if resp.status_code == 200:
                return {"valid": True, "status_code": 200, "message": "Conexión exitosa"}
            elif resp.status_code == 401:
                return {"valid": False, "status_code": 401, "message": "API Key inválida o no autorizada"}
            else:
                detail = resp.json().get("detail", "") if resp.headers.get("content-type", "").startswith("application/json") else ""
                msg = f"Error {resp.status_code}: {detail}" if detail else f"Error {resp.status_code}"
                return {"valid": False, "status_code": resp.status_code, "message": msg}
        except requests.exceptions.RequestException as ex:
            return {"valid": False, "status_code": 0, "message": f"No se pudo conectar: {ex}"}

    # ==================== CONSULTAS (GET) ====================

    def get_eps(self, activo: bool | None = True) -> list[dict[str, Any]]:
        """Obtiene la lista de EPS registradas."""
        url = f"{self.base_url}/eps"
        params = {}
        if activo is not None:
            params["activo"] = "true" if activo else "false"
        try:
            resp = self._session.get(url, headers=self._headers(), params=params, timeout=self.timeout)
            if resp.status_code == 200:
                return resp.json()
            logger.warning("GET /eps falló con código %s: %s", resp.status_code, resp.text)
            return []
        except requests.exceptions.RequestException as ex:
            logger.debug("Error de red al consultar GET /eps: %s", ex)
            return []

    def get_lotes(
        self,
        limit: int = 100,
        offset: int = 0,
        desde: str | None = None,
        hasta: str | None = None,
        id_eps: int | None = None,
        codigo_eps: str | None = None,
    ) -> dict[str, Any]:
        """
        Obtiene lista paginada de lotes de glosas.
        Retorna dict con total, limit, offset e items.
        """
        url = f"{self.base_url}/lotes"
        params: dict[str, Any] = {"limit": limit, "offset": offset}
        if desde:
            params["desde"] = desde
        if hasta:
            params["hasta"] = hasta
        if id_eps is not None:
            params["id_eps"] = id_eps
        if codigo_eps:
            params["codigo_eps"] = codigo_eps

        try:
            resp = self._session.get(url, headers=self._headers(), params=params, timeout=self.timeout)
            if resp.status_code == 200:
                return resp.json()
            logger.warning("GET /lotes falló con código %s: %s", resp.status_code, resp.text)
            return {"total": 0, "limit": limit, "offset": offset, "items": []}
        except requests.exceptions.RequestException as ex:
            logger.debug("Error de red al consultar GET /lotes: %s", ex)
            return {"total": 0, "limit": limit, "offset": offset, "items": []}

    def get_lote_por_id(
        self, id_lote: int, incluir_facturas: bool = True, incluir_detalles: bool = False
    ) -> dict[str, Any] | None:
        """Obtiene un lote específico por ID con sus facturas opcionales."""
        url = f"{self.base_url}/lotes/{id_lote}"
        params = {
            "incluir_facturas": "true" if incluir_facturas else "false",
            "incluir_detalles": "true" if incluir_detalles else "false",
        }
        try:
            resp = self._session.get(url, headers=self._headers(), params=params, timeout=self.timeout)
            if resp.status_code == 200:
                return resp.json()
            return None
        except requests.exceptions.RequestException as ex:
            logger.debug("Error de red al consultar GET /lotes/%s: %s", id_lote, ex)
            return None

    def get_facturas(
        self,
        id_lote: int | None = None,
        id_eps: int | None = None,
        numero_factura: str | None = None,
        estado_glosa: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> dict[str, Any]:
        """Obtiene lista paginada de facturas."""
        url = f"{self.base_url}/facturas"
        params: dict[str, Any] = {"limit": limit, "offset": offset}
        if id_lote is not None:
            params["id_lote"] = id_lote
        if id_eps is not None:
            params["id_eps"] = id_eps
        if numero_factura:
            params["numero_factura"] = numero_factura
        if estado_glosa:
            params["estado_glosa"] = estado_glosa

        try:
            resp = self._session.get(url, headers=self._headers(), params=params, timeout=self.timeout)
            if resp.status_code == 200:
                return resp.json()
            return {"total": 0, "limit": limit, "offset": offset, "items": []}
        except requests.exceptions.RequestException as ex:
            logger.debug("Error de red al consultar GET /facturas: %s", ex)
            return {"total": 0, "limit": limit, "offset": offset, "items": []}

    def get_metricas_resumen(
        self, modulo: str | None = None, desde: str | None = None, hasta: str | None = None
    ) -> list[dict[str, Any]]:
        """Obtiene el resumen de rendimiento técnico por módulo y fase."""
        url = f"{self.base_url}/metricas/resumen"
        params: dict[str, Any] = {}
        if modulo:
            params["modulo"] = modulo
        if desde:
            params["desde"] = desde
        if hasta:
            params["hasta"] = hasta

        try:
            resp = self._session.get(url, headers=self._headers(), params=params, timeout=self.timeout)
            if resp.status_code == 200:
                return resp.json()
            return []
        except requests.exceptions.RequestException as ex:
            logger.debug("Error de red al consultar GET /metricas/resumen: %s", ex)
            return []

    # ==================== INGESTA / ESCRITURA (POST) ====================

    def registrar_lote_completo(self, lote_completo: dict[str, Any]) -> dict[str, Any]:
        """
        Registra lote con sus facturas y detalles en una sola transacción.
        Retorna dict con success, data y error.
        """
        url = f"{self.base_url}/lotes/completo"
        # Asegurar usuario y equipo si vienen vacíos
        if "usuario_responsable" not in lote_completo or not lote_completo["usuario_responsable"]:
            lote_completo["usuario_responsable"] = getpass.getuser()
        if "nombre_equipo" not in lote_completo or not lote_completo["nombre_equipo"]:
            lote_completo["nombre_equipo"] = socket.gethostname()

        try:
            resp = self._session.post(url, headers=self._headers(), json=lote_completo, timeout=(5.0, 30.0))
            if resp.status_code in (200, 201):
                return {"success": True, "data": resp.json(), "error": None}
            detail = resp.text
            try:
                detail = resp.json().get("detail", detail)
            except Exception:
                pass
            return {"success": False, "data": None, "error": f"Error {resp.status_code}: {detail}"}
        except requests.exceptions.RequestException as ex:
            return {"success": False, "data": None, "error": str(ex)}

    def registrar_metricas(self, metricas: list[dict[str, Any]]) -> dict[str, Any]:
        """Registra una lista de métricas de telemetría."""
        if not metricas:
            return {"success": True, "insertados": 0, "error": None}
        url = f"{self.base_url}/metricas"
        try:
            resp = self._session.post(url, headers=self._headers(), json=metricas, timeout=(3.0, 10.0))
            if resp.status_code in (200, 201):
                return {"success": True, "data": resp.json(), "error": None}
            return {"success": False, "error": f"HTTP {resp.status_code}"}
        except requests.exceptions.RequestException as ex:
            return {"success": False, "error": str(ex)}

    def registrar_log(
        self,
        nivel: str,
        modulo_origen: str,
        mensaje: str,
        detalle_error: str | None = None,
        id_sesion: int | None = None,
    ) -> bool:
        """Registra un evento de log técnico."""
        url = f"{self.base_url}/logs"
        payload = {
            "nivel": nivel.upper(),
            "modulo_origen": modulo_origen,
            "mensaje": mensaje,
            "detalle_error": detalle_error,
        }
        if id_sesion is not None:
            payload["id_sesion"] = id_sesion
        try:
            resp = self._session.post(url, headers=self._headers(), json=[payload], timeout=(2.0, 5.0))
            return resp.status_code in (200, 201)
        except Exception:
            return False

    def abrir_sesion(
        self,
        usuario: str | None = None,
        nombre_equipo: str | None = None,
        version_app: str | None = None,
    ) -> int | None:
        """Registra la apertura de sesión de Glosaap."""
        url = f"{self.base_url}/sesiones"
        payload = {
            "usuario": usuario or getpass.getuser(),
            "nombre_equipo": nombre_equipo or socket.gethostname(),
            "version_app": version_app or APP_VERSION,
        }
        try:
            resp = self._session.post(url, headers=self._headers(), json=payload, timeout=(3.0, 5.0))
            if resp.status_code in (200, 201):
                return resp.json().get("id_sesion")
            return None
        except Exception:
            return None

    def cerrar_sesion(self, id_sesion: int) -> bool:
        """Registra el cierre de la sesión de Glosaap."""
        url = f"{self.base_url}/sesiones/{id_sesion}/cerrar"
        try:
            resp = self._session.post(url, headers=self._headers(), json={}, timeout=(2.0, 4.0))
            return resp.status_code == 200
        except Exception:
            return False


# Instancia singleton predeterminada
api_client = GlosappApiClient()
