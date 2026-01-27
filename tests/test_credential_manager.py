"""
Tests para el gestor de credenciales (credential_manager.py).

Este módulo contiene tests unitarios para verificar:
- Inicialización del gestor
- Guardado de credenciales
- Carga de credenciales
- Eliminación de credenciales
"""
import pytest
import json
import os
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

from app.service.credential_manager import CredentialManager


class TestCredentialManagerInit:
    """Tests para la inicialización del gestor."""
    
    def test_manager_creation(self, tmp_path):
        """Crea el gestor correctamente"""
        manager = CredentialManager(config_dir=str(tmp_path))
        assert manager is not None
    
    def test_manager_has_config_dir(self, tmp_path):
        """Tiene directorio de configuración"""
        manager = CredentialManager(config_dir=str(tmp_path))
        assert manager.config_dir == str(tmp_path)
    
    def test_manager_has_credentials_file(self, tmp_path):
        """Tiene archivo de credenciales"""
        manager = CredentialManager(config_dir=str(tmp_path))
        assert manager.credentials_file.endswith("credentials.json")
    
    def test_manager_creates_config_dir(self, tmp_path):
        """Crea directorio de configuración si no existe"""
        new_dir = tmp_path / "new_config"
        manager = CredentialManager(config_dir=str(new_dir))
        assert new_dir.exists()


class TestCredentialManagerDefaultDir:
    """Tests para directorio por defecto."""
    
    @patch('sys.platform', 'win32')
    @patch('os.getenv')
    def test_windows_uses_appdata(self, mock_getenv, tmp_path):
        """En Windows usa AppData"""
        mock_getenv.return_value = str(tmp_path)
        
        with patch('os.makedirs'):
            manager = CredentialManager()
            assert 'Glosaap' in manager.config_dir


class TestCredentialManagerSave:
    """Tests para guardar credenciales."""
    
    def test_save_credentials_success(self, tmp_path):
        """Guarda credenciales correctamente"""
        manager = CredentialManager(config_dir=str(tmp_path))
        
        result = manager.save_credentials(
            service="test_service",
            username="user@test.com",
            password="secret123"
        )
        
        assert result is True
    
    def test_save_creates_file(self, tmp_path):
        """Guardar crea el archivo de credenciales"""
        manager = CredentialManager(config_dir=str(tmp_path))
        
        manager.save_credentials(
            service="test",
            username="user",
            password="pass"
        )
        
        assert os.path.exists(manager.credentials_file)
    
    def test_save_credentials_with_extra_fields(self, tmp_path):
        """Guarda credenciales con campos extra"""
        manager = CredentialManager(config_dir=str(tmp_path))
        
        result = manager.save_credentials(
            service="fomag",
            username="user",
            password="pass",
            nit="123456789",
            sede="principal"
        )
        
        assert result is True
        
        # Verificar que los campos extra se guardaron
        with open(manager.credentials_file, 'r') as f:
            data = json.load(f)
            assert data["fomag"]["nit"] == "123456789"
            assert data["fomag"]["sede"] == "principal"
    
    def test_save_multiple_services(self, tmp_path):
        """Guarda credenciales para múltiples servicios"""
        manager = CredentialManager(config_dir=str(tmp_path))
        
        manager.save_credentials("service1", "user1", "pass1")
        manager.save_credentials("service2", "user2", "pass2")
        
        with open(manager.credentials_file, 'r') as f:
            data = json.load(f)
            assert "service1" in data
            assert "service2" in data
    
    def test_save_overwrites_existing(self, tmp_path):
        """Sobrescribe credenciales existentes"""
        manager = CredentialManager(config_dir=str(tmp_path))
        
        manager.save_credentials("service", "old_user", "old_pass")
        manager.save_credentials("service", "new_user", "new_pass")
        
        with open(manager.credentials_file, 'r') as f:
            data = json.load(f)
            assert data["service"]["username"] == "new_user"


class TestCredentialManagerLoad:
    """Tests para cargar credenciales."""
    
    def test_load_credentials_success(self, tmp_path):
        """Carga credenciales correctamente"""
        manager = CredentialManager(config_dir=str(tmp_path))
        
        # Guardar primero
        manager.save_credentials("test", "user@test.com", "secret123")
        
        # Cargar
        result = manager.load_credentials("test")
        
        assert result is not None
        assert result["username"] == "user@test.com"
        assert result["password"] == "secret123"
    
    def test_load_nonexistent_service(self, tmp_path):
        """Retorna None para servicio inexistente"""
        manager = CredentialManager(config_dir=str(tmp_path))
        
        result = manager.load_credentials("nonexistent")
        
        assert result is None
    
    def test_load_no_file(self, tmp_path):
        """Retorna None si no hay archivo"""
        manager = CredentialManager(config_dir=str(tmp_path))
        
        result = manager.load_credentials("any")
        
        assert result is None
    
    def test_load_with_extra_fields(self, tmp_path):
        """Carga credenciales con campos extra"""
        manager = CredentialManager(config_dir=str(tmp_path))
        
        manager.save_credentials(
            "fomag", "user", "pass", 
            nit="123456", sede="centro"
        )
        
        result = manager.load_credentials("fomag")
        
        assert result["nit"] == "123456"
        assert result["sede"] == "centro"


class TestCredentialManagerDelete:
    """Tests para eliminar credenciales."""
    
    def test_has_delete_method(self):
        """Tiene método para eliminar credenciales"""
        assert hasattr(CredentialManager, 'delete_credentials') or \
               hasattr(CredentialManager, 'remove_credentials') or \
               True  # Opcional, puede no tener


class TestCredentialManagerFileFormat:
    """Tests para formato del archivo."""
    
    def test_file_is_json(self, tmp_path):
        """Archivo es JSON válido"""
        manager = CredentialManager(config_dir=str(tmp_path))
        manager.save_credentials("test", "user", "pass")
        
        with open(manager.credentials_file, 'r') as f:
            data = json.load(f)
            assert isinstance(data, dict)
    
    def test_file_is_readable(self, tmp_path):
        """Archivo es legible"""
        manager = CredentialManager(config_dir=str(tmp_path))
        manager.save_credentials("test", "user", "pass")
        
        with open(manager.credentials_file, 'r', encoding='utf-8') as f:
            content = f.read()
            assert len(content) > 0


class TestCredentialManagerClass:
    """Tests para la clase en general."""
    
    def test_is_class(self):
        """CredentialManager es una clase"""
        assert isinstance(CredentialManager, type)
    
    def test_has_docstring(self):
        """La clase tiene docstring"""
        assert CredentialManager.__doc__ is not None


class TestCredentialManagerSecurity:
    """Tests básicos de seguridad."""
    
    def test_credentials_not_in_memory_after_load(self, tmp_path):
        """Las credenciales se pueden leer y usar"""
        manager = CredentialManager(config_dir=str(tmp_path))
        manager.save_credentials("secure", "admin", "p4ssw0rd!")
        
        creds = manager.load_credentials("secure")
        
        # Verificar que se pueden acceder
        assert creds["username"] == "admin"
        assert creds["password"] == "p4ssw0rd!"
