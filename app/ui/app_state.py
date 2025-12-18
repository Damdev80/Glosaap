"""
Estado global de la aplicación Glosaap

Centraliza el estado compartido entre todos los módulos de la UI.
"""
from dataclasses import dataclass, field
from typing import Optional, Dict, List, Any
from datetime import datetime


@dataclass
class AppState:
    """Estado global de la aplicación"""
    
    # Vista actual
    current_view: str = "login"
    
    # EPS seleccionada
    selected_eps: Optional[Dict[str, Any]] = None
    
    # Rango de fechas para búsqueda
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    
    # Acción del dashboard
    dashboard_action: Optional[str] = None
    
    # Mensajes encontrados
    found_messages: List[Dict[str, Any]] = field(default_factory=list)
    
    def reset(self):
        """Reinicia el estado a valores por defecto"""
        self.current_view = "login"
        self.selected_eps = None
        self.date_from = None
        self.date_to = None
        self.dashboard_action = None
        self.found_messages = []
    
    def set_eps(self, eps_info: Dict[str, Any], date_from: datetime = None, date_to: datetime = None):
        """Establece la EPS seleccionada con su rango de fechas"""
        self.selected_eps = eps_info
        self.date_from = date_from
        self.date_to = date_to
    
    def get_search_info(self) -> str:
        """Retorna información formateada de la búsqueda actual"""
        if not self.selected_eps:
            return ""
        
        eps_name = self.selected_eps.get("name", "")
        date_info = ""
        
        if self.date_from and self.date_to:
            date_info = f" | {self.date_from.strftime('%d/%m/%Y')} - {self.date_to.strftime('%d/%m/%Y')}"
        elif self.date_from:
            date_info = f" | Desde {self.date_from.strftime('%d/%m/%Y')}"
        elif self.date_to:
            date_info = f" | Hasta {self.date_to.strftime('%d/%m/%Y')}"
        
        return f"EPS: {eps_name}{date_info}"
    
    def get_eps_filter(self) -> str:
        """Retorna el filtro de la EPS seleccionada en minúsculas"""
        if not self.selected_eps:
            return ""
        return (self.selected_eps.get("filter") or "").lower()


# Instancia global del estado
app_state = AppState()
