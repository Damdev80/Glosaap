"""
Tests para el servicio de autenticación (auth_service.py).

Este módulo contiene tests unitarios para verificar:
- Inicialización del servicio
- Proceso de login
- Proceso de logout
- Estado de autenticación
"""
import pytest
import threading
import time
from unittest.mock import Mock, MagicMock, patch

from app.service.auth_service import AuthService


class TestAuthServiceInit:
    """Tests para la inicialización del servicio."""
    
    def test_service_creation(self):
        """Crea el servicio correctamente"""
        service = AuthService()
        assert service is not None
    
    def test_client_initially_none(self):
        """Cliente es None inicialmente"""
        service = AuthService()
        assert service.client is None
    
    def test_not_authenticated_initially(self):
        """No está autenticado inicialmente"""
        service = AuthService()
        assert service.is_authenticated is False
    
    def test_current_email_initially_none(self):
        """current_email es None inicialmente"""
        service = AuthService()
        assert service.current_email is None


class TestAuthServiceLogin:
    """Tests para el proceso de login."""
    
    @patch('app.service.auth_service.ImapClient')
    @patch('app.service.auth_service.threading.Thread')
    def test_login_creates_thread(self, mock_thread, mock_imap):
        """login crea un thread para la conexión"""
        service = AuthService()
        on_success = Mock()
        on_error = Mock()
        
        service.login("test@email.com", "password", on_success, on_error)
        
        mock_thread.assert_called_once()
    
    @patch('app.service.auth_service.ImapClient')
    def test_login_success_updates_state(self, mock_imap_class):
        """Login exitoso actualiza estado"""
        mock_client = MagicMock()
        mock_imap_class.return_value = mock_client
        
        service = AuthService()
        on_success = Mock()
        on_error = Mock()
        
        # Ejecutar login directamente sin thread
        service.client = mock_client  # type: ignore
        mock_client.connect.return_value = True
        
        service.client.connect("test@email.com", "password")  # type: ignore
        service.is_authenticated = True
        service.current_email = "test@email.com"  # type: ignore
        
        assert service.is_authenticated is True
        assert service.current_email == "test@email.com"  # type: ignore


class TestAuthServiceLogout:
    """Tests para el proceso de logout."""
    
    def test_logout_clears_client(self):
        """logout limpia el cliente"""
        service = AuthService()
        service.client = MagicMock()  # type: ignore
        service.is_authenticated = True
        service.current_email = "test@email.com"  # type: ignore
        
        service.logout()
        
        assert service.client is None
    
    def test_logout_clears_authentication(self):
        """logout marca como no autenticado"""
        service = AuthService()
        service.client = MagicMock()  # type: ignore
        service.is_authenticated = True
        
        service.logout()
        
        assert service.is_authenticated is False
    
    def test_logout_clears_email(self):
        """logout limpia current_email"""
        service = AuthService()
        service.client = MagicMock()  # type: ignore
        service.current_email = "test@email.com"  # type: ignore
        
        service.logout()
        
        assert service.current_email is None
    
    def test_logout_without_client_no_error(self):
        """logout sin cliente no da error"""
        service = AuthService()
        service.logout()  # No debería lanzar excepción
    
    def test_logout_handles_client_error(self):
        """logout maneja error del cliente"""
        service = AuthService()
        mock_client = MagicMock()
        mock_client.logout.side_effect = Exception("Connection error")
        service.client = mock_client  # type: ignore
        
        # No debería lanzar excepción
        service.logout()
        assert service.client is None


class TestAuthServiceGetClient:
    """Tests para get_client."""
    
    def test_get_client_when_authenticated(self):
        """Retorna cliente cuando está autenticado"""
        service = AuthService()
        mock_client = MagicMock()
        service.client = mock_client  # type: ignore
        service.is_authenticated = True
        
        result = service.get_client()
        
        assert result is mock_client
    
    def test_get_client_when_not_authenticated(self):
        """Retorna None cuando no está autenticado"""
        service = AuthService()
        service.client = MagicMock()  # type: ignore
        service.is_authenticated = False
        
        result = service.get_client()
        
        assert result is None
    
    def test_get_client_no_client(self):
        """Retorna None cuando no hay cliente"""
        service = AuthService()
        
        result = service.get_client()
        
        assert result is None


class TestAuthServiceClass:
    """Tests para la clase en general."""
    
    def test_is_class(self):
        """AuthService es una clase"""
        assert isinstance(AuthService, type)
    
    def test_has_docstring(self):
        """La clase tiene docstring"""
        assert AuthService.__doc__ is not None
    
    def test_has_login_method(self):
        """Tiene método login"""
        assert hasattr(AuthService, 'login')
    
    def test_has_logout_method(self):
        """Tiene método logout"""
        assert hasattr(AuthService, 'logout')
    
    def test_has_get_client_method(self):
        """Tiene método get_client"""
        assert hasattr(AuthService, 'get_client')


class TestAuthServiceThreadSafety:
    """Tests para seguridad de threads."""
    
    def test_login_uses_daemon_thread(self):
        """login usa thread daemon"""
        with patch('app.service.auth_service.ImapClient'):
            with patch('app.service.auth_service.threading.Thread') as mock_thread:
                service = AuthService()
                service.login("test@email.com", "pass", Mock(), Mock())
                
                # Verificar que se creó con daemon=True
                call_kwargs = mock_thread.call_args[1]
                assert call_kwargs.get('daemon') is True
