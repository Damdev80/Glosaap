"""Gestor de sesiones - Guarda y carga credenciales de usuario.

Formato v1 (escritura unica): sin secretos en disco. Password en
keyring (DPAPI en Windows) o token Fernet con clave en keyring.
Compat lectura v0 (base64) por una version.
"""
import base64
import binascii
import json
import os
from datetime import datetime, timezone

from app.config.settings import logger
from app.core.secure_store import (
    atomic_write_json,
    delete_secret,
    fernet_decrypt,
    fernet_encrypt,
    keyring_delete,
    keyring_get,
    keyring_set,
    read_json_locked,
    store_secret,
    retrieve_secret,
    get_lock,
    _chmod_600,
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
            saved = saved.replace(tzinfo=timezone.utc)
        now = datetime.now(timezone.utc)
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
            "saved_at": datetime.now(timezone.utc).isoformat(),
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


def _load_legacy_v0(data: dict):
    """Compat lectura formato viejo base64 (v0). Solo lectura."""
    logger.warning(
        "Sesion en formato legacy v0 (base64); migre guardando de nuevo. "
        "Soporte de lectura se retirara en proxima version."
    )
    try:
        raw = data.get("password", "")
        if not raw:
            return None
        password = base64.b64decode(raw).decode()
        return {
            "email": data.get("email", ""),
            "password": password,
            "server": data.get("server", ""),
        }
    except (binascii.Error, UnicodeDecodeError, ValueError) as e:
        logger.warning("Sesion legacy corrupta (base64 invalido): %s", e)
        return None


def load_session():
    """Carga la sesión guardada.

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
        # Legacy v0: sin "version", con password base64.
        if "password" in data and "version" not in data:
            return _load_legacy_v0(data)
        logger.warning("Archivo de sesion con version desconocida")
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
