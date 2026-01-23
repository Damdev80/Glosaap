"""
Tests para app_state.py
Cubre: manejo del estado global de la aplicación
"""
import pytest
from datetime import datetime
from app.ui.app_state import AppState


class TestAppState:
    """Tests para la clase AppState"""
    
    def test_initial_state(self):
        """Verifica que el estado inicial sea correcto"""
        state = AppState()
        
        assert state.current_view == "login"
        assert state.selected_eps is None
        assert state.date_from is None
        assert state.date_to is None
        assert state.dashboard_action is None
        assert state.found_messages == []
    
    def test_reset(self):
        """Verifica que reset() limpie todo el estado"""
        state = AppState()
        
        # Modificar el estado
        state.current_view = "dashboard"
        state.selected_eps = {"name": "Coosalud"}
        state.date_from = datetime(2026, 1, 1)
        state.found_messages = [{"id": 1}]
        
        # Resetear
        state.reset()
        
        # Verificar que todo volvió a valores por defecto
        assert state.current_view == "login"
        assert state.selected_eps is None
        assert state.date_from is None
        assert state.found_messages == []
    
    def test_set_eps(self):
        """Verifica que set_eps() guarde correctamente la EPS"""
        state = AppState()
        eps_info = {"name": "Coosalud", "filter": "coosalud"}
        date_from = datetime(2026, 1, 1)
        date_to = datetime(2026, 1, 31)
        
        state.set_eps(eps_info, date_from, date_to)
        
        assert state.selected_eps == eps_info
        assert state.date_from == date_from
        assert state.date_to == date_to
    
    def test_get_search_info_with_dates(self):
        """Verifica formato de información de búsqueda con fechas"""
        state = AppState()
        state.selected_eps = {"name": "Coosalud"}
        state.date_from = datetime(2026, 1, 1)
        state.date_to = datetime(2026, 1, 31)
        
        result = state.get_search_info()
        
        assert "Coosalud" in result
        assert "01/01/2026" in result
        assert "31/01/2026" in result
    
    def test_get_search_info_only_date_from(self):
        """Verifica formato con solo fecha desde"""
        state = AppState()
        state.selected_eps = {"name": "Mutualser"}
        state.date_from = datetime(2026, 1, 1)
        
        result = state.get_search_info()
        
        assert "Mutualser" in result
        assert "desde" in result.lower()
    
    def test_get_search_info_only_date_to(self):
        """Verifica formato con solo fecha hasta"""
        state = AppState()
        state.selected_eps = {"name": "Mutualser"}
        state.date_to = datetime(2026, 1, 31)
        
        result = state.get_search_info()
        
        assert "Mutualser" in result
        assert "hasta" in result.lower()
    
    def test_get_search_info_without_eps(self):
        """Verifica que retorne string vacío sin EPS"""
        state = AppState()
        
        result = state.get_search_info()
        
        assert result == ""
    
    def test_get_eps_filter(self):
        """Verifica que retorne el filtro en minúsculas"""
        state = AppState()
        state.selected_eps = {"filter": "COOSALUD"}
        
        result = state.get_eps_filter()
        
        assert result == "coosalud"
    
    def test_get_eps_filter_without_eps(self):
        """Verifica que retorne string vacío sin EPS"""
        state = AppState()
        
        result = state.get_eps_filter()
        
        assert result == ""
    
    def test_get_eps_filter_without_filter_key(self):
        """Verifica manejo cuando EPS no tiene 'filter'"""
        state = AppState()
        state.selected_eps = {"name": "Coosalud"}  # Sin 'filter'
        
        result = state.get_eps_filter()
        
        assert result == ""
