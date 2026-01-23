"""
Clase base para scrapers de portales web de EPS
"""
import os
from abc import ABC, abstractmethod
from typing import Optional, Callable


class BaseScraper(ABC):
    """Clase base para automatización de portales web"""
    
    def __init__(self, download_dir: str = None, progress_callback: Callable = None):
        """
        Args:
            download_dir: Directorio de descargas
            progress_callback: Función para reportar progreso (mensaje)
        """
        self.download_dir = download_dir or os.path.join(
            os.path.expanduser("~"), "Desktop", "descargas_glosaap"
        )
        self.progress_callback = progress_callback or print
        os.makedirs(self.download_dir, exist_ok=True)
    
    def log(self, message: str):
        """Envía mensaje al callback de progreso"""
        if self.progress_callback:
            self.progress_callback(message)
    
    @abstractmethod
    def login_and_download(self, **kwargs) -> dict:
        """
        Ejecuta login y descarga de archivos
        
        Returns:
            dict con {"success": bool, "files": int, "message": str}
        """
        pass
