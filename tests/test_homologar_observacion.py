"""
Tests para HomologadorObservacion (homologar_observacion.py).

Este módulo contiene tests unitarios para verificar:
- Inicialización del homologador
- Carga de archivo de homologación
- Búsqueda de códigos homologados
"""
import pytest
import pandas as pd
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from app.core.homologar_observacion import HomologadorObservacion


class TestHomologadorObservacionInit:
    """Tests para la inicialización del homologador."""
    
    @patch('os.path.exists', return_value=False)
    def test_homologador_creation(self, mock_exists):
        """Crea el homologador correctamente"""
        homologador = HomologadorObservacion()
        assert homologador is not None
    
    @patch('os.path.exists', return_value=False)
    def test_homologador_has_homologacion_path(self, mock_exists):
        """Tiene ruta de homologación"""
        homologador = HomologadorObservacion()
        assert homologador.homologacion_path is not None
    
    @patch('os.path.exists', return_value=False)
    def test_homologador_has_df_homologacion(self, mock_exists):
        """Tiene atributo df_homologacion"""
        homologador = HomologadorObservacion()
        assert hasattr(homologador, 'df_homologacion')
    
    @patch('os.path.exists', return_value=False)
    def test_homologador_has_todos_cod_serv_fact(self, mock_exists):
        """Tiene conjunto de códigos de servicio"""
        homologador = HomologadorObservacion()
        assert hasattr(homologador, 'todos_cod_serv_fact')
        assert isinstance(homologador.todos_cod_serv_fact, set)


class TestHomologadorObservacionDefaultPath:
    """Tests para ruta por defecto."""
    
    @patch('os.path.exists', return_value=False)
    def test_default_path_is_network(self, mock_exists):
        """Ruta por defecto es de red"""
        homologador = HomologadorObservacion()
        assert homologador.homologacion_path.startswith(r"\\")
    
    @patch('os.path.exists', return_value=False)
    def test_default_path_is_xlsx(self, mock_exists):
        """Ruta por defecto es xlsx"""
        homologador = HomologadorObservacion()
        assert homologador.homologacion_path.endswith('.xlsx')
    
    @patch('os.path.exists', return_value=False)
    def test_custom_path(self, mock_exists):
        """Puede especificar ruta personalizada"""
        custom_path = r"C:\custom\homologador.xlsx"
        homologador = HomologadorObservacion(homologacion_path=custom_path)
        assert homologador.homologacion_path == custom_path


class TestHomologadorObservacionCargarHomologacion:
    """Tests para carga de archivo de homologación."""
    
    @patch('os.path.exists', return_value=False)
    def test_cargar_homologacion_file_not_found(self, mock_exists):
        """Maneja archivo no encontrado"""
        homologador = HomologadorObservacion()
        # No debería lanzar excepción
        assert homologador.df_homologacion is None
    
    def test_cargar_homologacion_success(self, tmp_path):
        """Carga archivo exitosamente"""
        # Crear archivo de prueba
        file_path = tmp_path / "homologador.xlsx"
        df = pd.DataFrame({
            'Código Servicio de la ERP': ['SRV001', 'SRV002'],
            'Código producto en DGH': ['DGH001', 'DGH002'],
            'COD_SERV_FACT': ['FACT001', 'FACT002']
        })
        df.to_excel(file_path, index=False)
        
        homologador = HomologadorObservacion(homologacion_path=str(file_path))
        
        assert homologador.df_homologacion is not None
        assert len(homologador.df_homologacion) == 2


class TestHomologadorObservacionBuscarCodigo:
    """Tests para búsqueda de códigos homologados."""
    
    @patch('os.path.exists', return_value=False)
    def test_buscar_codigo_without_df_returns_empty(self, mock_exists):
        """Sin df_homologacion retorna vacío"""
        homologador = HomologadorObservacion()
        
        result = homologador._buscar_codigo_homologado('SRV001')
        
        assert result == ''
    
    @patch('os.path.exists', return_value=False)
    def test_buscar_codigo_with_nan_returns_empty(self, mock_exists):
        """Con NaN retorna vacío"""
        homologador = HomologadorObservacion()
        
        result = homologador._buscar_codigo_homologado(pd.NA)
        
        assert result == ''
    
    def test_buscar_codigo_empty_string_returns_empty(self, tmp_path):
        """Con string vacío retorna vacío"""
        file_path = tmp_path / "homologador.xlsx"
        df = pd.DataFrame({
            'Código Servicio de la ERP': ['SRV001'],
            'Código producto en DGH': ['DGH001'],
            'COD_SERV_FACT': ['FACT001']
        })
        df.to_excel(file_path, index=False)
        
        homologador = HomologadorObservacion(homologacion_path=str(file_path))
        result = homologador._buscar_codigo_homologado('')
        
        assert result == ''


class TestHomologadorObservacionMethods:
    """Tests para métodos del homologador."""
    
    def test_has_cargar_homologacion(self):
        """Tiene método _cargar_homologacion"""
        assert hasattr(HomologadorObservacion, '_cargar_homologacion')
    
    def test_has_buscar_codigo_homologado(self):
        """Tiene método _buscar_codigo_homologado"""
        assert hasattr(HomologadorObservacion, '_buscar_codigo_homologado')


class TestHomologadorObservacionClass:
    """Tests para la clase en general."""
    
    def test_is_class(self):
        """HomologadorObservacion es una clase"""
        assert isinstance(HomologadorObservacion, type)
    
    def test_has_docstring(self):
        """La clase tiene docstring"""
        assert HomologadorObservacion.__doc__ is not None


class TestHomologadorObservacionConjunto:
    """Tests para conjunto de códigos."""
    
    def test_todos_cod_serv_fact_initially_empty(self):
        """Conjunto inicialmente vacío sin archivo"""
        with patch('os.path.exists', return_value=False):
            homologador = HomologadorObservacion()
            assert homologador.todos_cod_serv_fact == set()
    
    def test_todos_cod_serv_fact_populated(self, tmp_path):
        """Conjunto se puebla con archivo"""
        file_path = tmp_path / "homologador.xlsx"
        df = pd.DataFrame({
            'Código Servicio de la ERP': ['SRV001', 'SRV002'],
            'Código producto en DGH': ['DGH001', 'DGH002'],
            'COD_SERV_FACT': ['FACT001', 'FACT002']
        })
        df.to_excel(file_path, index=False)
        
        homologador = HomologadorObservacion(homologacion_path=str(file_path))
        
        assert 'FACT001' in homologador.todos_cod_serv_fact
        assert 'FACT002' in homologador.todos_cod_serv_fact
