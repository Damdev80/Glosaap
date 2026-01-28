"""
Tests para el servicio de homologación (homologacion_service.py).

Este módulo contiene tests unitarios para verificar:
- Carga de archivos de homologación
- Búsqueda de códigos
- Validación de datos
- Operaciones CRUD
- Gestión de múltiples EPS
"""
import pytest
import pandas as pd
from pathlib import Path
import tempfile
import os
from unittest.mock import Mock, patch, MagicMock, mock_open

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

    @patch('app.core.homologacion_service.os.path.exists')
    @patch('app.core.homologacion_service.pd.read_excel')
    def test_get_eps_disponibles_success(self, mock_read_excel, mock_exists):
        """Test obtener EPS disponibles exitosamente"""
        # Mock directory exists
        mock_exists.side_effect = lambda path: path == HomologacionService.HOMOLOGACION_DIR or 'mutualser' in str(path)
        
        # Mock Excel reading
        mock_df = pd.DataFrame({'A': [1, 2, 3]})
        mock_read_excel.return_value = mock_df
        
        eps_list = HomologacionService.get_eps_disponibles()
        
        assert len(eps_list) > 0
        assert all('key' in eps for eps in eps_list)
        assert all('name' in eps for eps in eps_list)
        assert all('count' in eps for eps in eps_list)

    @patch('app.core.homologacion_service.os.path.exists')
    def test_get_eps_disponibles_no_directory(self, mock_exists):
        """Test cuando no existe el directorio"""
        mock_exists.return_value = False
        
        eps_list = HomologacionService.get_eps_disponibles()
        
        assert eps_list == []


class TestHomologacionServiceCRUD:
    """Tests para operaciones CRUD del servicio."""
    
    def setup_method(self):
        """Setup para cada test"""
        self.service = HomologacionService()
        
        # Datos de prueba
        self.test_data = pd.DataFrame({
            'Código Servicio de la ERP': ['100', '200', '300'],
            'Código producto en DGH': ['ABC100', 'DEF200', 'GHI300'],
            'COD_SERV_FACT': ['FACT100', 'FACT200', 'FACT300']
        })
    
    def test_listar_sin_datos(self):
        """Test listar sin datos cargados"""
        self.service.df = None
        resultado = self.service.listar()
        
        assert isinstance(resultado, pd.DataFrame)
        assert resultado.empty

    def test_listar_con_datos(self):
        """Test listar con datos"""
        self.service.df = self.test_data.copy()
        self.service.columnas_actuales = list(self.test_data.columns)
        
        resultado = self.service.listar()
        
        assert len(resultado) == 3
        assert '100' in resultado['Código Servicio de la ERP'].values

    def test_listar_con_filtro(self):
        """Test listar con filtro"""
        self.service.df = self.test_data.copy()
        self.service.columnas_actuales = list(self.test_data.columns)
        
        resultado = self.service.listar(filtro='100')
        
        assert len(resultado) == 1
        assert resultado.iloc[0]['Código Servicio de la ERP'] == '100'

    def test_listar_con_limite(self):
        """Test listar con límite"""
        self.service.df = self.test_data.copy()
        self.service.columnas_actuales = list(self.test_data.columns)
        
        resultado = self.service.listar(limite=2)
        
        assert len(resultado) <= 2

    def test_buscar_por_codigo_erp_existente(self):
        """Test buscar código ERP existente"""
        self.service.df = self.test_data.copy()
        self.service.eps = 'mutualser'  # Necesario para el caché
        
        resultado = self.service.buscar_por_codigo_erp('100')
        
        assert resultado is not None
        # El método retorna una Serie (fila), no un DataFrame
        assert resultado['Código producto en DGH'] == 'ABC100'

    def test_buscar_por_codigo_erp_inexistente(self):
        """Test buscar código ERP inexistente"""
        self.service.df = self.test_data.copy()
        
        resultado = self.service.buscar_por_codigo_erp('999')
        
        assert resultado is None or resultado.empty

    def test_buscar_por_codigo_erp_sin_datos(self):
        """Test buscar sin datos cargados"""
        self.service.df = None
        
        resultado = self.service.buscar_por_codigo_erp('100')
        
        assert resultado is None

    @patch.object(HomologacionService, '_guardar')
    def test_agregar_codigo_mutualser(self, mock_guardar):
        """Test agregar código para Mutualser (3 columnas)"""
        mock_guardar.return_value = True
        self.service.df = self.test_data.copy()
        self.service.columnas_actuales = HomologacionService.EPS_COLUMNAS['mutualser']
        
        resultado = self.service.agregar('400', 'JKL400', 'FACT400')
        
        assert resultado is True
        mock_guardar.assert_called_once()

    @patch.object(HomologacionService, '_guardar')
    def test_agregar_codigo_coosalud(self, mock_guardar):
        """Test agregar código para Coosalud (2 columnas)"""
        mock_guardar.return_value = True
        self.service.df = pd.DataFrame(columns=HomologacionService.EPS_COLUMNAS['coosalud'])
        self.service.columnas_actuales = HomologacionService.EPS_COLUMNAS['coosalud']
        
        resultado = self.service.agregar('400', 'JKL400')
        
        assert resultado is True
        mock_guardar.assert_called_once()

    @patch.object(HomologacionService, '_guardar')
    def test_agregar_codigo_duplicado(self, mock_guardar):
        """Test agregar código duplicado"""
        self.service.df = self.test_data.copy()
        
        resultado = self.service.agregar('100', 'NUEVO100', 'NEWFACT100')
        
        assert resultado is False
        mock_guardar.assert_not_called()

    @patch.object(HomologacionService, '_guardar')
    def test_actualizar_codigo_existente(self, mock_guardar):
        """Test actualizar código existente"""
        mock_guardar.return_value = True
        self.service.df = self.test_data.copy()
        self.service.columnas_actuales = HomologacionService.EPS_COLUMNAS['mutualser']
        
        resultado = self.service.actualizar('100', 'NUEVO100', 'NEWFACT100')
        
        assert resultado is True
        mock_guardar.assert_called_once()
        assert self.service.df.loc[0, 'Código producto en DGH'] == 'NUEVO100'

    @patch.object(HomologacionService, '_guardar')
    def test_actualizar_codigo_inexistente(self, mock_guardar):
        """Test actualizar código inexistente"""
        self.service.df = self.test_data.copy()
        
        resultado = self.service.actualizar('999', 'NUEVO999')
        
        assert resultado is False
        mock_guardar.assert_not_called()

    @patch.object(HomologacionService, '_guardar')
    def test_eliminar_codigo_existente(self, mock_guardar):
        """Test eliminar código existente"""
        mock_guardar.return_value = True
        self.service.df = self.test_data.copy()
        initial_length = len(self.service.df)
        
        resultado = self.service.eliminar('100')
        
        assert resultado is True
        assert len(self.service.df) == initial_length - 1
        mock_guardar.assert_called_once()

    @patch.object(HomologacionService, '_guardar')
    def test_eliminar_codigo_inexistente(self, mock_guardar):
        """Test eliminar código inexistente"""
        self.service.df = self.test_data.copy()
        
        resultado = self.service.eliminar('999')
        
        assert resultado is False
        mock_guardar.assert_not_called()


class TestHomologacionServiceFileOperations:
    """Tests para operaciones de archivos."""
    
    def setup_method(self):
        """Setup para cada test"""
        self.service = HomologacionService()
    
    @patch('app.core.homologacion_service.os.path.exists')
    @patch('app.core.homologacion_service.pd.read_excel')
    def test_cargar_archivo_exitoso(self, mock_read_excel, mock_exists):
        """Test carga exitosa de archivo"""
        mock_exists.return_value = True
        mock_df = pd.DataFrame({'A': [1, 2], 'B': [3, 4]})
        mock_read_excel.return_value = mock_df
        
        self.service.eps = 'mutualser'
        self.service.homologacion_path = 'test.xlsx'
        self.service.columnas_actuales = ['A', 'B']
        
        resultado = self.service._cargar()
        
        assert resultado is True
        assert self.service.df is not None

    @patch('app.core.homologacion_service.os.path.exists')
    def test_cargar_archivo_inexistente(self, mock_exists):
        """Test cargar archivo inexistente - crea DataFrame vacío"""
        mock_exists.return_value = False
        
        self.service.eps = 'mutualser'
        self.service.homologacion_path = 'inexistente.xlsx'
        
        resultado = self.service._cargar()
        
        # Ahora retorna True con DataFrame vacío (comportamiento correcto)
        assert resultado is True
        assert self.service.df is not None
        assert self.service.df.empty

    @patch('app.core.homologacion_service.pd.DataFrame.to_excel')
    @patch('app.core.homologacion_service.os.makedirs')
    def test_guardar_exitoso(self, mock_makedirs, mock_to_excel):
        """Test guardar archivo exitosamente"""
        self.service.df = pd.DataFrame({'A': [1], 'B': [2]})
        self.service.homologacion_path = 'test.xlsx'
        self.service.eps = 'mutualser'
        
        resultado = self.service._guardar()
        
        assert resultado is True
        mock_to_excel.assert_called_once()

    def test_cambiar_eps_valida(self):
        """Test cambiar a EPS válida"""
        with patch.object(self.service, '_cargar') as mock_cargar:
            mock_cargar.return_value = True
            
            self.service.cambiar_eps('coosalud')
            
            assert self.service.eps == 'coosalud'
            assert self.service.columnas_actuales == HomologacionService.EPS_COLUMNAS['coosalud']

    def test_cambiar_eps_invalida(self):
        """Test cambiar a EPS inválida"""
        with pytest.raises(ValueError):
            self.service.cambiar_eps('eps_inexistente')


class TestHomologacionServiceIntegration:
    """Tests de integración para el servicio."""
    
    def test_flujo_completo_con_archivo_temporal(self):
        """Test flujo completo usando archivo temporal"""
        # Limpiar caché antes del test
        HomologacionService.clear_all_cache()
        
        with tempfile.TemporaryDirectory() as temp_dir:
            # Crear archivo de prueba
            test_file = os.path.join(temp_dir, 'test_homologacion.xlsx')
            test_data = pd.DataFrame({
                'Código Servicio de la ERP': ['100', '200'],
                'Código producto en DGH': ['ABC100', 'DEF200'],
                'COD_SERV_FACT': ['FACT100', 'FACT200']
            })
            test_data.to_excel(test_file, index=False)
            
            # Probar servicio con archivo real
            service = HomologacionService()
            service.homologacion_path = test_file
            service.columnas_actuales = list(test_data.columns)
            service.eps = 'mutualser'
            
            # Cargar datos
            assert service._cargar() is True
            assert len(service.df) == 2
            
            # Buscar código - retorna Serie
            resultado = service.buscar_por_codigo_erp('100')
            assert resultado is not None
            
            # Listar con filtro
            filtrado = service.listar(filtro='100')
            assert len(filtrado) == 1
