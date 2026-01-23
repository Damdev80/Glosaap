# Core package
"""
Módulo core - Contiene la lógica de negocio principal
"""
from app.core.imap_client import ImapClient
from app.core.mutualser_processor import MutualserProcessor

__all__ = [
    "ImapClient",
    "MutualserProcessor",
]
