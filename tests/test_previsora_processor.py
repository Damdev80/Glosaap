"""Tests para PrevisoraProcessor y wiring (settings, eps_config, EmailService).

Cubre el SPEC de fase 1 (solo REGISTRO, sin objeciones):
- Solo .pdf (xlsx se ignora); TODOS los pdfs, nunca solo el primero.
- Parseo de liquidación: NRO_FACTURA + Cant/Código/Procedimiento/%/
  Cobrado/Objeción/Liquidado + Observación por ítem.
- homologate retorna DataFrame con CRNCXC FC0000+numero, SLNSERPRO
  original (aún sin tabla), CROVALOBJ numérico, CRDOBSERV observación.
- Export sin columnas internas; nombre PREVISORA_REGISTRO_<ts>.xlsx.
"""
import os

import pandas as pd
import pytest

from app.config import settings
from app.config.eps_config import get_eps_by_name
from app.service.email_service import EmailService
from app.service.processors import PrevisoraProcessor
from app.service.processors.previsora_processor import REGISTRO_COLUMNS

TEXTO_MUESTRA = (
    "Liquidación de reclamaciones Previsora Seguros SOAT No. Egreso 9888612 "
    "Nro Radicado HA230528/03281 Nro Factura FC515083 Siniestro SISE 438005 "
    "Cant. 1 Código 19304 Procedimiento Cuadro hemático y hemograma "
    "% 100.00% Cobrado $ 37,900.00 Objeción $ 37,900.00 Liquidado $ 0.00 "
    "Observación: Se glosa El ítem con código 19304 no se considera pertinente "
    "Cant. 1 Código 31109 Procedimiento Abdomen, visceras "
    "% 0.00% Cobrado $ 354,900.00 Objeción $ 0.00 Liquidado $ 354,900.00 "
    "Observación: Sin objeción "
)


@pytest.fixture
def processor():
    return PrevisoraProcessor(homologador_path="")


@pytest.fixture
def pdf_simple(tmp_path, monkeypatch):
    from app.service.processors.previsora_processor import PrevisoraProcessor as P

    path = tmp_path / "liquidacion.pdf"
    path.write_bytes(b"%PDF-1.4 fake")
    monkeypatch.setattr(P, "_extraer_texto_pdf", staticmethod(lambda p: TEXTO_MUESTRA))
    return str(path)


class TestIdentify:
    def test_solo_pdf_xlsx_se_ignora(self, tmp_path, processor):
        pdf = tmp_path / "a.pdf"
        pdf.write_bytes(b"%PDF-1.4 fake")
        xlsx = tmp_path / "b.xlsx"
        xlsx.write_bytes(b"fake")
        assert processor.identify_files([str(xlsx), str(pdf)]) == [str(pdf)]

    def test_retorna_todos_los_pdfs(self, tmp_path, processor):
        a = tmp_path / "a.pdf"
        b = tmp_path / "B.PDF"
        a.write_bytes(b"%PDF-1.4")
        b.write_bytes(b"%PDF-1.4")
        assert processor.identify_files([str(a), str(b)]) == [str(a), str(b)]

    def test_validate_ok_y_faltante(self, tmp_path, processor):
        pdf = tmp_path / "a.pdf"
        pdf.write_bytes(b"%PDF-1.4")
        assert processor.validate_files([str(pdf)]) is True
        assert processor.validate_files([str(tmp_path / "noexiste.pdf")]) is False

    def test_validate_sin_archivos(self, processor):
        assert processor.validate_files([]) is False
        assert any("pdf" in e.lower() for e in processor.errors)


class TestParseo:
    def test_seccion_por_factura(self, processor):
        secciones, huerfano = processor._seccionar_por_factura(TEXTO_MUESTRA)
        assert len(secciones) == 1
        factura, radicado, siniestro, _ = secciones[0]
        assert factura == "FC515083"
        assert siniestro == "438005"
        assert huerfano.strip() != ""

    def test_items_y_observacion(self, processor):
        secciones, _ = processor._seccionar_por_factura(TEXTO_MUESTRA)
        _, _, _, bloque = secciones[0]
        items = processor._parse_bloque_items(bloque, "FC515083", "", "")
        assert len(items) == 2
        assert items[0]["CODIGO"] == "19304"
        assert "hemático" in items[0]["PROCEDIMIENTO"]
        assert items[0]["OBJECION"] == "37,900.00"
        assert "Se glosa" in items[0]["OBSERVACION"]
        assert items[1]["CODIGO"] == "31109"

    def test_sin_factura_error(self, tmp_path, processor, monkeypatch):
        from app.service.processors.previsora_processor import PrevisoraProcessor as P

        path = tmp_path / "sin.pdf"
        path.write_bytes(b"%PDF-1.4")
        monkeypatch.setattr(P, "_extraer_texto_pdf", staticmethod(lambda p: "sin datos"))
        df = processor._parse_pdf(str(path))
        assert df.empty
        assert any("Factura" in e for e in processor.errors)

    def test_variantes_rotulo_y_suelto(self, processor):
        for texto, esperado in [
            ("No. Factura FC123456 resto", "FC123456"),
            ("FACTURA: FC 654321 resto", "FC654321"),
            ("NUMERO DE FACTURA 789012 resto", "789012"),
            ("Liquidación sin rótulo pero con FC789012 suelto", "FC789012"),
        ]:
            secciones, _ = processor._seccionar_por_factura(texto)
            assert len(secciones) == 1, texto
            assert secciones[0][0] == esperado, texto

    def test_formato_real_encabezado_por_item(self, processor):
        texto = (
            "Nro Radicado N4326BL791481 Reconsideracion Siniestro SISE 466355 "
            "Nro Factura FC831591 Amparo Gastos Médicos "
            "Cant. Código Procedimiento % Cobrado Objecion Liquidado "
            "1 21102 Brazo, pierna, rodilla, fémur, hombro, omoplato "
            "0.00% $ 99.900,00 $ 0,00 $ 99.900,00 Observación: "
            "Cant. Código Procedimiento % Cobrado Objecion Liquidado "
            "1 19304 Cuadro hemático o hemograma hematocrito y leucograma "
            "100.00% $ 37.900,00 $ 37.900,00 $ 0,00 "
            "Observación: Se glosa El item con código 19304, descripcion Cuadro "
            "hemático correspondiente a Pertinencia en función a 6.08, por la "
            "cantidad: 3, por el valor de 139600 debido a: No se considera pertinente "
            "Cant. Código Procedimiento % Cobrado Objecion Liquidado "
            "5 38132 Habitación bipersonal 60.00% $ 2.516.500,00 $ 1.509.900,00 "
            "$ 1.006.600,00 Observación: Se objeta la estancia "
        )
        secciones, huerfano = processor._seccionar_por_factura(texto)
        assert len(secciones) == 1
        _, _, _, bloque = secciones[0]
        items = processor._parse_bloque_items(bloque, "FC831591", "N4326BL791481", "466355")
        assert len(items) == 3
        assert items[0]["CODIGO"] == "21102"
        assert items[0]["CANT"] == "1"
        assert items[0]["OBJECION"] == "0,00"
        assert items[0]["OBSERVACION"] == ""
        assert items[1]["CODIGO"] == "19304"
        assert "hematocrito" in items[1]["PROCEDIMIENTO"]
        assert items[1]["COBRADO"] == "37.900,00"
        assert "No se considera pertinente" in items[1]["OBSERVACION"]
        assert items[2]["CANT"] == "5"
        assert items[2]["LIQUIDADO"] == "1.006.600,00"
        assert all(r["NRO_FACTURA"] == "FC831591" for r in items)

    def test_huerfano_se_asigna_primera_factura(self, tmp_path, processor, monkeypatch):
        from app.service.processors.previsora_processor import PrevisoraProcessor as P

        texto = (
            "Cant. Código Procedimiento % Cobrado Objecion Liquidado "
            "1 21102 Brazo 0.00% $ 10,00 $ 0,00 $ 10,00 Observación: "
            "Nro Factura FC999 Amparo X "
            "Cant. Código Procedimiento % Cobrado Objecion Liquidado "
            "1 22222 Pierna 0.00% $ 20,00 $ 0,00 $ 20,00 Observación: "
        )
        path = tmp_path / "h.pdf"
        path.write_bytes(b"%PDF-1.4")
        monkeypatch.setattr(P, "_extraer_texto_pdf", staticmethod(lambda p: texto))
        df = processor._parse_pdf(str(path))
        assert len(df) == 2
        assert (df["NRO_FACTURA"] == "FC999").all()
        assert any("se asigna a factura FC999" in w for w in processor.warnings)

    def test_items_con_rotulos_alternos(self, processor):
        bloque = (
            "Cantidad 2 Cod 456 Descripcion Terapia fisica "
            "% 50.00% Valor Cobrado $ 200,000.00 Valor Objetado $ 100,000.00 "
            "Valor Neto $ 100,000.00 Observación: Glosa parcial "
            "Cant 1 Código 789 Concepto Consulta % 0% Cobrado $ 50.000 "
            "Glosa $ 0 Liquidado $ 50.000"
        )
        filas = processor._parse_bloque_items(bloque, "FC1", "", "")
        assert len(filas) == 2
        assert filas[0]["CODIGO"] == "456"
        assert filas[0]["CANT"] == "2"
        assert filas[0]["OBJECION"] == "100,000.00"
        assert filas[0]["LIQUIDADO"] == "100,000.00"
        assert "Glosa parcial" in filas[0]["OBSERVACION"]
        assert filas[1]["CODIGO"] == "789"

    def test_debug_txt_en_fallo(self, tmp_path, processor, monkeypatch):
        from app.service.processors.previsora_processor import PrevisoraProcessor as P

        path = tmp_path / "vacio.pdf"
        path.write_bytes(b"%PDF-1.4")
        monkeypatch.setattr(P, "_extraer_texto_pdf", staticmethod(lambda p: "texto sin items FC123456"))
        out = tmp_path / "salida"
        df = processor._parse_pdf(str(path), debug_dir=str(out))
        assert df.empty
        assert (out / "PREVISORA_DEBUG_vacio.txt").exists()


class TestHomologate:
    def _detalle(self, processor, pdf_simple):
        return processor.homologate(processor.extract_data([pdf_simple]))

    def test_retorna_dataframe(self, processor, pdf_simple):
        result = self._detalle(processor, pdf_simple)
        assert isinstance(result, pd.DataFrame)
        assert len(result) == 2

    def test_factura_y_codigo_original(self, processor, pdf_simple):
        result = self._detalle(processor, pdf_simple)
        assert result.loc[0, "CRNCXC"] == "FC0000515083"
        assert result.loc[0, "SLNSERPRO"] == "19304"
        assert any("conserva original" in w for w in processor.warnings)

    def test_valor_y_observacion(self, processor, pdf_simple):
        result = self._detalle(processor, pdf_simple)
        assert result.loc[0, "CROVALOBJ"] == pytest.approx(37900.0)
        assert "Se glosa" in result.loc[0, "CRDOBSERV"]

    def test_export_sin_internas(self, tmp_path, processor, pdf_simple):
        detalle = self._detalle(processor, pdf_simple)
        detalle["fecha_correo"] = "2026-10-30 10:00:00"
        out = str(tmp_path / "out.xlsx")
        assert processor.save_to_excel({"detalle": detalle}, out) is True
        leido = pd.read_excel(out)
        assert list(leido.columns) == REGISTRO_COLUMNS
        assert "_FACTURA" not in leido.columns
        assert "fecha_correo" not in leido.columns


class TestProcessGlosas:
    def test_genera_registro(self, tmp_path, pdf_simple):
        proc = PrevisoraProcessor(homologador_path="")
        result, message = proc.process_glosas(
            [pdf_simple], output_dir=str(tmp_path), email_date="2026-10-30 10:00:00"
        )
        assert result is not None
        assert "detalle" in result
        assert len(result["detalle"]) == 2
        archivos = os.listdir(str(tmp_path))
        assert any(a.startswith("PREVISORA_REGISTRO_") and a.endswith(".xlsx") for a in archivos)
        assert message.startswith("[OK]")

    def test_fecha_por_archivo(self, tmp_path, monkeypatch):
        from app.service.processors.previsora_processor import PrevisoraProcessor as P

        a = tmp_path / "a.pdf"
        b = tmp_path / "b.pdf"
        a.write_bytes(b"%PDF-1.4")
        b.write_bytes(b"%PDF-1.4")
        monkeypatch.setattr(P, "_extraer_texto_pdf", staticmethod(lambda p: TEXTO_MUESTRA))

        class FakeAttach:
            def get_file_metadata(self, p):
                if p.endswith("a.pdf"):
                    return {"email_date": "2026-10-25 10:00:00"}
                return {"email_date": "2026-10-30 10:00:00"}

        proc = P(homologador_path="")
        result, _ = proc.process_glosas(
            [str(a), str(b)], output_dir=str(tmp_path), attachment_service=FakeAttach()
        )
        fechas = sorted(result["detalle"]["fecha_correo"].unique().tolist())
        assert fechas == ["2026-10-25 10:00:00", "2026-10-30 10:00:00"]


class TestWiring:
    def test_settings_rutas_previsora(self):
        assert "previsora_output" in settings.NETWORK_PATHS
        assert settings.NETWORK_PATHS["previsora_output"].endswith("PREVISORA")
        assert "previsora" in settings.HOMOLOGADOR_FILES
        assert settings.HOMOLOGADOR_FILES["previsora"].endswith(
            "previsora_homologacion.xlsx"
        )

    def test_eps_config_processor(self):
        eps = get_eps_by_name("Previsora")
        assert eps.processor_class == "PrevisoraProcessor"
        assert eps.enabled is True
        assert eps.sender_filter == "radicacionambulatorio@laconcepcion.org"
        assert "Notificación agrupada" in (eps.subject_pattern or "")

    def test_processors_export(self):
        from app.service import processors

        assert processors.PrevisoraProcessor is PrevisoraProcessor

    def test_email_service_procesar_previsora(self, tmp_path, pdf_simple):
        service = EmailService()
        service.previsora_output_dir = str(tmp_path)
        resultado = service.procesar_previsora([pdf_simple], email_date="2026-10-30 10:00:00")
        assert resultado["success"] is True
        for key in ("message", "output_file", "path", "resumen"):
            assert key in resultado
        assert resultado["objeciones_file"] is None
        assert resultado["resumen"]["total_registros"] == 2
        assert resultado["resumen"]["facturas_unicas"] == 1

    def test_email_service_sin_archivos(self):
        service = EmailService()
        resultado = service.procesar_previsora([])
        assert resultado["success"] is False
