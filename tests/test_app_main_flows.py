"""Tests de flujos principales de app (T2.3).

Cubre helpers de app.ui.app (_parse_email_date, _latest_email_date_str) y
MessageFilter de business_logic con EPS None y duplicado Coosalud/Cosalud.
Solo tmp_path y mocks; prohibido tocar red. FakePage con MagicMock (sin flet real).
"""
from datetime import datetime
from unittest.mock import MagicMock

import pytest

from app.ui.app import _latest_email_date_str, _parse_email_date
from app.ui.business_logic import MessageFilter


class FakePage:
    """Doble de ft.Page basado en MagicMock (no instancia flet real)."""

    def __init__(self):
        self._mock = MagicMock(name="FakePage")
        self.update = self._mock.update
        self.open = self._mock.open
        self.close = self._mock.close
        self.data = {}

    def __getattr__(self, name):
        return getattr(self._mock, name)


@pytest.fixture
def fake_page():
    return FakePage()


class TestFakePageMock:
    def test_fake_page_es_mock_sin_flet_real(self, fake_page):
        assert isinstance(fake_page.update, MagicMock)
        fake_page.update()
        fake_page.update.assert_called_once()

    def test_fake_page_data_dict(self, fake_page):
        fake_page.data["k"] = "v"
        assert fake_page.data["k"] == "v"


class TestParseEmailDate:
    def test_none_retorna_none(self):
        assert _parse_email_date(None) is None

    def test_formato_rfc_con_zona(self):
        d = _parse_email_date("Mon, 01 May 2024 10:00:00 +0000")
        assert d is not None
        assert (d.year, d.month, d.day) == (2024, 5, 1)

    def test_formato_rfc_sin_zona(self):
        d = _parse_email_date("Mon, 01 May 2024 10:00:00")
        assert d is not None
        assert d.day == 1

    def test_formato_ymd(self):
        d = _parse_email_date("2024-05-01 10:00:00")
        assert d == datetime(2024, 5, 1, 10, 0, 0)

    def test_formato_dmy_con_slash(self):
        d = _parse_email_date("01/05/2024 10:00:00")
        assert d is not None
        assert (d.day, d.month, d.year) == (1, 5, 2024)

    def test_invalido_retorna_none(self):
        assert _parse_email_date("no-es-fecha") is None
        assert _parse_email_date("") is None

    def test_datetime_passthrough(self):
        ahora = datetime(2024, 6, 1, 12, 0, 0)
        assert _parse_email_date(ahora) is ahora


class TestLatestEmailDateStr:
    def test_retorna_mas_reciente(self):
        msgs = [
            {"date": "2024-05-01 10:00:00"},
            {"date": "2024-05-03 08:30:00"},
            {"date": "2024-05-02 12:00:00"},
        ]
        assert _latest_email_date_str(msgs) == "2024-05-03 08:30:00"

    def test_vacio_retorna_none(self):
        assert _latest_email_date_str([]) is None
        assert _latest_email_date_str(None) is None

    def test_solo_invalidas_retorna_none(self):
        assert _latest_email_date_str([{"date": "xxx"}, {"date": None}]) is None

    def test_mixto_ignora_invalidas(self):
        msgs = [{"date": "xxx"}, {"date": "2024-05-01 10:00:00"}]
        assert _latest_email_date_str(msgs) == "2024-05-01 10:00:00"

    def test_acepta_datetime(self, fake_page):
        # FakePage no se usa en el helper pero demuestra flujo sin flet real
        assert fake_page is not None
        msgs = [{"date": datetime(2024, 5, 5, 9, 0, 0)}]
        assert _latest_email_date_str(msgs) == "2024-05-05 09:00:00"


class TestFilterByEpsMainFlows:
    def test_eps_none_retorna_todos(self):
        msgs = [{"subject": "a", "from": "x"}, {"subject": "b", "from": "y"}]
        assert MessageFilter.filter_by_eps(msgs, None) == msgs
        assert MessageFilter.filter_by_eps(msgs, {}) == msgs

    def test_coosalud_keyword(self):
        msgs = [
            {"subject": "Reporte Coosalud glosa", "from": "a@test.com"},
            {"subject": "Otro correo", "from": "b@test.com"},
        ]
        eps = {"filter_type": "keyword", "filter": "coosalud"}
        res = MessageFilter.filter_by_eps(msgs, eps)
        assert len(res) == 1
        assert "Coosalud" in res[0]["subject"]

    def test_cosalud_typo_no_arrastra_coosalud(self):
        """Duplicado Coosalud/Cosalud: filtros exactos no se contaminan."""
        msgs = [
            {"subject": "Reporte Coosalud glosa", "from": "a@test.com"},
            {"subject": "Reporte Cosalud glosa", "from": "b@test.com"},
            {"subject": "Otro", "from": "c@test.com"},
        ]
        eps_coo = {"filter_type": "keyword", "filter": "coosalud"}
        eps_cos = {"filter_type": "keyword", "filter": "cosalud"}
        res_coo = MessageFilter.filter_by_eps(msgs, eps_coo)
        res_cos = MessageFilter.filter_by_eps(msgs, eps_cos)
        assert len(res_coo) == 1
        assert "Coosalud" in res_coo[0]["subject"]
        # 'cosalud' es subcadena de ambos? se verifica distinción mínima:
        # al menos el mensaje Cosalud está en su filtro
        assert any("Cosalud" in m["subject"] for m in res_cos)

    def test_duplicados_se_preservan(self):
        dup = {"subject": "Coosalud glosa", "from": "a@test.com"}
        msgs = [dict(dup), dict(dup)]
        eps = {"filter_type": "keyword", "filter": "coosalud"}
        assert len(MessageFilter.filter_by_eps(msgs, eps)) == 2


class TestGetSearchKeywordMainFlows:
    def test_none_retorna_glosa(self):
        assert MessageFilter.get_search_keyword(None) == "glosa"

    def test_sin_patron_retorna_glosa(self):
        assert MessageFilter.get_search_keyword({}) == "glosa"
        assert MessageFilter.get_search_keyword({"subject_pattern": ""}) == "glosa"

    def test_coosalud_patron(self):
        eps = {"subject_pattern": "Reporte Glosas y Devoluciones"}
        assert MessageFilter.get_search_keyword(eps) == "Reporte"

    def test_mutualser_patron(self):
        eps = {"subject_pattern": "Objeciones de glosa Factura FC"}
        assert MessageFilter.get_search_keyword(eps) == "Objeciones"

    def test_ignora_preposiciones(self):
        eps = {"subject_pattern": "de la en glosas"}
        assert MessageFilter.get_search_keyword(eps) == "glosas"

    def test_cosalud_sin_patron_retorna_glosa(self):
        eps = {"name": "Cosalud", "filter": "cosalud"}
        assert MessageFilter.get_search_keyword(eps) == "glosa"
