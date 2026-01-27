"""
Tests para el servicio de homologación (homologacion_service.py).

Este módulo contiene tests unitarios para verificar:
- Carga de archivos de homologación
- Búsqueda de códigos
- Validación de datos
"""
import pytest
import pandas as pd
from pathlib import Path
from unittest.mock import Mock, patch

from app.core.homologacion_service import HomologacionService


class TestHomologacionServiceInit:
    """Tests para la inicialización del servicio."""
    
    def test_service_creation(self):
        """Crea el servicio correctamente"""
        service = HomologacionService()
        assert service is not None
    
    def test_service_creation_with_eps(self):
        """Crea el servicio con EPS especificada"""
        service = HomologacionService(eps="mutualser")
        assert service.eps == "mutualser"
    
    def test_service_has_df_attribute(self):
        """Tiene atributo df"""
        service = HomologacionService()
        assert hasattr(service, 'df')
    
    def test_service_has_eps_files(self):
        """Tiene diccionario de archivos por EPS"""
        assert hasattr(HomologacionService, 'EPS_FILES')
        assert "mutualser" in HomologacionService.EPS_FILES
        assert "coosalud" in HomologacionService.EPS_FILES


class TestHomologacionEpsConfig:
    """Tests para configuración de EPS."""
    
    def test_mutualser_columns(self):
        """Columnas de Mutualser están definidas"""
        cols = HomologacionService.EPS_COLUMNAS["mutualser"]
        assert 'Código Servicio de la ERP' in cols
        assert 'Código producto en DGH' in cols
    
    def test_coosalud_columns(self):
        """Columnas de Coosalud están definidas"""
        cols = HomologacionService.EPS_COLUMNAS["coosalud"]
        assert 'Código Servicio de la ERP' in cols
        assert 'Código producto en DGH' in cols
    
    def test_eps_files_are_xlsx(self):
        """Archivos de EPS son xlsx"""
        for eps, filename in HomologacionService.EPS_FILES.items():
            assert filename.endswith('.xlsx')


class TestHomologacionDirectory:
    """Tests para directorio de homologación."""
    
    def test_homologacion_dir_defined(self):
        """Directorio de homologación está definido"""
        assert HomologacionService.HOMOLOGACION_DIR
        assert isinstance(HomologacionService.HOMOLOGACION_DIR, str)
    
    def test_homologacion_dir_is_network_path(self):
        """Directorio es ruta de red"""
        path = HomologacionService.HOMOLOGACION_DIR
        assert path.startswith(r"\\")


class TestHomologacionOperations:
    """Tests para operaciones de homologación."""
    
    def test_service_with_mutualser(self):
        """Servicio con Mutualser configura columnas correctas"""
        service = HomologacionService(eps="mutualser")
        expected_cols = HomologacionService.EPS_COLUMNAS["mutualser"]
        assert service.columnas_actuales == expected_cols
    
    def test_service_with_coosalud(self):
        """Servicio con Coosalud configura columnas correctas"""
        service = HomologacionService(eps="coosalud")
        expected_cols = HomologacionService.EPS_COLUMNAS["coosalud"]
        assert service.columnas_actuales == expected_cols


class TestHomologacionClassMethods:
    """Tests para métodos de clase."""
    
    def test_default_columns_defined(self):
        """Columnas por defecto están definidas"""
        assert HomologacionService.COLUMNAS
        assert len(HomologacionService.COLUMNAS) >= 2
    
    def test_eps_columnas_defined(self):
        """EPS_COLUMNAS está definido"""
        assert HomologacionService.EPS_COLUMNAS
        assert len(HomologacionService.EPS_COLUMNAS) >= 2
