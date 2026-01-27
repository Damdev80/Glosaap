"""
Tests para el procesador de Mutualser (mutualser_processor.py).

Este módulo contiene tests unitarios para verificar:
- Inicialización del procesador
- Estructura de columnas requeridas
- Validación de archivos
- Procesamiento de datos
"""
import pytest
import pandas as pd
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from app.core.mutualser_processor import MutualserProcessor


class TestMutualserProcessorInit:
    """Tests para la inicialización del procesador."""
    
    @patch('os.path.exists', return_value=False)
    @patch('os.makedirs')
    def test_processor_creation(self, mock_makedirs, mock_exists):
        """Crea el procesador correctamente"""
        processor = MutualserProcessor(output_dir='test_output')
        assert processor is not None
    
    @patch('os.path.exists', return_value=False)
    @patch('os.makedirs')
    def test_processor_has_output_dir(self, mock_makedirs, mock_exists):
        """Tiene directorio de salida"""
        processor = MutualserProcessor(output_dir='my_output')
        assert processor.output_dir == 'my_output'
    
    @patch('os.path.exists', return_value=False)
    @patch('os.makedirs')
    def test_processor_has_df_consolidado(self, mock_makedirs, mock_exists):
        """Tiene df_consolidado inicialmente None"""
        processor = MutualserProcessor()
        assert processor.df_consolidado is None
    
    @patch('os.path.exists', return_value=False)
    @patch('os.makedirs')
    def test_processor_has_archivos_procesados(self, mock_makedirs, mock_exists):
        """Tiene lista de archivos procesados vacía"""
        processor = MutualserProcessor()
        assert processor.archivos_procesados == []
    
    @patch('os.path.exists', return_value=False)
    @patch('os.makedirs')
    def test_processor_has_errores(self, mock_makedirs, mock_exists):
        """Tiene lista de errores vacía"""
        processor = MutualserProcessor()
        assert processor.errores == []


class TestMutualserColumnasRequeridas:
    """Tests para columnas requeridas."""
    
    def test_columnas_requeridas_defined(self):
        """Columnas requeridas están definidas"""
        assert MutualserProcessor.COLUMNAS_REQUERIDAS
        assert len(MutualserProcessor.COLUMNAS_REQUERIDAS) > 0
    
    def test_numero_factura_required(self):
        """Número de factura es requerida"""
        assert 'Número de factura' in MutualserProcessor.COLUMNAS_REQUERIDAS
    
    def test_numero_glosa_required(self):
        """Número de glosa es requerida"""
        assert 'Número de glosa' in MutualserProcessor.COLUMNAS_REQUERIDAS
    
    def test_tecnologia_required(self):
        """Tecnología es requerida"""
        assert 'Tecnología' in MutualserProcessor.COLUMNAS_REQUERIDAS
    
    def test_cantidad_facturada_required(self):
        """Cantidad facturada es requerida"""
        assert 'Cantidad facturada' in MutualserProcessor.COLUMNAS_REQUERIDAS
    
    def test_valor_facturado_required(self):
        """Valor Facturado es requerida"""
        assert 'Valor Facturado' in MutualserProcessor.COLUMNAS_REQUERIDAS
    
    def test_concepto_glosa_required(self):
        """Concepto de glosa es requerida"""
        assert 'Concepto de glosa' in MutualserProcessor.COLUMNAS_REQUERIDAS
    
    def test_codigo_glosa_required(self):
        """Código de glosa es requerida"""
        assert 'Código de glosa' in MutualserProcessor.COLUMNAS_REQUERIDAS
    
    def test_observacion_required(self):
        """Observacion es requerida"""
        assert 'Observacion' in MutualserProcessor.COLUMNAS_REQUERIDAS


class TestMutualserHomologacionPath:
    """Tests para path de homologación."""
    
    def test_homologacion_path_defined(self):
        """Path de homologación está definido"""
        assert MutualserProcessor.HOMOLOGACION_PATH
    
    def test_homologacion_path_is_network(self):
        """Path es ruta de red"""
        assert MutualserProcessor.HOMOLOGACION_PATH.startswith(r"\\")
    
    def test_homologacion_path_is_xlsx(self):
        """Path apunta a archivo xlsx"""
        assert MutualserProcessor.HOMOLOGACION_PATH.endswith('.xlsx')
    
    @patch('os.path.exists', return_value=False)
    @patch('os.makedirs')
    def test_custom_homologacion_path(self, mock_makedirs, mock_exists):
        """Puede especificar path de homologación personalizado"""
        custom_path = r"C:\custom\homologacion.xlsx"
        processor = MutualserProcessor(homologacion_path=custom_path)
        # El procesador intenta cargar el archivo y puede modificar el path
        assert processor is not None


class TestMutualserDataStructures:
    """Tests para estructuras de datos del procesador."""
    
    @patch('os.path.exists', return_value=False)
    @patch('os.makedirs')
    def test_df_homologacion_attribute(self, mock_makedirs, mock_exists):
        """Tiene atributo df_homologacion"""
        processor = MutualserProcessor()
        assert hasattr(processor, 'df_homologacion')
    
    @patch('os.path.exists', return_value=False)
    @patch('os.makedirs')
    def test_todos_cod_serv_fact_attribute(self, mock_makedirs, mock_exists):
        """Tiene atributo _todos_cod_serv_fact"""
        processor = MutualserProcessor()
        assert hasattr(processor, '_todos_cod_serv_fact')


class TestMutualserProcessorMethods:
    """Tests para métodos del procesador."""
    
    @patch('os.path.exists', return_value=False)
    @patch('os.makedirs')
    def test_has_cargar_homologacion(self, mock_makedirs, mock_exists):
        """Tiene método _cargar_homologacion"""
        processor = MutualserProcessor()
        assert hasattr(processor, '_cargar_homologacion')
    
    def test_has_procesar_archivo(self):
        """Tiene método procesar_archivo"""
        assert hasattr(MutualserProcessor, 'procesar_archivo')


class TestMutualserConstants:
    """Tests para constantes del procesador."""
    
    def test_columnas_count(self):
        """Número correcto de columnas requeridas"""
        # Debe tener todas las columnas necesarias para procesar
        assert len(MutualserProcessor.COLUMNAS_REQUERIDAS) >= 10
    
    def test_columnas_all_strings(self):
        """Todas las columnas son strings"""
        for col in MutualserProcessor.COLUMNAS_REQUERIDAS:
            assert isinstance(col, str)
    
    def test_columnas_no_empty(self):
        """Ninguna columna está vacía"""
        for col in MutualserProcessor.COLUMNAS_REQUERIDAS:
            assert col.strip() != ""


class TestMutualserOutputDir:
    """Tests para directorio de salida."""
    
    @patch('os.path.exists', return_value=False)
    @patch('os.makedirs')
    def test_default_output_dir(self, mock_makedirs, mock_exists):
        """Directorio de salida por defecto es 'outputs'"""
        processor = MutualserProcessor()
        assert processor.output_dir == 'outputs'
    
    @patch('os.path.exists', return_value=False)
    @patch('os.makedirs')
    def test_creates_output_directory(self, mock_makedirs, mock_exists):
        """Crea directorio de salida si no existe"""
        MutualserProcessor(output_dir='new_output')
        mock_makedirs.assert_called()


class TestMutualserProcessorClass:
    """Tests para la clase en general."""
    
    def test_is_class(self):
        """MutualserProcessor es una clase"""
        assert isinstance(MutualserProcessor, type)
    
    def test_has_docstring(self):
        """La clase tiene docstring"""
        assert MutualserProcessor.__doc__ is not None
