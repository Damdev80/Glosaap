"""Gestor de sesiones - Guarda y carga credenciales de usuario.

Formato v1 (escritura unica): sin secretos en disco. Password en
keyring (DPAPI en Windows) o token Fernet con clave en keyring.
Los formatos legacy (v0 base64) ya NO se leen: requieren re-login.
"""
import json
import os
from datetime import UTC, datetime

from app.config.settings import logger
from app.core.secure_store import (
    atomic_write_json,
    get_lock,
    keyring_delete,
    read_json_locked,
    retrieve_secret,
    store_secret,
)

# Ruta del archivo de sesión
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
SESSION_FILE = os.path.join(PROJECT_ROOT, ".session.json")

SESSION_VERSION = 1
SESSION_EXPIRY_DAYS = 30
KEYRING_SERVICE = "Glosaap"


def _session_keyring_user(email: str) -> str:
    return f"session/{email}"


def _is_expired(saved_at_iso: str) -> bool:
    try:
        saved = datetime.fromisoformat(saved_at_iso)
        if saved.tzinfo is None:
            saved = saved.replace(tzinfo=UTC)
        now = datetime.now(UTC)
        return (now - saved).days > SESSION_EXPIRY_DAYS
    except Exception as exc:
        logger.warning("saved_at invalido (%s): %s", saved_at_iso, exc)
        return False


def save_session(email, password, server):
    """Guarda la sesión en un archivo local (formato v1, sin secreto en disco).

    Args:
        email: Correo electrónico
        password: Contraseña (se custodia en keyring o Fernet)
        server: Servidor IMAP
    """
    try:
        username = _session_keyring_user(email)
        try:
            backend, token = store_secret(username, password, KEYRING_SERVICE)
        except ValueError as exc:
            logger.error("No se pudo custodiar password de sesion: %s", exc)
            return
        session_data = {
            "version": SESSION_VERSION,
            "email": email,
            "server": server,
            "saved_at": datetime.now(UTC).isoformat(),
            "backend": backend,
        }
        if token is not None:
            session_data["token"] = token
        atomic_write_json(SESSION_FILE, session_data)
        logger.info("Sesion guardada para %s (backend=%s)", email, backend)
    except Exception as e:
        logger.error("Error guardando sesión: %s", e)


def _load_v1(data: dict):
    email = data.get("email", "")
    server = data.get("server", "")
    backend = data.get("backend", "keyring")
    token = data.get("token")
    saved_at = data.get("saved_at", "")
    if saved_at and _is_expired(saved_at):
        logger.info("Sesion expirada (>%s dias), se ignora", SESSION_EXPIRY_DAYS)
        return None
    username = _session_keyring_user(email)
    password = retrieve_secret(username, backend, token, KEYRING_SERVICE)
    if password is None:
        logger.warning("No se pudo recuperar secreto de sesion para %s", email)
        return None
    return {"email": email, "password": password, "server": server}


def load_session():
    """Carga la sesión guardada.

    Solo formato v1. Archivos legacy o desconocidos se ignoran
    (requieren re-login) y se avisa en el log.

    Returns:
        dict con {email, password, server} o None si no existe/expirada.
    """
    try:
        if not os.path.exists(SESSION_FILE):
            return None
        try:
            data = read_json_locked(SESSION_FILE)
        except json.JSONDecodeError as e:
            logger.warning("Archivo de sesion corrupto (JSON invalido): %s", e)
            return None
        except FileNotFoundError:
            return None
        if not isinstance(data, dict):
            logger.warning("Archivo de sesion con formato inesperado")
            return None
        if data.get("version") == SESSION_VERSION:
            return _load_v1(data)
        logger.warning(
            "Archivo de sesion legacy o desconocido: se ignora, re-inicie sesion"
        )
        return None
    except Exception as e:
        logger.error("Error cargando sesión: %s", e)
        return None


def clear_session():
    """Elimina la sesión guardada (fichero + secreto en keyring)."""
    try:
        email = None
        if os.path.exists(SESSION_FILE):
            try:
                data = read_json_locked(SESSION_FILE)
                if isinstance(data, dict):
                    email = data.get("email")
            except Exception as exc:
                logger.warning("No se pudo leer sesion para limpieza: %s", exc)
        if email:
            try:
                keyring_delete(_session_keyring_user(email), KEYRING_SERVICE)
            except Exception as exc:
                logger.warning("No se pudo limpiar keyring de sesion: %s", exc)
        lock = get_lock(SESSION_FILE)
        with lock:
            if os.path.exists(SESSION_FILE):
                os.remove(SESSION_FILE)
        logger.info("Sesion eliminada")
    except Exception as e:
        logger.error("Error eliminando sesión: %s", e)
