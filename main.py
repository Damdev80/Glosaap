"""
Punto de entrada principal para Glosaap
Ejecuta la nueva versión modular de la aplicación
"""
import sys
import os

# Configurar ruta de navegadores de Playwright ANTES de cualquier import
if sys.platform == 'win32':
    browsers_path = os.path.join(os.getenv('APPDATA'), 'Glosaap', 'browsers')
    os.environ['PLAYWRIGHT_BROWSERS_PATH'] = browsers_path
    # Crear directorio si no existe
    os.makedirs(browsers_path, exist_ok=True)

# Agregar el directorio raíz al path para imports
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

# Importar y ejecutar la app
from app.ui.app import main
import flet as ft

if __name__ == "__main__":
    ft.app(target=main)
