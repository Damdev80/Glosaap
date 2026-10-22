"""
Configuración de la aplicación
"""
from app.config.eps_config import EPS_CONFIG, get_all_eps, get_enabled_eps, get_eps_by_name, get_eps_list
from app.config.settings import (
    ALLOWED_EXTENSIONS,
    HOMOLOGADOR_FILES,
    IMAP_CONFIG,
    NETWORK_PATHS,
    ensure_dir,
    get_homologador_path,
    get_output_dir,
    is_network_available,
    logger,
)

__all__ = [
    "ALLOWED_EXTENSIONS",
    "EPS_CONFIG",
    "HOMOLOGADOR_FILES",
    "IMAP_CONFIG",
    "NETWORK_PATHS",
    "ensure_dir",
    "get_all_eps",
    "get_enabled_eps",
    "get_eps_by_name",
    "get_eps_list",
    "get_homologador_path",
    "get_output_dir",
    "is_network_available",
    "logger",
]

