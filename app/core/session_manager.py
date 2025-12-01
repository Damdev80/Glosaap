"""
Gestor de sesiones - Guarda y carga credenciales de usuario
"""
import os
import json
import base64

# Ruta del archivo de sesión
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
SESSION_FILE = os.path.join(PROJECT_ROOT, ".session.json")


def save_session(email, password, server):
    """
    Guarda la sesión en un archivo local
    
    Args:
        email: Correo electrónico
        password: Contraseña (se codifica en base64)
        server: Servidor IMAP
    """
    try:
        session_data = {
            "email": email,
            "password": base64.b64encode(password.encode()).decode(),
            "server": server
        }
        with open(SESSION_FILE, 'w') as f:
            json.dump(session_data, f)
    except Exception as e:
        print(f"Error guardando sesión: {e}")


def load_session():
    """
    Carga la sesión guardada
    
    Returns:
        dict con {email, password, server} o None si no existe
    """
    try:
        if os.path.exists(SESSION_FILE):
            with open(SESSION_FILE, 'r') as f:
                data = json.load(f)
            return {
                "email": data.get("email", ""),
                "password": base64.b64decode(data.get("password", "")).decode(),
                "server": data.get("server", "")
            }
    except Exception as e:
        print(f"Error cargando sesión: {e}")
    return None


def clear_session():
    """Elimina la sesión guardada"""
    try:
        if os.path.exists(SESSION_FILE):
            os.remove(SESSION_FILE)
    except Exception as e:
        print(f"Error eliminando sesión: {e}")
