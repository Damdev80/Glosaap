"""Almacen seguro compartido para sesion y credenciales.

Backend primario: ``keyring`` (DPAPI via Windows Credential Manager en
Windows). Fallback: ``cryptography.fernet`` con clave custodiada en
keyring, nunca en disco.

Provee escritura atomica (tmp + replace), FileLock y chmod 600.
"""
import json
import os
import tempfile

try:
    from app.config.settings import logger
except Exception:  # pragma: no cover - fallback si settings no disponible
    import logging
    logger = logging.getLogger("glosaap")

try:
    import keyring
    import keyring.errors as keyring_errors
except Exception:  # pragma: no cover
    keyring = None
    keyring_errors = None

try:
    from cryptography.fernet import Fernet, InvalidToken
except Exception:  # pragma: no cover
    Fernet = None
    InvalidToken = Exception

try:
    from filelock import FileLock
except Exception:  # pragma: no cover
    FileLock = None


KEYRING_SERVICE = "Glosaap"
FERNET_KEY_USERNAME = "fernet-master-key"
LOCK_TIMEOUT = 10

_memory_fernet_key = None


def _chmod_600(path: str) -> None:
    """Aplica permisos 600 donde el SO lo soporta."""
    try:
        os.chmod(path, 0o600)
    except Exception as exc:  # Windows no soporta modo POSIX completo
        logger.debug("No se pudo aplicar chmod 600 a %s: %s", path, exc)


def get_lock(path: str):
    """Retorna un FileLock para *path* (o un no-op si filelock ausente)."""
    lock_path = f"{path}.lock"
    if FileLock is None:  # pragma: no cover
        class _NoOpLock:
            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

        logger.warning("filelock no disponible, sin bloqueo para %s", path)
        return _NoOpLock()
    return FileLock(lock_path, timeout=LOCK_TIMEOUT)


def _get_fernet():
    """Retorna Fernet con clave custodiada en keyring.

    La clave nunca se guarda en disco. En Windows keyring usa DPAPI.
    Si keyring no esta disponible se usa una clave efimera en memoria
    (solo permite roundtrip dentro del mismo proceso).
    """
    global _memory_fernet_key
    if Fernet is None:  # pragma: no cover
        logger.error("cryptography no disponible, sin fallback Fernet")
        return None
    # Intentar clave custodiada en keyring.
    if keyring is not None:
        try:
            stored = keyring.get_password(KEYRING_SERVICE, FERNET_KEY_USERNAME)
            if stored:
                try:
                    return Fernet(stored.encode("utf-8"))
                except Exception as exc:
                    logger.warning("Clave Fernet en keyring invalida: %s", exc)
            # Generar y custodiar nueva clave.
            new_key = Fernet.generate_key().decode("utf-8")
            try:
                keyring.set_password(KEYRING_SERVICE, FERNET_KEY_USERNAME, new_key)
                stored_check = keyring.get_password(KEYRING_SERVICE, FERNET_KEY_USERNAME)
                if stored_check:
                    return Fernet(stored_check.encode("utf-8"))
                return Fernet(new_key.encode("utf-8"))
            except Exception as exc:
                logger.warning("No se pudo custodiar clave Fernet en keyring: %s", exc)
                return Fernet(new_key.encode("utf-8"))
        except Exception as exc:
            logger.warning("keyring no disponible para clave Fernet: %s", exc)
    # Fallback memoria (roundtrip mismo proceso).
    if _memory_fernet_key is None:
        _memory_fernet_key = Fernet.generate_key()
        logger.warning("Usando clave Fernet efimera en memoria (keyring no disponible)")
    return Fernet(_memory_fernet_key)


def keyring_get(username: str, service: str = KEYRING_SERVICE):
    """Lee un secreto desde keyring. Retorna None si no existe o falla."""
    if keyring is None:
        return None
    try:
        return keyring.get_password(service, username)
    except Exception as exc:
        logger.warning("keyring get fallo %s/%s: %s", service, username, exc)
        return None


def keyring_set(username: str, password: str, service: str = KEYRING_SERVICE) -> bool:
    """Guarda un secreto en keyring. Retorna True si ok."""
    if keyring is None:
        return False
    try:
        keyring.set_password(service, username, password)
        return True
    except Exception as exc:
        logger.warning("keyring set fallo %s/%s: %s", service, username, exc)
        return False


def keyring_delete(username: str, service: str = KEYRING_SERVICE) -> bool:
    """Elimina un secreto de keyring. Retorna True (idempotente)."""
    if keyring is None:
        return True
    try:
        try:
            keyring.delete_password(service, username)
        except Exception as exc:
            # PasswordNotFoundError u otros: tratar como ya eliminado.
            logger.debug("keyring delete %s/%s: %s", service, username, exc)
        return True
    except Exception as exc:  # pragma: no cover
        logger.warning("keyring delete fallo %s/%s: %s", service, username, exc)
        return True


def fernet_encrypt(plaintext: str):
    """Cifra con Fernet. Retorna token str o None si falla."""
    try:
        f = _get_fernet()
        if f is None:
            return None
        return f.encrypt(plaintext.encode("utf-8")).decode("utf-8")
    except Exception as exc:
        logger.error("Fernet encrypt fallo: %s", exc)
        return None


def fernet_decrypt(token: str):
    """Descifra token Fernet. Retorna plaintext o None si falla."""
    try:
        f = _get_fernet()
        if f is None or not token:
            return None
        return f.decrypt(token.encode("utf-8")).decode("utf-8")
    except InvalidToken:
        logger.warning("Token Fernet invalido o clave distinta")
        return None
    except Exception as exc:
        logger.warning("Fernet decrypt fallo: %s", exc)
        return None


def store_secret(username: str, password: str, service: str = KEYRING_SERVICE):
    """Guarda secreto: keyring primario, fallback Fernet.

    Returns:
        tuple (backend, token): backend "keyring" con token None,
        o "fernet" con token cifrado. Lanza ValueError si nada funciona.
    """
    if keyring_set(username, password, service):
        # Verificar lectura para no declarar exito falso.
        check = keyring_get(username, service)
        if check == password:
            return ("keyring", None)
        logger.warning("keyring verificacion fallo para %s, usando Fernet", username)
    token = fernet_encrypt(password)
    if token is not None:
        return ("fernet", token)
    raise ValueError("No se pudo almacenar el secreto (keyring y Fernet fallaron)")


def retrieve_secret(username: str, backend: str, token, service: str = KEYRING_SERVICE):
    """Recupera secreto segun backend. Retorna str o None."""
    if backend == "keyring":
        value = keyring_get(username, service)
        if value is not None:
            return value
        # Si hay token acompañante (caso borde), intentar Fernet.
        if token:
            return fernet_decrypt(token)
        return None
    if backend == "fernet":
        if not token:
            return None
        return fernet_decrypt(token)
    logger.warning("Backend desconocido: %s", backend)
    return None


def delete_secret(username: str, service: str = KEYRING_SERVICE) -> bool:
    """Elimina secreto de keyring (idempotente)."""
    return keyring_delete(username, service)


def atomic_write_json(path: str, data: dict) -> None:
    """Escritura atomica tmp+replace con FileLock y chmod 600."""
    parent = os.path.dirname(os.path.abspath(path))
    if parent and not os.path.exists(parent):
        os.makedirs(parent, exist_ok=True)
    lock = get_lock(path)
    with lock:
        fd, tmp_path = tempfile.mkstemp(
            dir=parent or ".", prefix=".tmp_", suffix=".json"
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
                f.flush()
                try:
                    os.fsync(f.fileno())
                except Exception:
                    pass
            _chmod_600(tmp_path)
            os.replace(tmp_path, path)
            _chmod_600(path)
        finally:
            try:
                if os.path.exists(tmp_path):
                    os.remove(tmp_path)
            except Exception:
                pass


def read_json_locked(path: str):
    """Lee JSON bajo FileLock. Lanza FileNotFoundError / JSONDecodeError."""
    lock = get_lock(path)
    with lock:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
