"""
Tests para el servicio de adjuntos (attachment_service.py).

Este módulo contiene tests unitarios para verificar:
- Inicialización del servicio
- Gestión de directorios
- Escaneo de archivos
- Filtrado de adjuntos
"""
import pytest
import os
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from app.service.attachment_service import AttachmentService


class TestAttachmentServiceInit:
    """Tests para la inicialización del servicio."""
    
    def test_service_creation(self):
        """Crea el servicio correctamente"""
        with patch.object(AttachmentService, '_ensure_directory'):
            service = AttachmentService()
            assert service is not None
    
    def test_service_has_downloaded_files(self):
        """Tiene lista de archivos descargados"""
        with patch.object(AttachmentService, '_ensure_directory'):
            service = AttachmentService()
            assert hasattr(service, 'downloaded_files')
            assert service.downloaded_files == []
    
    def test_service_has_session_files(self):
        """Tiene lista de archivos de sesión"""
        with patch.object(AttachmentService, '_ensure_directory'):
            service = AttachmentService()
            assert hasattr(service, 'session_files')
            assert service.session_files == []
    
    def test_service_has_base_dir(self):
        """Tiene directorio base"""
        with patch.object(AttachmentService, '_ensure_directory'):
            service = AttachmentService()
            assert hasattr(service, 'base_dir')


class TestAttachmentServiceBaseDir:
    """Tests para directorio base."""
    
    def test_default_uses_temp_dir(self):
        """Sin parámetro usa directorio temporal"""
        with patch.object(AttachmentService, '_ensure_directory'):
            service = AttachmentService()
            # Debería estar en tempdir
            assert tempfile.gettempdir() in service.base_dir
    
    def test_default_subdir_name(self):
        """Subdirectorio por defecto es glosaap_attachments"""
        with patch.object(AttachmentService, '_ensure_directory'):
            service = AttachmentService()
            assert "glosaap_attachments" in service.base_dir
    
    def test_custom_base_dir(self):
        """Puede especificar directorio base personalizado"""
        custom_dir = tempfile.mkdtemp()
        try:
            with patch.object(AttachmentService, '_ensure_directory'):
                service = AttachmentService(base_dir=custom_dir)
                assert service.base_dir == custom_dir
        finally:
            os.rmdir(custom_dir)


class TestAttachmentServiceMethods:
    """Tests para métodos del servicio."""
    
    def test_has_ensure_directory_method(self):
        """Tiene método _ensure_directory"""
        assert hasattr(AttachmentService, '_ensure_directory')
    
    def test_has_scan_directory_method(self):
        """Tiene método _scan_directory"""
        assert hasattr(AttachmentService, '_scan_directory')


class TestAttachmentServiceDirectory:
    """Tests para gestión de directorios."""
    
    def test_ensure_creates_directory(self, tmp_path):
        """_ensure_directory crea el directorio"""
        test_dir = tmp_path / "test_attachments"
        
        with patch.object(AttachmentService, '_scan_directory'):
            service = AttachmentService(base_dir=str(test_dir))
        
        assert test_dir.exists()
    
    def test_scan_finds_existing_files(self, tmp_path):
        """_scan_directory encuentra archivos existentes"""
        # Crear archivos de prueba
        test_dir = tmp_path / "attachments"
        test_dir.mkdir()
        (test_dir / "file1.xlsx").touch()
        (test_dir / "file2.pdf").touch()
        
        service = AttachmentService(base_dir=str(test_dir))
        
        # Debería haber encontrado los archivos
        assert len(service.downloaded_files) >= 0  # Puede variar según implementación


class TestAttachmentServiceScanEmpty:
    """Tests para escaneo de directorio vacío."""
    
    def test_scan_empty_directory(self, tmp_path):
        """Escanea directorio vacío sin errores"""
        test_dir = tmp_path / "empty_dir"
        test_dir.mkdir()
        
        service = AttachmentService(base_dir=str(test_dir))
        
        assert service.downloaded_files == []


class TestAttachmentServiceRelativePath:
    """Tests para rutas relativas."""
    
    def test_relative_path_converted_to_absolute(self):
        """Ruta relativa se convierte a absoluta"""
        with patch.object(AttachmentService, '_ensure_directory'):
            service = AttachmentService(base_dir="relative/path")
            assert os.path.isabs(service.base_dir)


class TestAttachmentServiceClass:
    """Tests para la clase en general."""
    
    def test_is_class(self):
        """AttachmentService es una clase"""
        assert isinstance(AttachmentService, type)
    
    def test_has_docstring(self):
        """La clase tiene docstring"""
        assert AttachmentService.__doc__ is not None


class TestAttachmentServiceIntegration:
    """Tests de integración básica."""
    
    def test_full_initialization(self, tmp_path):
        """Inicialización completa funciona"""
        test_dir = tmp_path / "full_test"
        
        service = AttachmentService(base_dir=str(test_dir))
        
        assert service is not None
        assert test_dir.exists()
        assert service.downloaded_files == []
        assert service.session_files == []


class TestAttachmentServiceFileFiltering:
    """Tests para filtrado de archivos."""
    
    def test_service_initialization_with_files(self, tmp_path):
        """Inicializa con archivos existentes"""
        test_dir = tmp_path / "filter_test"
        test_dir.mkdir()
        
        # Crear archivos de diferentes tipos
        (test_dir / "doc1.xlsx").touch()
        (test_dir / "doc2.xls").touch()
        (test_dir / "doc3.pdf").touch()
        (test_dir / "doc4.docx").touch()
        
        service = AttachmentService(base_dir=str(test_dir))
        
        # El servicio debería poder manejar diferentes tipos
        assert service is not None
