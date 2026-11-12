"""
Clase base para scrapers de portales web de EPS
"""
import os
import subprocess
import sys
from abc import ABC, abstractmethod
from collections.abc import Callable

SYSTEM_BROWSER_SUBPATHS = (
    os.path.join("Google", "Chrome", "Application", "chrome.exe"),
    os.path.join("Microsoft", "Edge", "Application", "msedge.exe"),
)


def find_system_browser() -> str | None:
    """Busca Google Chrome o Microsoft Edge instalado en Windows."""
    roots = [
        os.environ.get("PROGRAMFILES", ""),
        os.environ.get("PROGRAMFILES(X86)", ""),
        os.environ.get("LOCALAPPDATA", ""),
    ]
    for sub in SYSTEM_BROWSER_SUBPATHS:
        for root in roots:
            if not root:
                continue
            cand = os.path.join(root, sub)
            if os.path.exists(cand):
                return cand
    return None


def auto_install_chromium(log_fn: Callable[[str], None] | None = None) -> bool:
    """Descarga Chromium usando el driver embebido de Playwright."""
    try:
        from playwright._impl._driver import compute_driver_executable, get_driver_env

        driver_exe, driver_cli = compute_driver_executable()
        if not os.path.exists(str(driver_exe)):
            return False
        if log_fn:
            log_fn("📥 Instalando navegador Chromium por primera vez (1-2 min)...")
        flags = getattr(subprocess, "CREATE_NO_WINDOW", 0) if sys.platform == "win32" else 0
        res = subprocess.run(
            [str(driver_exe), str(driver_cli), "install", "chromium"],
            env=get_driver_env(),
            capture_output=True,
            text=True,
            timeout=300,
            creationflags=flags,
        )
        return res.returncode == 0
    except Exception:
        return False


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
