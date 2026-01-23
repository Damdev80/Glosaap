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
    
    def test_identify_file_pairs(self):
        """Verifica la identificación de pares de archivos"""
        from app.service.processors.coosalud_processor import CoosaludProcessor
        
        processor = CoosaludProcessor()
        
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
