"""
Servicio de actualización automática para Glosaap

Este módulo maneja la verificación y descarga de actualizaciones
desde GitHub Releases.
"""
import os
import sys
import json
import tempfile
import subprocess
import urllib.request
import urllib.error
import ssl
import re
from pathlib import Path
from typing import Optional, Callable
from dataclasses import dataclass

from app.config.settings import logger, TEMP_DIR


# ==================== CONFIGURACIÓN ====================

# Repositorio de GitHub (formato: owner/repo)
GITHUB_REPO = "Damdev80/Glosaap"

# URL base de la API de GitHub
GITHUB_API_BASE = "https://api.github.com"

# Nombre del asset a descargar (el .zip con el ejecutable)
RELEASE_ASSET_PATTERN = r"Glosaap.*\.zip"

# Directorio de descargas temporales
UPDATE_DOWNLOAD_DIR = TEMP_DIR / "updates"


# ==================== MODELO DE DATOS ====================

@dataclass
class ReleaseInfo:
    """Información de una release de GitHub"""
    version: str
    tag_name: str
    name: str
    body: str  # Changelog/descripción
    published_at: str
    download_url: str
    asset_name: str
    asset_size: int
    
    @property
    def changelog(self) -> str:
        """Retorna el changelog formateado"""
        return self.body or "Sin descripción disponible."
    
    @property
    def size_mb(self) -> float:
        """Retorna el tamaño en MB"""
        return self.asset_size / (1024 * 1024)


# ==================== COMPARACIÓN DE VERSIONES ====================

def parse_version(version_str: str) -> tuple:
    """
    Parsea una cadena de versión semver a una tupla comparable.
    
    Ejemplos:
        "1.0.0" -> (1, 0, 0, '')
        "v1.2.3" -> (1, 2, 3, '')
        "2.0.0-beta" -> (2, 0, 0, 'beta')
        "1.0.0-rc.1" -> (1, 0, 0, 'rc.1')
    """
    # Remover prefijo 'v' si existe
    version_str = version_str.lstrip('v').strip()
    
    # Separar versión base de prerelease
    if '-' in version_str:
        base, prerelease = version_str.split('-', 1)
    else:
        base, prerelease = version_str, ''
    
    # Parsear números de versión
    parts = base.split('.')
    try:
        major = int(parts[0]) if len(parts) > 0 else 0
        minor = int(parts[1]) if len(parts) > 1 else 0
        patch = int(parts[2]) if len(parts) > 2 else 0
    except ValueError:
        # Si no se puede parsear, retornar versión 0.0.0
        logger.warning(f"No se pudo parsear versión: {version_str}")
        return (0, 0, 0, version_str)
    
    return (major, minor, patch, prerelease)


def compare_versions(current: str, remote: str) -> int:
    """
    Compara dos versiones semver.
    
    Retorna:
        -1 si current < remote (hay actualización disponible)
         0 si current == remote
         1 si current > remote
    """
    current_tuple = parse_version(current)
    remote_tuple = parse_version(remote)
    
    # Comparar major, minor, patch
    for i in range(3):
        if current_tuple[i] < remote_tuple[i]:
            return -1
        elif current_tuple[i] > remote_tuple[i]:
            return 1
    
    # Si los números son iguales, comparar prerelease
    # Una versión sin prerelease es mayor que una con prerelease
    # Ej: 1.0.0 > 1.0.0-beta
    current_pre = current_tuple[3]
    remote_pre = remote_tuple[3]
    
    if not current_pre and remote_pre:
        return 1  # current es release, remote es prerelease
    elif current_pre and not remote_pre:
        return -1  # current es prerelease, remote es release
    elif current_pre and remote_pre:
        # Ambos son prerelease, comparar alfabéticamente
        if current_pre < remote_pre:
            return -1
        elif current_pre > remote_pre:
            return 1
    
    return 0


def is_update_available(current_version: str, remote_version: str) -> bool:
    """Verifica si hay una actualización disponible"""
    return compare_versions(current_version, remote_version) < 0


# ==================== SERVICIO DE ACTUALIZACIÓN ====================

class UpdateService:
    """
    Servicio para verificar y descargar actualizaciones de GitHub Releases.
    
    Uso:
        service = UpdateService(current_version="1.0.0")
        release = await service.check_for_updates()
        if release:
            service.download_update(release, on_progress=callback)
            service.launch_updater()
    """
    
    def __init__(self, current_version: str, github_repo: str = GITHUB_REPO):
        """
        Inicializa el servicio de actualización.
        
        Args:
            current_version: Versión actual de la aplicación
            github_repo: Repositorio de GitHub (formato: owner/repo)
        """
        self.current_version = current_version
        self.github_repo = github_repo
        self._downloaded_file: Optional[Path] = None
        self._ssl_context = self._create_ssl_context()
    
    def _create_ssl_context(self) -> ssl.SSLContext:
        """Crea un contexto SSL para conexiones HTTPS"""
        ctx = ssl.create_default_context()
        return ctx
    
    def _make_request(self, url: str, headers: dict | None = None) -> dict:
        """
        Realiza una petición HTTP GET.
        
        Args:
            url: URL a consultar
            headers: Headers adicionales
            
        Returns:
            Respuesta JSON parseada
            
        Raises:
            UpdateCheckError: Si hay error en la conexión
        """
        default_headers = {
            'User-Agent': 'Glosaap-Updater/1.0',
            'Accept': 'application/vnd.github.v3+json'
        }
        if headers:
            default_headers.update(headers)
        
        request = urllib.request.Request(url, headers=default_headers)
        
        try:
            with urllib.request.urlopen(request, context=self._ssl_context, timeout=30) as response:
                return json.loads(response.read().decode('utf-8'))
        except urllib.error.HTTPError as e:
            logger.error(f"Error HTTP al consultar {url}: {e.code} {e.reason}")
            raise UpdateCheckError(f"Error al consultar GitHub: {e.code} {e.reason}")
        except urllib.error.URLError as e:
            logger.error(f"Error de conexión: {e.reason}")
            raise UpdateCheckError(f"Sin conexión a internet: {e.reason}")
        except json.JSONDecodeError as e:
            logger.error(f"Error parseando respuesta JSON: {e}")
            raise UpdateCheckError("Respuesta inválida del servidor")
    
    def check_for_updates(self) -> Optional[ReleaseInfo]:
        """
        Verifica si hay actualizaciones disponibles.
        
        Returns:
            ReleaseInfo si hay actualización, None si no
            
        Raises:
            UpdateCheckError: Si hay error de conexión o API
        """
        logger.info(f"Verificando actualizaciones para {self.github_repo}...")
        
        # Obtener última release
        url = f"{GITHUB_API_BASE}/repos/{self.github_repo}/releases/latest"
        
        try:
            data = self._make_request(url)
        except UpdateCheckError:
            raise
        except Exception as e:
            logger.error(f"Error inesperado verificando actualizaciones: {e}")
            raise UpdateCheckError(f"Error verificando actualizaciones: {str(e)}")
        
        # Extraer información
        tag_name = data.get('tag_name', '')
        remote_version = tag_name.lstrip('v')
        
        logger.info(f"Versión actual: {self.current_version}, Versión remota: {remote_version}")
        
        # Comparar versiones
        if not is_update_available(self.current_version, remote_version):
            logger.info("No hay actualizaciones disponibles")
            return None
        
        # Buscar el asset correcto para descargar
        assets = data.get('assets', [])
        download_url = None
        asset_name = None
        asset_size = 0
        
        pattern = re.compile(RELEASE_ASSET_PATTERN, re.IGNORECASE)
        for asset in assets:
            name = asset.get('name', '')
            if pattern.match(name):
                download_url = asset.get('browser_download_url')
                asset_name = name
                asset_size = asset.get('size', 0)
                break
        
        if not download_url:
            # Si no hay zip específico, buscar cualquier zip
            for asset in assets:
                name = asset.get('name', '')
                if name.endswith('.zip'):
                    download_url = asset.get('browser_download_url')
                    asset_name = name
                    asset_size = asset.get('size', 0)
                    break
        
        if not download_url:
            logger.warning("No se encontró asset descargable en la release")
            raise UpdateCheckError("La actualización no tiene archivos descargables")
        
        release_info = ReleaseInfo(
            version=remote_version,
            tag_name=tag_name,
            name=data.get('name', f'Versión {remote_version}'),
            body=data.get('body', ''),
            published_at=data.get('published_at', ''),
            download_url=download_url,
            asset_name=asset_name or '',
            asset_size=asset_size
        )
        
        logger.info(f"Actualización disponible: {release_info.version} ({release_info.size_mb:.1f} MB)")
        return release_info
    
    def download_update(
        self,
        release: ReleaseInfo,
        on_progress: Optional[Callable[[int, int], None]] = None
    ) -> Path:
        """
        Descarga la actualización.
        
        Args:
            release: Información de la release a descargar
            on_progress: Callback con (bytes_descargados, total_bytes)
            
        Returns:
            Ruta al archivo descargado
            
        Raises:
            UpdateDownloadError: Si hay error en la descarga
        """
        logger.info(f"Descargando actualización: {release.download_url}")
        
        # Crear directorio de descargas
        UPDATE_DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)
        
        # Ruta destino
        dest_path = UPDATE_DOWNLOAD_DIR / release.asset_name
        
        # Si ya existe, eliminarlo
        if dest_path.exists():
            dest_path.unlink()
        
        request = urllib.request.Request(
            release.download_url,
            headers={'User-Agent': 'Glosaap-Updater/1.0'}
        )
        
        try:
            with urllib.request.urlopen(request, context=self._ssl_context, timeout=300) as response:
                total_size = int(response.headers.get('Content-Length', release.asset_size))
                downloaded = 0
                chunk_size = 8192
                
                with open(dest_path, 'wb') as f:
                    while True:
                        chunk = response.read(chunk_size)
                        if not chunk:
                            break
                        f.write(chunk)
                        downloaded += len(chunk)
                        
                        if on_progress:
                            on_progress(downloaded, total_size)
            
            logger.info(f"Descarga completada: {dest_path}")
            self._downloaded_file = dest_path
            return dest_path
            
        except urllib.error.HTTPError as e:
            logger.error(f"Error HTTP descargando: {e.code}")
            raise UpdateDownloadError(f"Error al descargar: {e.code} {e.reason}")
        except urllib.error.URLError as e:
            logger.error(f"Error de conexión descargando: {e.reason}")
            raise UpdateDownloadError(f"Error de conexión: {e.reason}")
        except IOError as e:
            logger.error(f"Error escribiendo archivo: {e}")
            raise UpdateDownloadError(f"Error guardando archivo: {str(e)}")
        except Exception as e:
            logger.error(f"Error inesperado descargando: {e}")
            raise UpdateDownloadError(f"Error inesperado: {str(e)}")
    
    def launch_updater(self, downloaded_file: Optional[Path] = None) -> bool:
        """
        Lanza el proceso de actualización.
        
        El updater.exe se encarga de:
        1. Esperar a que la app principal termine
        2. Extraer y reemplazar archivos
        3. Reiniciar la aplicación
        
        Args:
            downloaded_file: Ruta al archivo descargado (opcional, usa el último descargado)
            
        Returns:
            True si se lanzó correctamente
            
        Raises:
            UpdateLaunchError: Si no se puede iniciar el updater
        """
        update_file = downloaded_file or self._downloaded_file
        if not update_file or not update_file.exists():
            raise UpdateLaunchError("No hay archivo de actualización para instalar")
        
        # Determinar ruta del updater
        if getattr(sys, 'frozen', False):
            # Ejecutable compilado con PyInstaller
            app_dir = Path(sys.executable).parent
            updater_path = app_dir / "updater.exe"
        else:
            # Modo desarrollo
            app_dir = Path(__file__).parent.parent.parent
            updater_path = app_dir / "updater.exe"
            
            # En desarrollo, si no existe el exe, usar el script Python
            if not updater_path.exists():
                updater_script = app_dir / "updater.py"
                if updater_script.exists():
                    logger.info("Modo desarrollo: ejecutando updater.py")
                    # Ejecutar con Python
                    python_exe = sys.executable
                    args = [
                        python_exe,
                        str(updater_script),
                        "--update-file", str(update_file),
                        "--app-dir", str(app_dir),
                        "--app-exe", str(sys.executable),
                        "--pid", str(os.getpid())
                    ]
                    
                    logger.info(f"Lanzando updater: {' '.join(args)}")
                    subprocess.Popen(
                        args,
                        creationflags=subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS
                        if sys.platform == 'win32' else 0
                    )
                    return True
                else:
                    raise UpdateLaunchError("No se encontró el actualizador")
        
        if not updater_path.exists():
            raise UpdateLaunchError(f"Actualizador no encontrado: {updater_path}")
        
        # Argumentos para el updater
        # El updater necesita:
        # - Ruta al archivo zip descargado
        # - Directorio de la aplicación
        # - Ejecutable principal para reiniciar
        # - PID del proceso actual para esperar
        
        app_exe = sys.executable if getattr(sys, 'frozen', False) else "Glosaap.exe"
        
        args = [
            str(updater_path),
            "--update-file", str(update_file),
            "--app-dir", str(app_dir),
            "--app-exe", str(app_exe),
            "--pid", str(os.getpid())
        ]
        
        logger.info(f"Lanzando updater: {' '.join(args)}")
        
        try:
            # Lanzar como proceso independiente (detached)
            if sys.platform == 'win32':
                subprocess.Popen(
                    args,
                    creationflags=subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS
                )
            else:
                subprocess.Popen(args, start_new_session=True)
            
            return True
            
        except Exception as e:
            logger.error(f"Error lanzando updater: {e}")
            raise UpdateLaunchError(f"No se pudo iniciar el actualizador: {str(e)}")
    
    def get_all_releases(self, limit: int = 10) -> list[ReleaseInfo]:
        """
        Obtiene las últimas releases del repositorio.
        
        Args:
            limit: Número máximo de releases a obtener
            
        Returns:
            Lista de ReleaseInfo
        """
        url = f"{GITHUB_API_BASE}/repos/{self.github_repo}/releases?per_page={limit}"
        
        try:
            data = self._make_request(url)
        except Exception as e:
            logger.error(f"Error obteniendo releases: {e}")
            return []
        
        releases = []
        for item in data:
            # Buscar asset descargable
            assets = item.get('assets', [])
            download_url = None
            asset_name = None
            asset_size = 0
            
            pattern = re.compile(RELEASE_ASSET_PATTERN, re.IGNORECASE)
            for asset in assets:
                name = asset.get('name', '')
                if pattern.match(name) or name.endswith('.zip'):
                    download_url = asset.get('browser_download_url', '')
                    asset_name = name
                    asset_size = asset.get('size', 0)
                    break
            
            if download_url:
                releases.append(ReleaseInfo(
                    version=item.get('tag_name', '').lstrip('v'),
                    tag_name=item.get('tag_name', ''),
                    name=item.get('name', ''),
                    body=item.get('body', ''),
                    published_at=item.get('published_at', ''),
                    download_url=download_url,
                    asset_name=asset_name or '',
                    asset_size=asset_size
                ))
        
        return releases


# ==================== EXCEPCIONES ====================

class UpdateError(Exception):
    """Error base para actualizaciones"""
    pass


class UpdateCheckError(UpdateError):
    """Error al verificar actualizaciones"""
    pass


class UpdateDownloadError(UpdateError):
    """Error al descargar actualización"""
    pass


class UpdateLaunchError(UpdateError):
    """Error al iniciar el actualizador"""
    pass
