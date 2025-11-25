"""
Configuración de las EPS disponibles en el sistema
Cada EPS tiene su propia configuración para filtrado y procesamiento
"""


class EpsInfo:
    """Clase base para información de una EPS"""
    
    def __init__(
        self,
        name: str,
        icon: str,
        description: str,
        filter_value: str = None,
        filter_type: str = None,
        subject_pattern: str = None,
        processor_class: str = None,
        enabled: bool = True
    ):
        self.name = name
        self.icon = icon
        self.description = description
        self.filter = filter_value
        self.filter_type = filter_type
        self.subject_pattern = subject_pattern
        self.processor_class = processor_class
        self.enabled = enabled
    
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
            "enabled": self.enabled
        }


# ==================== CONFIGURACIÓN DE CADA EPS ====================

class TodasLasEps(EpsInfo):
    """Configuración para buscar en todas las EPS (sin filtro)"""
    
    def __init__(self):
        super().__init__(
            name="Todas las EPS",
            icon="🏥",
            description="Sin filtro",
            filter_value=None,
            filter_type=None,
            processor_class=None,
            enabled=True
        )


class MutualserEps(EpsInfo):
    """Configuración para Mutualser EPS"""
    
    def __init__(self):
        super().__init__(
            name="Mutualser",
            icon="🔵",
            description="Mutualser EPS",
            filter_value="mutualser",
            filter_type="subject_exact_pattern",
            subject_pattern="objeciones de glosa factura fc",
            processor_class="MutualserProcessor",
            enabled=True
        )


class SanitasEps(EpsInfo):
    """Configuración para Sanitas EPS"""
    
    def __init__(self):
        super().__init__(
            name="Sanitas",
            icon="🟢",
            description="Sanitas EPS",
            filter_value="sanitas",
            filter_type="keyword",
            processor_class=None,  # Pendiente de implementar
            enabled=True
        )


class NuevaEps(EpsInfo):
    """Configuración para Nueva EPS"""
    
    def __init__(self):
        super().__init__(
            name="Nueva EPS",
            icon="🟠",
            description="Nueva EPS",
            filter_value="nuevaeps",
            filter_type="keyword",
            processor_class=None,  # Pendiente de implementar
            enabled=True
        )


class CompensarEps(EpsInfo):
    """Configuración para Compensar EPS"""
    
    def __init__(self):
        super().__init__(
            name="Compensar",
            icon="🟡",
            description="Compensar EPS",
            filter_value="compensar",
            filter_type="keyword",
            processor_class=None,  # Pendiente de implementar
            enabled=True
        )


class FamisanarEps(EpsInfo):
    """Configuración para Famisanar EPS"""
    
    def __init__(self):
        super().__init__(
            name="Famisanar",
            icon="🟣",
            description="Famisanar EPS",
            filter_value="famisanar",
            filter_type="keyword",
            processor_class=None,  # Pendiente de implementar
            enabled=True
        )


class CosaludEps(EpsInfo):
    """Configuración para Cosalud EPS"""
    
    def __init__(self):
        super().__init__(
            name="Cosalud",
            icon="🔴",
            description="Cosalud EPS",
            filter_value="cosalud",
            filter_type="keyword",
            processor_class="CosaludProcessor",  # Pendiente de implementar
            enabled=True
        )


# ==================== LISTA DE EPS DISPONIBLES ====================

# Instancias de cada EPS
EPS_CONFIG = [
    TodasLasEps(),
    MutualserEps(),
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


def get_eps_by_name(name: str) -> EpsInfo:
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

