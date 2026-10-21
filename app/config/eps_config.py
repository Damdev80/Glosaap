""" 
Configuración de las EPS disponibles en el sistema
Cada EPS tiene su propia configuración para filtrado y procesamiento

Fuente única de rutas de homologación: app/config/settings.py
(HOMOLOGADOR_FILES + get_homologador_path()). Prohibido hardcodear
rutas UNC de red en este archivo.
"""
import os

from app.config.settings import get_homologador_path

# Ruta de assets
ASSETS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "assets"))


class EpsInfo:
    """Clase base para información de una EPS"""
    
    def __init__(
        self,
        name: str,
        icon: str,
        description: str,
        filter_value: str | None = None,
        filter_type: str | None = None,
        subject_pattern: str | None = None,
        processor_class: str | None = None,
        enabled: bool = True,
        image_path: str | None = None,
        homologador_file: str | None = None,
        sender_filter: str | None = None
    ):
        self.name = name
        self.icon = icon
        self.description = description
        self.filter = filter_value
        self.filter_type = filter_type
        self.subject_pattern = subject_pattern
        self.processor_class = processor_class
        self.enabled = enabled
        self.image_path = image_path
        self.sender_filter = sender_filter  # Correo específico del remitente
        # Ruta completa al archivo de homologación de esta EPS.
        # Fuente única: settings.get_homologador_path(). `homologador_file`
        # se interpreta como clave de EPS ("mutualser"/"coosalud") por
        # compatibilidad; no se construyen rutas UNC aquí.
        if homologador_file:
            try:
                self.homologador_path = get_homologador_path(homologador_file)
            except Exception:
                self.homologador_path = None
        else:
            self.homologador_path = None
    
    def to_dict(self) -> dict:
        """Convierte a diccionario para compatibilidad con código existente"""
        return {
            "name": self.name,
            "icon": self.icon,
            "description": self.description,
            "filter": self.filter,
            "filter_type": self.filter_type,
            "subject_pattern": self.subject_pattern,
            "processor_class": self.processor_class,
            "enabled": self.enabled,
            "image_path": self.image_path,
            "homologador_path": self.homologador_path,
            "sender_filter": self.sender_filter
        }
# ==================== CONFIGURACIÓN DE CADA EPS ====================



    
class MutualserEps(EpsInfo):
    """Configuración para Mutualser EPS"""
    
    def __init__(self):
        super().__init__(
            name="Mutualser",
            icon="🟢",
            description="Mutualser EPS",
            filter_value="mutualser",
            filter_type="subject_exact_pattern",
            subject_pattern="Objeciones de glosa Factura FC",
            processor_class="MutualserProcessor",
            enabled=True,
            image_path=os.path.join(ASSETS_DIR, "img", "eps", "mutualser.png"),
            homologador_file="mutualser"
        )


class CoosaludEps(EpsInfo):
    """Configuración para Coosalud EPS"""
    
    def __init__(self):
        super().__init__(
            name="Coosalud",
            icon="🟢",
            description="Coosalud EPS",
            filter_value="coosalud",
            filter_type="subject_exact_pattern",
            subject_pattern="Reporte Glosas y Devoluciones",
            processor_class="CoosaludProcessor",
            enabled=True,
            image_path=os.path.join(ASSETS_DIR, "img", "eps", "coosalud.png"),
            homologador_file="coosalud",
        )


class SanitasEps(EpsInfo):
    """Configuración para Sanitas EPS (sin procesador: visible, en desarrollo)"""

    def __init__(self):
        super().__init__(
            name="Sanitas",
            icon="🔵",
            description="Sanitas EPS",
            filter_value="sanitas",
            filter_type="subject_exact_pattern",
            subject_pattern="Referencia: Informe Glosas EPS Sanitas",
            processor_class=None,
            enabled=True,
            image_path=os.path.join(ASSETS_DIR, "img", "eps", "sanitas.png"),
            sender_filter="cuentasmedicaseps@epssanitas.notify-it.com",
        )


class NuevaEps(EpsInfo):
    """Configuración para Nueva EPS (sin procesador: deshabilitada)"""
    
    def __init__(self):
        super().__init__(
            name="Nueva EPS",
            icon="🟠",
            description="Nueva EPS",
            filter_value="nuevaeps",
            filter_type="keyword",
            processor_class=None,  # Pendiente de implementar
            enabled=False
        )


class CompensarEps(EpsInfo):
    """Configuración para Compensar EPS (sin procesador: deshabilitada)"""
    
    def __init__(self):
        super().__init__(
            name="Compensar",
            icon="🟡",
            description="Compensar EPS",
            filter_value="compensar",
            filter_type="keyword",
            processor_class=None,  # Pendiente de implementar
            enabled=False
        )


class FamisanarEps(EpsInfo):
    """Configuración para Famisanar EPS (sin procesador: deshabilitada)"""
    
    def __init__(self):
        super().__init__(
            name="Famisanar",
            icon="🟣",
            description="Famisanar EPS",
            filter_value="famisanar",
            filter_type="keyword",
            processor_class=None,  # Pendiente de implementar
            enabled=False
        )


class CosaludEps(EpsInfo):
    """Configuración para Cosalud EPS (typo de Coosalud, procesador inexistente: deshabilitada)"""
    
    def __init__(self):
        super().__init__(
            name="Cosalud",
            icon="🔴",
            description="Cosalud EPS",
            filter_value="cosalud",
            filter_type="keyword",
            processor_class="CosaludProcessor",  # Procesador inexistente (typo de CoosaludProcessor)
            enabled=False
        )


# ==================== LISTA DE EPS DISPONIBLES ====================

# Instancias de cada EPS
EPS_CONFIG = [
    MutualserEps(),
    CoosaludEps(),
    SanitasEps(),
    NuevaEps(),
    CompensarEps(),
    FamisanarEps(),
    CosaludEps()
]


def get_eps_list() -> list:
    """
    Retorna la lista de EPS como diccionarios para compatibilidad
    
    Returns:
        Lista de diccionarios con info de cada EPS
    """
    return [eps.to_dict() for eps in EPS_CONFIG if eps.enabled]


def get_eps_by_name(name: str) -> EpsInfo | None:
    """
    Busca una EPS por nombre
    
    Args:
        name: Nombre de la EPS
        
    Returns:
        EpsInfo o None si no se encuentra
    """
    for eps in EPS_CONFIG:
        if eps.name.lower() == name.lower():
            return eps
    return None


def get_all_eps() -> list:
    """
    Retorna todas las instancias de EPS
    
    Returns:
        Lista de EpsInfo
    """
    return EPS_CONFIG


def get_enabled_eps() -> list:
    """
    Retorna solo las EPS habilitadas
    
    Returns:
        Lista de EpsInfo habilitadas
    """
    return [eps for eps in EPS_CONFIG if eps.enabled]

