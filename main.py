"""
Punto de entrada principal para Glosaap
Ejecuta la nueva versión modular de la aplicación
"""
import sys
import os

# Agregar el directorio raíz al path para imports
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

# Consola Windows usa cp1252 por defecto y revienta con emojis/acentos
# en prints (UnicodeEncodeError). Fuerza UTF-8 con reemplazo seguro.
try:
    if sys.stdout is not None:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if sys.stderr is not None:
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

# Si no está en el venv, redirigir al venv (mismo patrón que build.py):
# `py main.py` usa el Python del sistema, que no tiene flet ni pandas.
if not hasattr(sys, "real_prefix") and not (
    hasattr(sys, "base_prefix") and sys.base_prefix != sys.prefix
):
    venv_python = os.path.join(ROOT_DIR, ".venv", "Scripts", "python.exe")
    if os.path.exists(venv_python):
        import subprocess

        sys.exit(subprocess.run([venv_python, __file__] + sys.argv[1:]).returncode)

# Importar settings primero (configura Playwright automáticamente)
from app.config.settings import PLAYWRIGHT_BROWSERS_PATH

# Importar y ejecutar la app
from app.ui.app import main
import flet as ft


def _preflight_flet_desktop() -> None:
    """Verifica el viewer Flet antes de arrancar (solo exe congelado).

    Si flet_desktop no está empaquetado, flet intentaría instalarlo con
    `sys.executable -m pip install`, que en el exe RE-EJECUTA Glosaap.exe
    en bucle infinito. Mejor morir limpio con un mensaje visible.
    """
    if not getattr(sys, "frozen", False):
        return
    try:
        import flet.version as _fv
        import flet_desktop.version as _fdv

        assert not _fdv.version or _fdv.version == _fv.version
    except Exception as e:
        msg = f"Falta el visor Flet empaquetado (flet_desktop): {e}"
        try:
            from app.config.settings import logger

            logger.error(msg)
        except Exception:
            pass
        try:
            import ctypes

            ctypes.windll.user32.MessageBoxW(0, msg, "Glosaap - Error", 0x10)
        except Exception:
            pass
        sys.exit(1)


# Nombre del mutex de instancia única (debe coincidir con AppMutex en
# installer/glosaap.iss; tests/test_installer.py lo verifica).
APP_MUTEX_NAME = r"Local\GlosaapAppMutex"

_mutex_handle = None


def _ensure_single_instance() -> None:
    """Evita dos Glosaap corriendo (corrompe descargas/logs y bloquea updates).

    Solo Windows. Crea un mutex nombrado y lo conserva vivo en
    `_mutex_handle` durante todo el proceso. Si ya existe, avisa y sale.
    El instalador usa el mismo nombre (AppMutex) para no instalar encima
    de una app en ejecución.
    """
    global _mutex_handle
    if not sys.platform.startswith("win"):
        return
    try:
        import ctypes

        kernel32 = ctypes.windll.kernel32
        handle = kernel32.CreateMutexW(None, True, APP_MUTEX_NAME)
        if not handle:
            return  # Sin mutex no se puede garantizar; seguir sin bloquear.
        ERROR_ALREADY_EXISTS = 183
        if kernel32.GetLastError() == ERROR_ALREADY_EXISTS:
            kernel32.CloseHandle(handle)
            try:
                ctypes.windll.user32.MessageBoxW(
                    0,
                    "Glosaap ya está en ejecución.\n\n"
                    "Ciérralo antes de abrir otra instancia.",
                    "Glosaap",
                    0x40,
                )
            except Exception:
                pass
            sys.exit(0)
        _mutex_handle = handle  # Mantener vivo hasta el fin del proceso.
    except Exception:
        pass


if __name__ == "__main__":
    _ensure_single_instance()
    _preflight_flet_desktop()
    ft.app(target=main)
