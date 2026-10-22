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


if __name__ == "__main__":
    _preflight_flet_desktop()
    ft.app(target=main)
