"""Fase 1 Sanitas: búsqueda IMAP con filtro FROM.
Fase 2: SanitasEps ya expone processor_class="SanitasProcessor".

Cubre:
- SanitasEps: sender_filter + subject_pattern + filter_type subject_exact_pattern,
  processor_class SanitasProcessor, enabled True.
- MessageFilter.get_search_keyword para Sanitas retorna patrón completo.
- ImapClient._build_search_criteria incluye FROM cuando se pasa from_addr,
  y sin from_addr sigue igual (sin FROM).
- EmailService.search_messages e ImapClient.search_by_subject aceptan
  from_addr opcional con default None y lo propagan.
"""
import inspect
from unittest.mock import MagicMock

from app.config.eps_config import get_eps_by_name
from app.core.imap_client import ImapClient
from app.service.email_service import EmailService
from app.ui.business_logic import MessageFilter


SANITAS_SENDER = "cuentasmedicaseps@epssanitas.notify-it.com"
SANITAS_PATTERN = "Referencia: Informe Glosas EPS Sanitas"


class TestSanitasEpsConfig:
    def test_sanitas_sender_y_patron(self):
        eps = get_eps_by_name("Sanitas")
        assert eps is not None
        assert eps.sender_filter == SANITAS_SENDER
        assert eps.subject_pattern == SANITAS_PATTERN
        assert eps.filter_type == "subject_exact_pattern"

    def test_sanitas_con_procesador_y_habilitada(self):
        eps = get_eps_by_name("Sanitas")
        assert eps.processor_class == "SanitasProcessor"
        assert eps.enabled is True

    def test_sanitas_to_dict_expone_sender(self):
        eps = get_eps_by_name("Sanitas")
        d = eps.to_dict()
        assert d["sender_filter"] == SANITAS_SENDER
        assert d["subject_pattern"] == SANITAS_PATTERN
        assert d["filter_type"] == "subject_exact_pattern"


class TestSanitasSearchKeyword:
    def test_retorna_patron_completo(self):
        eps = get_eps_by_name("Sanitas").to_dict()
        assert MessageFilter.get_search_keyword(eps) == SANITAS_PATTERN

    def test_dict_manual_igual(self):
        eps = {
            "filter_type": "subject_exact_pattern",
            "subject_pattern": SANITAS_PATTERN,
            "sender_filter": SANITAS_SENDER,
        }
        assert MessageFilter.get_search_keyword(eps) == SANITAS_PATTERN


class TestImapFromCriteria:
    def test_criterio_incluye_from_cuando_se_pasa(self):
        client = ImapClient()
        crit = client._build_search_criteria(
            keyword=SANITAS_PATTERN, from_addr=SANITAS_SENDER
        )
        assert f'FROM "{SANITAS_SENDER}"' in crit
        assert f'SUBJECT "{SANITAS_PATTERN}"' in crit

    def test_criterio_solo_from(self):
        client = ImapClient()
        crit = client._build_search_criteria(from_addr=SANITAS_SENDER)
        assert f'FROM "{SANITAS_SENDER}"' in crit
        assert "SUBJECT" not in crit

    def test_busqueda_sin_from_sigue_igual(self):
        client = ImapClient()
        assert client._build_search_criteria() == "ALL"
        crit = client._build_search_criteria(keyword="glosas")
        assert 'SUBJECT "glosas"' in crit
        assert "FROM" not in crit

    def test_from_con_comillas_escapadas(self):
        client = ImapClient()
        crit = client._build_search_criteria(from_addr='a"b@test.com')
        assert 'FROM "a\\"b@test.com"' in crit

    def test_search_by_subject_pasa_from_al_criterio(self):
        client = ImapClient()
        mock_conn = MagicMock()
        mock_conn.select.return_value = ("OK", [b"0"])
        mock_conn.search.return_value = ("OK", [b""])
        client.conn = mock_conn
        client.search_by_subject("glosa", from_addr=SANITAS_SENDER)
        assert mock_conn.search.called
        args = mock_conn.search.call_args[0]
        # search(None, criteria)
        assert f'FROM "{SANITAS_SENDER}"' in args[1]

    def test_search_by_subject_sin_from_no_incluye_from(self):
        client = ImapClient()
        mock_conn = MagicMock()
        mock_conn.select.return_value = ("OK", [b"0"])
        mock_conn.search.return_value = ("OK", [b""])
        client.conn = mock_conn
        client.search_by_subject("glosa")
        args = mock_conn.search.call_args[0]
        assert "FROM" not in args[1]


class TestFromAddrFirmasOpcionales:
    def test_build_search_criteria_default_none(self):
        sig = inspect.signature(ImapClient._build_search_criteria)
        assert "from_addr" in sig.parameters
        assert sig.parameters["from_addr"].default is None

    def test_search_by_subject_default_none(self):
        sig = inspect.signature(ImapClient.search_by_subject)
        assert "from_addr" in sig.parameters
        assert sig.parameters["from_addr"].default is None

    def test_email_service_search_messages_default_none(self):
        sig = inspect.signature(EmailService.search_messages)
        assert "from_addr" in sig.parameters
        assert sig.parameters["from_addr"].default is None


class TestEmailServiceFromAddr:
    def _service_con_mock(self):
        service = EmailService()
        mock_client = MagicMock()
        mock_client.search_by_subject.return_value = []
        service.imap_client = mock_client
        return service, mock_client

    def test_pasa_from_al_cliente(self):
        service, mock_client = self._service_con_mock()
        service.search_messages("x", from_addr=SANITAS_SENDER)
        _, kwargs = mock_client.search_by_subject.call_args
        assert kwargs.get("from_addr") == SANITAS_SENDER

    def test_sin_from_pasa_none(self):
        service, mock_client = self._service_con_mock()
        service.search_messages("x")
        _, kwargs = mock_client.search_by_subject.call_args
        assert kwargs.get("from_addr") is None


class TestSanitasFlujoSinRamaEspecial:
    def test_matches_usa_mismo_codigo(self):
        eps = get_eps_by_name("Sanitas").to_dict()
        ok = {
            "subject": "Referencia: Informe Glosas EPS Sanitas FC123",
            "from": "cuentasmedicaseps@epssanitas.notify-it.com",
        }
        otro_remitente = {
            "subject": "Referencia: Informe Glosas EPS Sanitas FC123",
            "from": "otro@test.com",
        }
        assert MessageFilter.matches(ok, eps) is True
        assert MessageFilter.matches(otro_remitente, eps) is False
        # dedupe helper compartido
        assert MessageFilter.normalize_subject(ok["subject"]) != ""
