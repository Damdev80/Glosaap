"""
Tests para el servicio Mix Excel (mix_excel_service.py).

Este módulo contiene tests unitarios para verificar:
- Inicialización del servicio
- Carga de archivos Excel
- Transferencia de datos
"""
import pytest
import pandas as pd
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from app.core.mix_excel_service import MixExcelService


class TestMixExcelServiceInit:
    """Tests para la inicialización del servicio."""
    
    def test_service_creation(self):
        """Crea el servicio correctamente"""
        service = MixExcelService()
        assert service is not None
    
    def test_source_df_initially_none(self):
        """source_df es None inicialmente"""
        service = MixExcelService()
        assert service.source_df is None
    
    def test_dest_df_initially_none(self):
        """dest_df es None inicialmente"""
        service = MixExcelService()
        assert service.dest_df is None
    
    def test_source_file_initially_none(self):
        """source_file es None inicialmente"""
        service = MixExcelService()
        assert service.source_file is None
    
    def test_dest_file_initially_none(self):
        """dest_file es None inicialmente"""
        service = MixExcelService()
        assert service.dest_file is None


class TestMixExcelServiceLoadFile:
    """Tests para carga de archivos."""
    
    def test_cargar_source_file(self, tmp_path):
        """Carga archivo fuente"""
        # Crear archivo Excel de prueba
        file_path = tmp_path / "source.xlsx"
        df = pd.DataFrame({
            'columna1': [1, 2, 3],
            'columna2': ['a', 'b', 'c']
        })
        df.to_excel(file_path, index=False)
        
        service = MixExcelService()
        success, columns, message = service.cargar_archivo(str(file_path), "source")
        
        assert success is True
        assert 'columna1' in columns
        assert 'columna2' in columns
    
    def test_cargar_dest_file(self, tmp_path):
        """Carga archivo destino"""
        file_path = tmp_path / "dest.xlsx"
        df = pd.DataFrame({
            'col_a': [10, 20],
            'col_b': [100, 200]
        })
        df.to_excel(file_path, index=False)
        
        service = MixExcelService()
        success, columns, message = service.cargar_archivo(str(file_path), "dest")
        
        assert success is True
        assert service.dest_df is not None
        assert service.dest_file == str(file_path)
    
    def test_cargar_archivo_nonexistent(self):
        """Error al cargar archivo inexistente"""
        service = MixExcelService()
        success, columns, message = service.cargar_archivo("/no/existe.xlsx", "source")
        
        assert success is False
        assert columns == []
        assert "Error" in message
    
    def test_cargar_archivo_returns_row_count(self, tmp_path):
        """Mensaje incluye número de filas"""
        file_path = tmp_path / "test.xlsx"
        df = pd.DataFrame({'col': range(10)})
        df.to_excel(file_path, index=False)
        
        service = MixExcelService()
        success, columns, message = service.cargar_archivo(str(file_path), "source")
        
        assert "10 filas" in message


class TestMixExcelServiceTransfer:
    """Tests para transferencia de datos."""
    
    def test_transferir_without_files_fails(self):
        """transferir_datos falla sin archivos cargados"""
        service = MixExcelService()
        
        success, matches, message = service.transferir_datos(
            "col1", "ref1", "col2", "ref2", "adj"
        )
        
        assert success is False
        assert "Carga ambos archivos" in message
    
    def test_transferir_with_source_only_fails(self, tmp_path):
        """transferir_datos falla con solo archivo fuente"""
        file_path = tmp_path / "source.xlsx"
        pd.DataFrame({'col': [1]}).to_excel(file_path, index=False)
        
        service = MixExcelService()
        service.cargar_archivo(str(file_path), "source")
        
        success, matches, message = service.transferir_datos(
            "col", "col", "col", "col", "col"
        )
        
        assert success is False


class TestMixExcelServiceMethods:
    """Tests para métodos del servicio."""
    
    def test_has_cargar_archivo(self):
        """Tiene método cargar_archivo"""
        assert hasattr(MixExcelService, 'cargar_archivo')
    
    def test_has_transferir_datos(self):
        """Tiene método transferir_datos"""
        assert hasattr(MixExcelService, 'transferir_datos')


class TestMixExcelServiceClass:
    """Tests para la clase en general."""
    
    def test_is_class(self):
        """MixExcelService es una clase"""
        assert isinstance(MixExcelService, type)
    
    def test_has_docstring(self):
        """La clase tiene docstring"""
        assert MixExcelService.__doc__ is not None


class TestMixExcelServiceDataTypes:
    """Tests para tipos de datos."""
    
    def test_cargar_archivo_returns_tuple(self, tmp_path):
        """cargar_archivo retorna tupla"""
        file_path = tmp_path / "test.xlsx"
        pd.DataFrame({'col': [1]}).to_excel(file_path, index=False)
        
        service = MixExcelService()
        result = service.cargar_archivo(str(file_path), "source")
        
        assert isinstance(result, tuple)
        assert len(result) == 3
    
    def test_transferir_datos_returns_tuple(self):
        """transferir_datos retorna tupla"""
        service = MixExcelService()
        result = service.transferir_datos(
            "col1", "ref1", "col2", "ref2", "adj"
        )
        
        assert isinstance(result, tuple)
        assert len(result) == 3


class TestMixExcelServiceTolerance:
    """Tests para tolerancia en comparaciones."""
    
    def test_default_tolerance(self):
        """Tolerancia por defecto es 0.05 (5%)"""
        import inspect
        sig = inspect.signature(MixExcelService.transferir_datos)
        params = sig.parameters
        
        assert 'tolerance' in params
        assert params['tolerance'].default == 0.05
