"""
Punto de entrada principal para Glosaap
Ejecuta la nueva versión modular de la aplicación
"""
import sys
import os

# Agregar el directorio app al path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

# Importar y ejecutar la app
from ui.app_new import main
import flet as ft

if __name__ == "__main__":
    ft.app(target=main)
