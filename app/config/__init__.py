"""
Configuración de la aplicación
"""
from app.config.eps_config import EPS_CONFIG, get_eps_by_name, get_all_eps
from app.config.settings import (
    NETWORK_PATHS,
    HOMOLOGADOR_FILES,
    IMAP_CONFIG,
    ALLOWED_EXTENSIONS,
    logger,
    is_network_available,
    get_output_dir,
    get_homologador_path,
    ensure_dir
)

