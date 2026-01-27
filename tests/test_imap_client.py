"""
Tests para el cliente IMAP (imap_client.py).

Este módulo contiene tests unitarios para verificar:
- Detección de servidores IMAP
- Decodificación de headers
- Manejo de conexiones
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
import imaplib

from app.core.imap_client import ImapClient, _decode_header


class TestDecodeHeader:
    """Tests para la función de decodificación de headers."""
    
    def test_decode_none_returns_empty(self):
        """None retorna cadena vacía"""
        result = _decode_header(None)
        assert result == ""
    
    def test_decode_simple_string(self):
        """Cadena simple se decodifica correctamente"""
        result = _decode_header("Simple Subject")
        assert "Simple" in result
    
    def test_decode_utf8_encoded(self):
        """Header UTF-8 encoded se decodifica"""
        # Simular header encoded
        result = _decode_header("=?UTF-8?Q?Notificaci=C3=B3n?=")
        assert result  # Debería decodificar algo


class TestImapClientInit:
    """Tests para inicialización del cliente."""
    
    def test_client_creation(self):
        """Crea el cliente correctamente"""
        client = ImapClient()
        assert client is not None
    
    def test_client_has_conn_attribute(self):
        """Tiene atributo conn inicialmente None"""
        client = ImapClient()
        assert client.conn is None
    
    def test_client_has_tempdir_attribute(self):
        """Tiene atributo tempdir"""
        client = ImapClient()
        assert hasattr(client, 'tempdir')
    
    def test_client_has_imap_server_attribute(self):
        """Tiene atributo imap_server"""
        client = ImapClient()
        assert client.imap_server == ""


class TestDetectImapServer:
    """Tests para detección automática de servidor IMAP."""
    
    def test_detect_gmail(self):
        """Detecta servidor Gmail"""
        client = ImapClient()
        server = client._detect_imap_server("user@gmail.com")
        assert server == "imap.gmail.com"
    
    def test_detect_googlemail(self):
        """Detecta servidor Googlemail"""
        client = ImapClient()
        server = client._detect_imap_server("user@googlemail.com")
        assert server == "imap.gmail.com"
    
    def test_detect_outlook(self):
        """Detecta servidor Outlook"""
        client = ImapClient()
        server = client._detect_imap_server("user@outlook.com")
        assert server == "outlook.office365.com"
    
    def test_detect_hotmail(self):
        """Detecta servidor Hotmail"""
        client = ImapClient()
        server = client._detect_imap_server("user@hotmail.com")
        assert server == "outlook.office365.com"
    
    def test_detect_live(self):
        """Detecta servidor Live"""
        client = ImapClient()
        server = client._detect_imap_server("user@live.com")
        assert server == "outlook.office365.com"
    
    def test_detect_yahoo(self):
        """Detecta servidor Yahoo"""
        client = ImapClient()
        server = client._detect_imap_server("user@yahoo.com")
        assert server == "imap.mail.yahoo.com"
    
    def test_detect_custom_domain(self):
        """Dominio personalizado retorna mail.dominio"""
        client = ImapClient()
        server = client._detect_imap_server("user@empresa.com")
        assert server == "mail.empresa.com"
    
    def test_detect_case_insensitive(self):
        """Detección es case-insensitive"""
        client = ImapClient()
        server = client._detect_imap_server("user@GMAIL.COM")
        assert server == "imap.gmail.com"


class TestImapClientMethods:
    """Tests para métodos del cliente."""
    
    def test_list_mailboxes_without_connection(self):
        """list_mailboxes sin conexión retorna lista vacía"""
        client = ImapClient()
        result = client.list_mailboxes()
        assert result == []
    
    def test_select_folder_without_connection_raises(self):
        """select_folder sin conexión lanza RuntimeError"""
        client = ImapClient()
        with pytest.raises(RuntimeError, match="Not connected"):
            client.select_folder("INBOX")


class TestImapClientConnection:
    """Tests para conexión IMAP (mockeados)."""
    
    @patch('app.core.imap_client.imaplib.IMAP4_SSL')
    def test_connect_with_ssl(self, mock_imap):
        """Conecta con SSL por defecto"""
        mock_conn = MagicMock()
        mock_imap.return_value = mock_conn
        
        client = ImapClient()
        result = client.connect(
            "user@gmail.com",
            "password",
            server="imap.gmail.com"
        )
        
        assert result is True
        mock_imap.assert_called_once_with("imap.gmail.com", 993)
        mock_conn.login.assert_called_once_with("user@gmail.com", "password")
    
    @patch('app.core.imap_client.imaplib.IMAP4')
    def test_connect_without_ssl(self, mock_imap):
        """Conecta sin SSL cuando se especifica"""
        mock_conn = MagicMock()
        mock_imap.return_value = mock_conn
        
        client = ImapClient()
        result = client.connect(
            "user@test.com",
            "password",
            server="mail.test.com",
            port=143,
            use_ssl=False
        )
        
        assert result is True
        mock_imap.assert_called_once_with("mail.test.com", 143)
    
    @patch('app.core.imap_client.imaplib.IMAP4_SSL')
    def test_connect_autodetects_server(self, mock_imap):
        """Autodetecta servidor si no se especifica"""
        mock_conn = MagicMock()
        mock_imap.return_value = mock_conn
        
        client = ImapClient()
        client.connect("user@gmail.com", "password")
        
        # Debería detectar imap.gmail.com
        mock_imap.assert_called_once_with("imap.gmail.com", 993)


class TestImapClientMailboxes:
    """Tests para operaciones con mailboxes."""
    
    def test_list_mailboxes_with_connection(self):
        """list_mailboxes retorna lista de carpetas"""
        client = ImapClient()
        mock_conn = MagicMock()
        mock_conn.list.return_value = ("OK", [b"INBOX", b"Sent"])
        client.conn = mock_conn
        
        result = client.list_mailboxes()
        
        assert len(result) == 2
        assert "INBOX" in result
    
    def test_list_mailboxes_handles_none(self):
        """list_mailboxes maneja None en data"""
        client = ImapClient()
        mock_conn = MagicMock()
        mock_conn.list.return_value = ("OK", [None, b"INBOX"])
        client.conn = mock_conn
        
        result = client.list_mailboxes()
        
        # Solo debería incluir INBOX, no None
        assert "INBOX" in result
    
    def test_list_mailboxes_error_returns_empty(self):
        """list_mailboxes retorna vacío si hay error"""
        client = ImapClient()
        mock_conn = MagicMock()
        mock_conn.list.return_value = ("NO", [])
        client.conn = mock_conn
        
        result = client.list_mailboxes()
        
        assert result == []


class TestImapClientSelectFolder:
    """Tests para selección de carpetas."""
    
    def test_select_folder_success(self):
        """Selecciona carpeta exitosamente"""
        client = ImapClient()
        mock_conn = MagicMock()
        mock_conn.select.return_value = ("OK", [b"50"])
        client.conn = mock_conn
        
        count = client.select_folder("INBOX")
        
        mock_conn.select.assert_called_once_with("INBOX")
        assert count == 50
    
    def test_select_folder_error_raises(self):
        """Selección fallida lanza RuntimeError"""
        client = ImapClient()
        mock_conn = MagicMock()
        mock_conn.select.return_value = ("NO", [None])
        client.conn = mock_conn
        
        with pytest.raises(RuntimeError, match="Unable to select"):
            client.select_folder("InvalidFolder")
    
    def test_select_folder_empty_returns_zero(self):
        """Carpeta vacía retorna 0"""
        client = ImapClient()
        mock_conn = MagicMock()
        mock_conn.select.return_value = ("OK", [None])
        client.conn = mock_conn
        
        count = client.select_folder("INBOX")
        
        assert count == 0


class TestImapClientDisconnect:
    """Tests para desconexión."""
    
    def test_has_disconnect_method(self):
        """Tiene método para desconectar"""
        client = ImapClient()
        assert hasattr(client, 'disconnect') or hasattr(client, 'logout') or hasattr(client, 'close')


class TestImapClientPortConfig:
    """Tests para configuración de puertos."""
    
    def test_default_ssl_port(self):
        """Puerto SSL por defecto es 993"""
        # El puerto por defecto en connect es 993
        import inspect
        sig = inspect.signature(ImapClient.connect)
        params = sig.parameters
        assert params['port'].default == 993
    
    def test_default_use_ssl(self):
        """SSL está habilitado por defecto"""
        import inspect
        sig = inspect.signature(ImapClient.connect)
        params = sig.parameters
        assert params['use_ssl'].default is True
