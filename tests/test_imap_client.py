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


# ==================== EXTENSIÓN T2.3 (mocks, tmp_path, sin sockets) ====================

from datetime import datetime as _dt_imap
from email.message import EmailMessage as _EmailMessage


def _raw_glosa_email(subject="Reporte Glosas FC123", filename="detalle.xlsx",
                     payload=b"fake-excel-bytes"):
    msg = _EmailMessage()
    msg["Subject"] = subject
    msg["From"] = "eps@test.com"
    msg["Date"] = "Mon, 01 May 2024 10:00:00 +0000"
    msg.set_content("cuerpo del correo")
    msg.add_attachment(
        payload, maintype="application",
        subtype="vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        filename=filename,
    )
    return msg.as_bytes()


def _client_with_raw(raw, msg_id=b"1"):
    client = ImapClient()
    mock_conn = MagicMock()
    mock_conn.select.return_value = ("OK", [b"1"])
    mock_conn.fetch.return_value = ("OK", [(msg_id, raw)])
    client.conn = mock_conn
    return client


class TestImapBuildSearchCriteriaTmp:
    """_build_search_criteria por fecha/keyword."""

    def test_keyword_solo(self):
        client = ImapClient()
        crit = client._build_search_criteria(keyword="glosas")
        assert 'SUBJECT "glosas"' in crit

    def test_keyword_escapa_comillas(self):
        client = ImapClient()
        crit = client._build_search_criteria(keyword='glosa "fc"')
        assert '\\"' in crit

    def test_sin_args_retorna_all(self):
        client = ImapClient()
        assert client._build_search_criteria() == "ALL"

    def test_fecha_desde(self):
        client = ImapClient()
        crit = client._build_search_criteria(date_from=_dt_imap(2024, 5, 1))
        assert "SINCE 01-May-2024" in crit

    def test_fecha_hasta_es_exclusiva_mas_un_dia(self):
        client = ImapClient()
        crit = client._build_search_criteria(date_to=_dt_imap(2024, 5, 10))
        # BEFORE es exclusivo: 10-may -> 11-May-2024
        assert "BEFORE 11-May-2024" in crit

    def test_keyword_y_rango_combinados(self):
        client = ImapClient()
        crit = client._build_search_criteria(
            keyword="glosa",
            date_from=_dt_imap(2024, 5, 1),
            date_to=_dt_imap(2024, 5, 10),
        )
        assert crit.startswith("(") and crit.endswith(")")
        assert 'SUBJECT "glosa"' in crit
        assert "SINCE 01-May-2024" in crit
        assert "BEFORE 11-May-2024" in crit

    def test_fecha_string_soportada(self):
        client = ImapClient()
        crit = client._build_search_criteria(date_from="2024-05-01")
        assert "SINCE 01-May-2024" in crit


class TestImapParseMessageTmp:
    """_parse_message con adjunto programado vía MockIMAP."""

    def test_parse_con_adjunto(self):
        raw = _raw_glosa_email(subject="Reporte Glosas FC123")
        client = _client_with_raw(raw, b"7")
        info = client._parse_message(b"7", keyword="glosas")
        assert info is not None
        assert info["id"] == "7"
        assert "Glosas" in info["subject"]
        assert info["has_attachments"] is True

    def test_parse_filtra_por_keyword(self):
        raw = _raw_glosa_email(subject="Reporte Glosas FC123")
        client = _client_with_raw(raw)
        assert client._parse_message(b"1", keyword="mutualser") is None

    def test_parse_fetch_fallido_retorna_none(self):
        client = ImapClient()
        mock_conn = MagicMock()
        mock_conn.fetch.return_value = ("NO", [None])
        client.conn = mock_conn
        assert client._parse_message(b"1") is None


class TestImapDownloadAttachmentsTmp:
    """download_attachments a tmp_path, sin red."""

    def test_download_guarda_xlsx_en_tmp(self, tmp_path):
        raw = _raw_glosa_email(filename="detalle.xlsx", payload=b"XLSX-BYTES")
        client = _client_with_raw(raw)
        saved = client.download_attachments("1", dest_dir=str(tmp_path))
        assert len(saved) == 1
        assert saved[0].endswith("detalle.xlsx")
        import os
        assert os.path.exists(saved[0])
        with open(saved[0], "rb") as f:
            assert f.read() == b"XLSX-BYTES"

    def test_download_omite_extension_no_permitida(self, tmp_path):
        msg = _EmailMessage()
        msg["Subject"] = "test"
        msg["From"] = "a@test.com"
        msg.set_content("cuerpo")
        msg.add_attachment(b"IMG", maintype="image", subtype="png", filename="logo.png")
        msg.add_attachment(
            b"XLSX", maintype="application",
            subtype="vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            filename="glosa.xlsx",
        )
        client = _client_with_raw(msg.as_bytes())
        saved = client.download_attachments("1", dest_dir=str(tmp_path))
        assert len(saved) == 1
        assert saved[0].endswith("glosa.xlsx")

    def test_download_sin_conexion_retorna_vacio(self, tmp_path):
        client = ImapClient()
        assert client.download_attachments("1", dest_dir=str(tmp_path)) == []


class TestImapMockFlowTmp:
    """Flujo select/search/fetch programados + mock de IMAP4_SSL."""

    def test_search_by_subject_con_mock_programado(self):
        raw = _raw_glosa_email(subject="Reporte Glosas FC999")
        client = ImapClient()
        mock_conn = MagicMock()
        mock_conn.select.return_value = ("OK", [b"2"])
        mock_conn.search.return_value = ("OK", [b"1 2"])
        mock_conn.fetch.return_value = ("OK", [(b"1", raw)])
        client.conn = mock_conn

        msgs = client.search_by_subject("glosas")
        assert len(msgs) == 2
        assert all("Glosas" in m["subject"] for m in msgs)
        mock_conn.select.assert_called()
        mock_conn.search.assert_called()

    def test_search_sin_resultados_retorna_vacio(self):
        client = ImapClient()
        mock_conn = MagicMock()
        mock_conn.select.return_value = ("OK", [b"0"])
        mock_conn.search.return_value = ("OK", [b""])
        client.conn = mock_conn
        assert client.search_by_subject("glosas") == []

    @patch('app.core.imap_client.imaplib.IMAP4_SSL')
    def test_connect_mock_sin_sockets(self, mock_ssl):
        mock_conn = MagicMock()
        mock_ssl.return_value = mock_conn
        client = ImapClient()
        assert client.connect("user@gmail.com", "pwd") is True
        mock_ssl.assert_called_once_with("imap.gmail.com", 993)
        mock_conn.login.assert_called_once_with("user@gmail.com", "pwd")
