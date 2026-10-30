"""
Módulo de procesadores de archivos por EPS
Cada EPS tiene su propio procesador que sabe cómo manejar sus archivos específicos
"""

from .base_processor import BaseProcessor
from .coosalud_processor import CoosaludProcessor
from .previsora_processor import PrevisoraProcessor
from .sanitas_processor import SanitasProcessor

__all__ = [
    "BaseProcessor",
    "CoosaludProcessor",
    "PrevisoraProcessor",
    "SanitasProcessor",
    "MutualserProcessor",
]


def __getattr__(name: str):
    # Importación perezosa para evitar ciclo circular:
    # app.core.mutualser_processor importa BaseProcessor desde este paquete.
    if name == "MutualserProcessor":
        from app.core.mutualser_processor import MutualserProcessor

        return MutualserProcessor
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
