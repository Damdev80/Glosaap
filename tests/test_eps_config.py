"""
Tests para eps_config.py
Cubre: configuración de EPS
"""
import pytest
from app.config.eps_config import get_all_eps, get_eps_by_name, get_enabled_eps, get_eps_list


class TestEpsConfig:
    """Tests para configuración de EPS"""
    
    def test_get_all_eps(self):
        """Obtiene todas las EPS configuradas"""
        eps_list = get_all_eps()
        
        assert len(eps_list) > 0
        assert isinstance(eps_list, list)
    
    def test_get_eps_list(self):
        """Obtiene lista de EPS"""
        eps_list = get_eps_list()
        
        assert len(eps_list) > 0
        assert isinstance(eps_list, list)
    
    def test_get_enabled_eps(self):
        """Obtiene solo EPS habilitadas"""
        enabled = get_enabled_eps()
        
        assert isinstance(enabled, list)
        assert len(enabled) > 0
    
    def test_get_eps_by_name_coosalud(self):
        """Obtiene EPS por nombre coosalud"""
        eps = get_eps_by_name('Coosalud')
        
        assert eps is not None
        assert eps.name == 'Coosalud'
    
    def test_get_eps_by_name_mutualser(self):
        """Obtiene EPS por nombre mutualser"""
        eps = get_eps_by_name('Mutualser')
        
        assert eps is not None
        assert eps.name == 'Mutualser'
    
    def test_get_eps_by_name_invalid(self):
        """Retorna None para nombre inválido"""
        eps = get_eps_by_name('NoExiste')
        
        assert eps is None
    
    def test_get_eps_by_name_empty(self):
        """Retorna None para nombre vacío"""
        eps = get_eps_by_name('')
        
        assert eps is None
    
    def test_all_eps_return_objects(self):
        """Verifica que las EPS sean objetos"""
        all_eps = get_all_eps()
        
        for eps in all_eps:
            assert hasattr(eps, 'name')
            assert hasattr(eps, 'filter')
    
    def test_eps_names_are_unique(self):
        """Verifica que no haya nombres duplicados"""
        all_eps = get_all_eps()
        names = [eps.name for eps in all_eps]
        
        assert len(names) == len(set(names))
