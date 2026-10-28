"""Gestor simple de credenciales (sin secretos en disco).

Password en keyring (DPAPI en Windows) o token Fernet con clave en
keyring. En fichero solo username + backend + extras. Los formatos
legacy en plano ya NO se leen: requieren guardar de nuevo.
"""
import json
import os
import sys
from datetime import UTC, datetime

from app.config.settings import logger
from app.core.secure_store import (
    _chmod_600,
    atomic_write_json,
    keyring_delete,
    read_json_locked,
    retrieve_secret,
    store_secret,
)

KEYRING_SERVICE = "Glosaap"


class CredentialManager:
    """Gestor de credenciales guardadas localmente"""

    def __init__(self, config_dir: str | None = None):
        if config_dir is None:
            # Usar AppData en Windows para persistencia (funciona en exe y desarrollo)
            if sys.platform == 'win32':
                appdata = os.getenv('APPDATA')
                if appdata is None:
                    # Fallback si APPDATA no está definido
                    appdata = os.path.expanduser('~')
                config_dir = os.path.join(appdata, 'Glosaap', 'config')
            else:
                # En desarrollo o Linux/Mac, usar carpeta temp del proyecto
                config_dir = os.path.join(
                    os.path.dirname(__file__), "..", "..", "temp", "config"
                )

        self.config_dir = os.path.abspath(config_dir)
        os.makedirs(self.config_dir, exist_ok=True)
        self.credentials_file = os.path.join(self.config_dir, "credentials.json")
        # Endurecer permisos si el fichero ya existe.
        if os.path.exists(self.credentials_file):
            _chmod_600(self.credentials_file)

    def _keyring_user(self, service: str, username: str) -> str:
        return f"credentials/{service}/{username}"

    def _read_all(self) -> dict:
        if not os.path.exists(self.credentials_file):
            return {}
        try:
            data = read_json_locked(self.credentials_file)
            if not isinstance(data, dict):
                logger.warning("credentials.json con formato inesperado")
                return {}
            return data
        except json.JSONDecodeError as e:
            logger.warning("credentials.json corrupto (JSON invalido): %s", e)
            # Preservar copia para diagnostico.
            try:
                bak = self.credentials_file + ".bak"
                with open(self.credentials_file, encoding="utf-8") as src:
                    content = src.read()
                with open(bak, "w", encoding="utf-8") as dst:
                    dst.write(content)
                _chmod_600(bak)
                logger.info("Copia de credentials corrupto en %s", bak)
            except Exception as exc:
                logger.warning("No se pudo respaldar credentials corrupto: %s", exc)
            return {}
        except FileNotFoundError:
            return {}

    def save_credentials(self, service: str, username: str, password: str, **extra_fields) -> bool:
        """
        Guarda credenciales para un servicio (sin secreto en disco).

        Args:
            service: Nombre del servicio (ej: "fomag", "familiar")
            username: Usuario
            password: Contraseña (keyring o Fernet, nunca plano en fichero)
            **extra_fields: Campos adicionales (ej: nit="123456")

        Returns:
            True si se guardó correctamente
        """
        try:
            # Evitar que extras pisen campos reservados o filtren secreto.
            reserved = {"username", "password", "backend", "token", "updated_at", "version"}
            extras = {k: v for k, v in extra_fields.items() if k not in reserved}
            if any(k in reserved for k in extra_fields):
                logger.warning("Campos reservados ignorados en extras para %s", service)

            credentials = self._read_all()

            key_user = self._keyring_user(service, username)
            # Si cambia el username, limpiar secreto anterior del mismo servicio.
            old = credentials.get(service)
            if isinstance(old, dict) and old.get("username") not in (None, username):
                old_user = self._keyring_user(service, old.get("username", ""))
                try:
                    keyring_delete(old_user, KEYRING_SERVICE)
                except Exception as exc:
                    logger.warning("No se pudo limpiar secreto anterior: %s", exc)

            try:
                backend, token = store_secret(key_user, password, KEYRING_SERVICE)
            except ValueError as exc:
                logger.error("No se pudo custodiar password para %s: %s", service, exc)
                return False

            entry = {
                "username": username,
                "backend": backend,
                "updated_at": datetime.now(UTC).isoformat(),
                **extras,
            }
            if token is not None:
                entry["token"] = token

            credentials[service] = entry
            atomic_write_json(self.credentials_file, credentials)
            logger.info("Credenciales guardadas para %s (backend=%s)", service, backend)
            return True

        except Exception as e:
            logger.error("Error guardando credenciales: %s", e)
            return False

    def load_credentials(self, service: str) -> dict | None:
        """
        Carga credenciales de un servicio.

        Args:
            service: Nombre del servicio

        Returns:
            dict con username y password, o None si no existe
        """
        try:
            if not os.path.exists(self.credentials_file):
                return None

            try:
                credentials = read_json_locked(self.credentials_file)
            except json.JSONDecodeError as e:
                logger.warning("credentials.json corrupto: %s", e)
                return None
            except FileNotFoundError:
                return None

            if not isinstance(credentials, dict):
                return None
            entry = credentials.get(service)
            if entry is None:
                return None
            if not isinstance(entry, dict):
                return None

            # Formato legacy en plano: ya no se lee (re-guardar requerido).
            if "password" in entry and "backend" not in entry:
                logger.warning(
                    "Credenciales de '%s' en formato legacy plano; se ignoran. "
                    "Vuelva a guardar para migrar.",
                    service,
                )
                return None

            username = entry.get("username", "")
            backend = entry.get("backend", "keyring")
            token = entry.get("token")
            key_user = self._keyring_user(service, username)
            password = retrieve_secret(key_user, backend, token, KEYRING_SERVICE)
            if password is None:
                logger.warning("No se pudo recuperar secreto para %s", service)
                return None

            reserved = {"username", "backend", "token", "updated_at", "version"}
            result = {"username": username, "password": password}
            for k, v in entry.items():
                if k not in reserved and k != "password":
                    result[k] = v
            return result

        except Exception as e:
            logger.error("Error cargando credenciales: %s", e)
            return None

    def delete_credentials(self, service: str) -> bool:
        """
        Elimina credenciales de un servicio (fichero + keyring).

        Args:
            service: Nombre del servicio

        Returns:
            True si se eliminó correctamente
        """
        try:
            if not os.path.exists(self.credentials_file):
                return True

            try:
                credentials = read_json_locked(self.credentials_file)
            except json.JSONDecodeError as e:
                logger.warning("credentials.json corrupto al eliminar: %s", e)
                return False
            except FileNotFoundError:
                return True

            if not isinstance(credentials, dict):
                return True

            if service in credentials:
                entry = credentials[service]
                if isinstance(entry, dict) and "username" in entry:
                    try:
                        keyring_delete(
                            self._keyring_user(service, entry.get("username", "")),
                            KEYRING_SERVICE,
                        )
                    except Exception as exc:
                        logger.warning("No se pudo limpiar keyring al eliminar: %s", exc)
                del credentials[service]
                atomic_write_json(self.credentials_file, credentials)
                logger.info("Credenciales eliminadas para %s", service)

            return True

        except Exception as e:
            logger.error("Error eliminando credenciales: %s", e)
            return False
