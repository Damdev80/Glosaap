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

if __name__ == "__main__":
    ft.app(target=main)
