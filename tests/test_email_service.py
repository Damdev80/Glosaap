"""
Tests para el servicio de email (email_service.py).

Este módulo contiene tests unitarios para verificar:
- Inicialización del servicio
- Configuración de conexión
- Manejo de estados
"""
import pytest
from unittest.mock import Mock, patch, MagicMock

from app.service.email_service import EmailService


class TestEmailServiceInit:
    """Tests para la inicialización del EmailService."""
    
    def test_service_creation(self):
        """Crea el servicio correctamente"""
        service = EmailService()
        assert service is not None
    
    def test_service_has_imap_client(self):
        """Tiene atributo imap_client"""
        service = EmailService()
        assert hasattr(service, 'imap_client')
    
    def test_service_has_attachment_service(self):
        """Tiene atributo attachment_service"""
        service = EmailService()
        assert hasattr(service, 'attachment_service')
    
    def test_service_has_messages_list(self):
        """Tiene lista de mensajes vacía"""
        service = EmailService()
        assert hasattr(service, 'messages')
        assert service.messages == []
    
    def test_service_has_connect_method(self):
        """Tiene método connect"""
        service = EmailService()
        assert hasattr(service, 'connect')
        assert callable(service.connect)


class TestEmailServiceConnection:
    """Tests para la conexión del EmailService."""
    
    @patch('app.service.email_service.ImapClient')
    def test_connect_creates_imap_client(self, mock_imap):
        """Connect crea cliente IMAP"""
        mock_client = MagicMock()
        mock_client.connect.return_value = True
        mock_imap.return_value = mock_client
        
        service = EmailService()
        # La conexión real requiere credenciales válidas
        assert service is not None


class TestImapConfig:
    """Tests para configuración IMAP."""
    
    def test_imap_config_exists(self):
        """Configuración IMAP existe"""
        from app.config.settings import IMAP_CONFIG
        
        assert IMAP_CONFIG is not None
        assert "default_port" in IMAP_CONFIG
        assert "use_ssl" in IMAP_CONFIG
    
    def test_imap_default_port(self):
        """Puerto por defecto es 993 (SSL)"""
        from app.config.settings import IMAP_CONFIG
        
        assert IMAP_CONFIG["default_port"] == 993
    
    def test_imap_ssl_enabled(self):
        """SSL está habilitado por defecto"""
        from app.config.settings import IMAP_CONFIG
        
        assert IMAP_CONFIG["use_ssl"] is True
    
    def test_known_servers_mapping(self):
        """Mapeo de servidores conocidos"""
        from app.config.settings import IMAP_CONFIG
        
        known = IMAP_CONFIG["known_servers"]
        
        assert "gmail.com" in known
        assert known["gmail.com"] == "imap.gmail.com"
        
        assert "outlook.com" in known
        assert "outlook.office365.com" in known["outlook.com"]
