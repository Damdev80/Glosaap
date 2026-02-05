"""
Gestor simple de credenciales
"""
import json
import os
import sys
from typing import Optional


class CredentialManager:
    """Gestor de credenciales guardadas localmente"""
    
    def __init__(self, config_dir: Optional[str] = None):
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
    
    def save_credentials(self, service: str, username: str, password: str, **extra_fields) -> bool:
        """
        Guarda credenciales para un servicio
        
        Args:
            service: Nombre del servicio (ej: "fomag", "familiar")
            username: Usuario
            password: Contraseña
            **extra_fields: Campos adicionales (ej: nit="123456")
            
        Returns:
            True si se guardó correctamente
        """
        try:
            # Cargar credenciales existentes
            credentials = {}
            if os.path.exists(self.credentials_file):
                with open(self.credentials_file, 'r', encoding='utf-8') as f:
                    credentials = json.load(f)
            
            # Agregar/actualizar
            credentials[service] = {
                "username": username,
                "password": password,
                **extra_fields
            }
            
            # Guardar
            with open(self.credentials_file, 'w', encoding='utf-8') as f:
                json.dump(credentials, f, indent=2)
            
            return True
            
        except Exception as e:
            print(f"Error guardando credenciales: {e}")
            return False
    
    def load_credentials(self, service: str) -> Optional[dict]:
        """
        Carga credenciales de un servicio
        
        Args:
            service: Nombre del servicio
            
        Returns:
            dict con username y password, o None si no existe
        """
        try:
            if not os.path.exists(self.credentials_file):
                return None
            
            with open(self.credentials_file, 'r', encoding='utf-8') as f:
                credentials = json.load(f)
            
            return credentials.get(service)
            
        except Exception as e:
            print(f"Error cargando credenciales: {e}")
            return None
    
    def delete_credentials(self, service: str) -> bool:
        """
        Elimina credenciales de un servicio
        
        Args:
            service: Nombre del servicio
            
        Returns:
            True si se eliminó correctamente
        """
        try:
            if not os.path.exists(self.credentials_file):
                return True
            
            with open(self.credentials_file, 'r', encoding='utf-8') as f:
                credentials = json.load(f)
            
            if service in credentials:
                del credentials[service]
                
                with open(self.credentials_file, 'w', encoding='utf-8') as f:
                    json.dump(credentials, f, indent=2)
            
            return True
            
        except Exception as e:
            print(f"Error eliminando credenciales: {e}")
            return False
