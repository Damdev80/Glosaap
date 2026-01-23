"""
Módulo de procesadores de archivos por EPS
Cada EPS tiene su propio procesador que sabe cómo manejar sus archivos específicos
"""

from .base_processor import BaseProcessor
from .coosalud_processor import CoosaludProcessor

# Re-exportar MutualserProcessor desde core para mantener compatibilidad
from app.core.mutualser_processor import MutualserProcessor

__all__ = [
    "BaseProcessor",
    "CoosaludProcessor",
    "MutualserProcessor",
]
