"""
Configuración centralizada de la aplicación Glosaap

Este archivo contiene todas las constantes, rutas y configuraciones
que se utilizan a lo largo de la aplicación.
"""
import os
import logging
from pathlib import Path

# ==================== INFORMACIÓN DE LA APLICACIÓN ====================

# Versión actual de la aplicación (seguir semver: MAJOR.MINOR.PATCH)
# Actualizar manualmente en cada release
APP_VERSION = "1.0.0"

# Nombre de la aplicación
APP_NAME = "Glosaap"

# Repositorio de GitHub para actualizaciones (formato: owner/repo)
GITHUB_REPO = "Damdev80/Glosaap"

# Configuración de auto-actualización
AUTO_UPDATE_CONFIG = {
    "enabled": True,              # Habilitar verificación automática
    "check_on_startup": False,    # Verificar al iniciar la app (deshabilitado hasta primera release)
    "check_interval_hours": 24,   # Intervalo entre verificaciones automáticas
    "show_changelog": True,       # Mostrar changelog en diálogo de actualización
    "create_backup": True,        # Crear backup antes de actualizar
}

# ==================== RUTAS BASE ====================

# Directorio raíz del proyecto
PROJECT_ROOT = Path(__file__).parent.parent.parent

# Directorio de assets
ASSETS_DIR = PROJECT_ROOT / "assets"

# Directorio temporal local
TEMP_DIR = Path(os.environ.get('TEMP', '/tmp')) / "glosaap"

# ==================== RUTAS DE RED ====================

# Servidor de archivos
NETWORK_BASE = r"\\MINERVA\Cartera\GLOSAAP"

# Subdirectorios en el servidor
NETWORK_PATHS = {
    "homologador": os.path.join(NETWORK_BASE, "HOMOLOGADOR"),
    "resultados": os.path.join(NETWORK_BASE, "REPOSITORIO DE RESULTADOS"),
    "mutualser_output": os.path.join(NETWORK_BASE, "REPOSITORIO DE RESULTADOS", "MUTUALSER"),
    "coosalud_output": os.path.join(NETWORK_BASE, "REPOSITORIO DE RESULTADOS", "COOSALUD"),
}

# Archivos de homologación por EPS
HOMOLOGADOR_FILES = {
    "mutualser": os.path.join(NETWORK_PATHS["homologador"], "mutualser_homologacion.xlsx"),
    "coosalud": os.path.join(NETWORK_PATHS["homologador"], "mutualser_homologacion.xlsx"),  # Usa el mismo
}

# ==================== CONFIGURACIÓN IMAP ====================

IMAP_CONFIG = {
    "default_port": 993,
    "use_ssl": True,
    "search_timeout": 30,  # segundos
    "search_limit": None,  # Sin límite - busca todos los correos
    "known_servers": {
        'gmail.com': 'imap.gmail.com',
        'googlemail.com': 'imap.gmail.com',
        'outlook.com': 'outlook.office365.com',
        'hotmail.com': 'outlook.office365.com',
        'live.com': 'outlook.office365.com',
        'yahoo.com': 'imap.mail.yahoo.com',
        'yahoo.es': 'imap.mail.yahoo.com',
    }
}

# ==================== EXTENSIONES DE ARCHIVO ====================

ALLOWED_EXTENSIONS = {
    "excel": ('.xlsx', '.xls', '.xlsm', '.xlsb'),
    "word": ('.doc', '.docx', '.docm'),
    "pdf": ('.pdf',),
    "csv": ('.csv',),
}

# Todas las extensiones permitidas para descarga
ALL_ALLOWED_EXTENSIONS = (
    ALLOWED_EXTENSIONS["excel"] + 
    ALLOWED_EXTENSIONS["word"] + 
    ALLOWED_EXTENSIONS["pdf"]
)

# ==================== CONFIGURACIÓN DE LOGGING ====================

LOG_CONFIG = {
    "level": logging.INFO,
    "format": "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    "date_format": "%Y-%m-%d %H:%M:%S",
    "file": TEMP_DIR / "glosaap.log",
}

# ==================== CONFIGURACIÓN DE UI ====================

WINDOW_SIZES = {
    "login": {"width": 450, "height": 550},
    "dashboard": {"width": 1200, "height": 700},
    "messages": {"width": 1200, "height": 700},
    "tools": {"width": 900, "height": 600},
}

# ==================== FUNCIONES DE UTILIDAD ====================

def is_network_available() -> bool:
    """Verifica si el servidor de red está disponible"""
    return os.path.exists(NETWORK_BASE)

def get_output_dir(eps_name: str) -> str:
    """Obtiene el directorio de salida para una EPS"""
    eps_key = eps_name.lower()
    if eps_key in NETWORK_PATHS:
        return NETWORK_PATHS[f"{eps_key}_output"]
    return str(TEMP_DIR / eps_name)

def get_homologador_path(eps_name: str) -> str:
    """Obtiene la ruta del homologador para una EPS"""
    eps_key = eps_name.lower()
    return HOMOLOGADOR_FILES.get(eps_key, HOMOLOGADOR_FILES["mutualser"])

def ensure_dir(path: str) -> bool:
    """Crea un directorio si no existe"""
    try:
        os.makedirs(path, exist_ok=True)
        return True
    except Exception:
        return False


# ==================== INICIALIZACIÓN ====================

def setup_logging():
    """Configura el sistema de logging"""
    ensure_dir(str(TEMP_DIR))
    
    logging.basicConfig(
        level=LOG_CONFIG["level"],
        format=LOG_CONFIG["format"],
        datefmt=LOG_CONFIG["date_format"],
        handlers=[
            logging.StreamHandler(),  # Consola
            logging.FileHandler(LOG_CONFIG["file"], encoding='utf-8')  # Archivo
        ]
    )
    
    return logging.getLogger("glosaap")


# Logger global de la aplicación
logger = setup_logging()
