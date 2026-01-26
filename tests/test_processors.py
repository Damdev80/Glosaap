"""
Tests para los procesadores de archivos EPS
"""
import pytest
import pandas as pd
import os
import tempfile
from unittest.mock import Mock, patch


class TestMutualserProcessor:
    """Tests para MutualserProcessor"""
    
    def test_import_processor(self):
        """Verifica que se puede importar el procesador"""
        from app.core.mutualser_processor import MutualserProcessor
        assert MutualserProcessor is not None
    
    def test_processor_init(self):
        """Verifica la inicialización del procesador"""
        from app.core.mutualser_processor import MutualserProcessor
        
        with tempfile.TemporaryDirectory() as tmpdir:
            processor = MutualserProcessor(output_dir=tmpdir, homologacion_path=None)
            assert processor.output_dir == tmpdir
            assert processor.df_consolidado is None
    
    def test_columnas_requeridas(self):
        """Verifica que las columnas requeridas están definidas"""
        from app.core.mutualser_processor import MutualserProcessor
        
        assert hasattr(MutualserProcessor, 'COLUMNAS_REQUERIDAS')
        assert len(MutualserProcessor.COLUMNAS_REQUERIDAS) > 0
        assert 'Número de factura' in MutualserProcessor.COLUMNAS_REQUERIDAS


class TestCoosaludProcessor:
    """Tests para CoosaludProcessor"""
    
    def test_import_processor(self):
        """Verifica que se puede importar el procesador"""
        from app.service.processors.coosalud_processor import CoosaludProcessor
        assert CoosaludProcessor is not None
    
    def test_homologar_codigo_glosa_numerico(self):
        """Verifica homologación de códigos numéricos"""
        from app.service.processors.coosalud_processor import CoosaludProcessor
        processor = CoosaludProcessor()
        
        # Test casos con números
        assert processor._homologar_codigo_glosa("203") == "TA0301"
        assert processor._homologar_codigo_glosa("103") == "FA0301"
        assert processor._homologar_codigo_glosa("301") == "SO0101"
        assert processor._homologar_codigo_glosa("405") == "AU0501"
        assert processor._homologar_codigo_glosa("502") == "CO0201"
        assert processor._homologar_codigo_glosa("605") == "CL0501"
    
    def test_homologar_codigo_glosa_especial_430(self):
        """Verifica caso especial 430 -> AU2103"""
        from app.service.processors.coosalud_processor import CoosaludProcessor
        processor = CoosaludProcessor()
        
        assert processor._homologar_codigo_glosa("430") == "AU2103"
    
    def test_homologar_codigo_glosa_con_letras(self):
        """Verifica que códigos con letras no se modifican"""
        from app.service.processors.coosalud_processor import CoosaludProcessor
        processor = CoosaludProcessor()
        
        # Códigos que ya empiezan con letra no deben modificarse
        assert processor._homologar_codigo_glosa("AU01") == "AU01"
        assert processor._homologar_codigo_glosa("SO1234") == "SO1234"
        assert processor._homologar_codigo_glosa("FA01") == "FA01"
        assert processor._homologar_codigo_glosa("TA02") == "TA02"
    
    def test_homologar_codigo_glosa_vacios(self):
        """Verifica manejo de valores vacíos"""
        from app.service.processors.coosalud_processor import CoosaludProcessor
        processor = CoosaludProcessor()
        
        assert processor._homologar_codigo_glosa("") == ""
        assert processor._homologar_codigo_glosa(None) == ""
        assert processor._homologar_codigo_glosa("NAN") == ""
    
    def test_homologar_codigo_glosa_un_digito(self):
        """Verifica homologación con un solo dígito"""
        from app.service.processors.coosalud_processor import CoosaludProcessor
        processor = CoosaludProcessor()
        
        # Un solo dígito debe agregar padding
        assert processor._homologar_codigo_glosa("5") == "CO0001"
        assert processor._homologar_codigo_glosa("2") == "TA0001"
    
    def test_identify_file_pairs(self, tmp_path):
        """Verifica la identificación de pares de archivos"""
        from app.service.processors.coosalud_processor import CoosaludProcessor
        
        # Crear homologador temporal
        homolog_path = tmp_path / "homologador.xlsx"
        pd.DataFrame({
            'Código Servicio de la ERP': [],
            'Código producto en DGH': []
        }).to_excel(homolog_path, index=False)
        
        processor = CoosaludProcessor(homologador_path=str(homolog_path))
        
        # Simular lista de archivos
        files = [
            "C:/temp/DETALLE FC12345.xlsx",
            "C:/temp/GLOSAS FC12345.xlsx",
            "C:/temp/DETALLE FC12346.xlsx",
            "C:/temp/GLOSAS FC12346.xlsx",
            "C:/temp/DEVOLUCION FC99999.xlsx",  # Debe ser ignorado
        ]
        
        pairs = processor.identify_file_pairs(files)
        
        # Debe encontrar 2 pares (ignorando devolución)
        assert len(pairs) == 2
        assert all('detalle' in p and 'glosa' in p for p in pairs)


class TestImapClient:
    """Tests para ImapClient"""
    
    def test_import_client(self):
        """Verifica que se puede importar el cliente"""
        from app.core.imap_client import ImapClient
        assert ImapClient is not None
    
    def test_detect_imap_server_gmail(self):
        """Verifica detección de servidor Gmail"""
        from app.core.imap_client import ImapClient
        
        client = ImapClient()
        server = client._detect_imap_server("test@gmail.com")
        assert server == "imap.gmail.com"
    
    def test_detect_imap_server_outlook(self):
        """Verifica detección de servidor Outlook"""
        from app.core.imap_client import ImapClient
        
        client = ImapClient()
        server = client._detect_imap_server("test@outlook.com")
        assert server == "outlook.office365.com"
    
    def test_detect_imap_server_custom(self):
        """Verifica detección de servidor personalizado"""
        from app.core.imap_client import ImapClient
        
        client = ImapClient()
        server = client._detect_imap_server("test@empresa.com")
        assert server == "mail.empresa.com"


class TestSettings:
    """Tests para configuración"""
    
    def test_import_settings(self):
        """Verifica que se puede importar settings"""
        from app.config.settings import NETWORK_PATHS, IMAP_CONFIG
        assert NETWORK_PATHS is not None
        assert IMAP_CONFIG is not None
    
    def test_network_paths(self):
        """Verifica estructura de rutas de red"""
        from app.config.settings import NETWORK_PATHS
        
        assert "homologador" in NETWORK_PATHS
        assert "resultados" in NETWORK_PATHS
    
    def test_get_homologador_path(self):
        """Verifica función get_homologador_path"""
        from app.config.settings import get_homologador_path
        
        path = get_homologador_path("mutualser")
        assert "mutualser" in path.lower() or "homologador" in path.lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
