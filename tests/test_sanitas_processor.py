"""Tests para SanitasProcessor y wiring (settings, eps_config, EmailService).

Cubre el SPEC confirmado:
- CRNCXC FC0000+numero vía _formatear_crncxc.
- CRNCONOBJ de 6 caracteres: GENERAL numérico 1-6 mapeado a FA/TA/SO/AU/CO/CL
  (letras se conservan) + ESPECIFICO 2 dígitos (cero a la izquierda) +
  APLICACIÓN 2 dígitos (cero a la izquierda; "01" si vacía).
  Ej: GENERAL=2, ESPECIFICO=6, APLICACIÓN vacía -> "TA0601".
- OBSERVACIONES vacía -> "MVC EN <NOMBRE PROCEDIMIENTO>".
- Homologación por CODIGO PROCEDIMIENTO PRESTADOR (solo insumos).
- CROOBSERV "REG, GLOSA SEGÚN RAD N. <fecha>" DD/MM/AAAA.
- CRNCLAOBJ siempre vacía; CROFECOBJ = fecha del correo.
- Solo .xlsx (PDF ignorado); un xlsx por correo.
- homologate retorna DataFrame; export sin columnas internas.
- Nombres SANITAS_GLOSAS_<ts>.xlsx / Objeciones_SANITAS_<ts>.xlsx.
"""
import os

import pandas as pd
import pytest

from app.config import settings
from app.config.eps_config import get_eps_by_name
from app.service.email_service import EmailService
from app.service.processors import SanitasProcessor
from app.service.processors.sanitas_processor import OBJECIONES_COLUMNS

EMAIL_DATE = "2026-03-10 08:00:00"


def _fila_base(**kwargs):
    fila = {
        "NUMERO DE FACTURA": "12345",
        "VALOR GLOSADO": 1500.50,
        "NOMBRE PROCEDIMIENTO": "CONSULTA MEDICA",
        "CODIGO PROCEDIMIENTO PRESTADOR": "SERV001",
        "CODIGO CONCEPTO GENERAL": "4",
        "CODIGO CONCEPTO ESPECIFICO": "30",
        "CODIGO CONCEPTO APLICACIÓN": "2",
        "OBSERVACIONES": "Soporte incompleto",
    }
    fila.update(kwargs)
    return fila


def _xlsx(path, filas):
    pd.DataFrame(filas).to_excel(path, index=False)
    return str(path)


@pytest.fixture
def xlsx_simple(tmp_path):
    return _xlsx(tmp_path / "sanitas.xlsx", [_fila_base()])


@pytest.fixture
def processor():
    return SanitasProcessor(homologador_path="")


class TestIdentify:
    def test_solo_xlsx_pdf_se_ignora(self, tmp_path, processor):
        xlsx = _xlsx(tmp_path / "a.xlsx", [_fila_base()])
        pdf = tmp_path / "b.pdf"
        pdf.write_bytes(b"%PDF-1.4 fake")
        result = processor.identify_files([xlsx, str(pdf)])
        assert result == [xlsx]

    def test_retorna_lista_xlsx(self, tmp_path, processor):
        a = _xlsx(tmp_path / "a.xlsx", [_fila_base()])
        b = _xlsx(tmp_path / "b.XLSX", [_fila_base()])
        assert processor.identify_files([a, b]) == [a, b]

    def test_validate_ok_y_faltante(self, tmp_path, processor):
        xlsx = _xlsx(tmp_path / "a.xlsx", [_fila_base()])
        assert processor.validate_files([xlsx]) is True
        assert processor.validate_files([str(tmp_path / "noexiste.xlsx")]) is False

    def test_validate_sin_archivos(self, processor):
        assert processor.validate_files([]) is False
        assert any("xlsx" in e.lower() for e in processor.errors)


class TestHomologate:
    def test_retorna_dataframe(self, processor, xlsx_simple):
        data = processor.extract_data([xlsx_simple])
        result = processor.homologate(data)
        assert isinstance(result, pd.DataFrame)
        assert len(result) == 1

    def test_factura_formato_crncxc(self, processor, xlsx_simple):
        result = processor.homologate(processor.extract_data([xlsx_simple]))
        assert result.loc[0, "CRNCXC"] == "FC000012345"

    def test_codigo_seis_caracteres(self, processor, xlsx_simple):
        result = processor.homologate(processor.extract_data([xlsx_simple]))
        # GENERAL "4" -> AU, ESPECIFICO "30", APLICACIÓN "2" -> "02".
        assert result.loc[0, "CRNCONOBJ"] == "AU3002"

    def test_codigo_con_vacios(self, tmp_path, processor):
        path = _xlsx(
            tmp_path / "v.xlsx",
            [_fila_base(**{"CODIGO CONCEPTO ESPECIFICO": "", "CODIGO CONCEPTO APLICACIÓN": None})],
        )
        result = processor.homologate(processor.extract_data([path]))
        # AU + "00" + "01".
        assert result.loc[0, "CRNCONOBJ"] == "AU0001"

    def test_mapeo_general_numerico(self, tmp_path, processor):
        filas = [
            _fila_base(**{
                "CODIGO CONCEPTO GENERAL": str(n),
                "CODIGO CONCEPTO ESPECIFICO": 6,
                "CODIGO CONCEPTO APLICACIÓN": None,
            })
            for n in (1, 2, 3, 4, 5, 6)
        ]
        path = _xlsx(tmp_path / "nums.xlsx", filas)
        result = processor.homologate(processor.extract_data([path]))
        assert result["CRNCONOBJ"].tolist() == [
            "FA0601",
            "TA0601",
            "SO0601",
            "AU0601",
            "CO0601",
            "CL0601",
        ]
        assert all(len(c) == 6 for c in result["CRNCONOBJ"])

    def test_ejemplo_usuario_ta0601(self, tmp_path, processor):
        path = _xlsx(
            tmp_path / "e.xlsx",
            [_fila_base(**{
                "CODIGO CONCEPTO GENERAL": 2,
                "CODIGO CONCEPTO ESPECIFICO": 6,
                "CODIGO CONCEPTO APLICACIÓN": "",
            })],
        )
        result = processor.homologate(processor.extract_data([path]))
        assert result.loc[0, "CRNCONOBJ"] == "TA0601"

    def test_general_letras_se_conservan(self, tmp_path, processor):
        path = _xlsx(
            tmp_path / "l.xlsx",
            [_fila_base(**{
                "CODIGO CONCEPTO GENERAL": "au",
                "CODIGO CONCEPTO ESPECIFICO": "01",
                "CODIGO CONCEPTO APLICACIÓN": "",
            })],
        )
        result = processor.homologate(processor.extract_data([path]))
        assert result.loc[0, "CRNCONOBJ"] == "AU0101"

    def test_observacion_conserva_valor(self, processor, xlsx_simple):
        result = processor.homologate(processor.extract_data([xlsx_simple]))
        assert result.loc[0, "CRDOBSERV"] == "Soporte incompleto"

    def test_observacion_vacia_mvc_en_procedimiento(self, tmp_path, processor):
        path = _xlsx(tmp_path / "m.xlsx", [_fila_base(OBSERVACIONES="")])
        result = processor.homologate(processor.extract_data([path]))
        assert result.loc[0, "CRDOBSERV"] == "MVC EN CONSULTA MEDICA"

    def test_observacion_vacia_sin_distincion_general(self, tmp_path, processor):
        path = _xlsx(
            tmp_path / "m.xlsx",
            [
                _fila_base(OBSERVACIONES=""),
                _fila_base(OBSERVACIONES="", **{"CODIGO CONCEPTO GENERAL": "5"}),
                _fila_base(OBSERVACIONES="  "),
                _fila_base(OBSERVACIONES="Ya observado"),
            ],
        )
        result = processor.homologate(processor.extract_data([path]))
        assert result.loc[0, "CRDOBSERV"] == "MVC EN CONSULTA MEDICA"
        assert result.loc[1, "CRDOBSERV"] == "MVC EN CONSULTA MEDICA"
        assert result.loc[2, "CRDOBSERV"] == "MVC EN CONSULTA MEDICA"
        assert result.loc[3, "CRDOBSERV"] == "Ya observado"

    def test_falta_columna_error_explicito(self, tmp_path, processor):
        df = pd.DataFrame([{"OTRA": 1, "VALOR": 2}])
        path = str(tmp_path / "bad.xlsx")
        df.to_excel(path, index=False)
        result = processor.homologate(processor.extract_data([path]))
        assert result.empty
        assert any("Falta columna" in e and "candidatas:" in e for e in processor.errors)

    def test_valor_preserva_decimales(self, processor, xlsx_simple):
        result = processor.homologate(processor.extract_data([xlsx_simple]))
        assert result.loc[0, "CROVALOBJ"] == pytest.approx(1500.50)

    def test_homologacion_solo_insumos(self, tmp_path):
        hom = pd.DataFrame(
            {
                "Código Servicio de la ERP": ["SERV001"],
                "Código producto en DGH": ["HOM001"],
                "COD_SERV_FACT": ["HOM001"],
            }
        )
        hom_path = str(tmp_path / "hom.xlsx")
        hom.to_excel(hom_path, index=False)
        proc = SanitasProcessor(homologador_path=hom_path)
        assert proc.load_homologador() is True
        path = _xlsx(
            tmp_path / "s.xlsx",
            [
                _fila_base(**{"NOMBRE PROCEDIMIENTO": "insumos y medicamentos intrahospitalarios"}),
                _fila_base(**{"NOMBRE PROCEDIMIENTO": "CONSULTA MEDICA"}),
            ],
        )
        result = proc.homologate(proc.extract_data([path]))
        assert result.loc[0, "SLNSERPRO"] == "HOM001"
        assert result.loc[1, "SLNSERPRO"] == "SERV001"

    def test_columna_prestador_canonica(self, tmp_path, processor):
        path = _xlsx(
            tmp_path / "c.xlsx",
            [_fila_base(**{"CODIGO PROCEDIMIENTO PRESTADOR": "PREST123"})],
        )
        result = processor.homologate(processor.extract_data([path]))
        assert result.loc[0, "SLNSERPRO"] == "PREST123"

    def test_alias_legado_codigo_servicio(self, tmp_path, processor):
        fila = _fila_base()
        del fila["CODIGO PROCEDIMIENTO PRESTADOR"]
        fila["CODIGO SERVICIO"] = "SERV001"
        path = _xlsx(tmp_path / "a.xlsx", [fila])
        result = processor.homologate(processor.extract_data([path]))
        assert result.loc[0, "SLNSERPRO"] == "SERV001"

    def test_export_sin_columnas_internas(self, tmp_path, processor, xlsx_simple):
        detalle = processor.homologate(processor.extract_data([xlsx_simple]))
        detalle["fecha_correo"] = EMAIL_DATE
        out = str(tmp_path / "out.xlsx")
        assert processor.save_result(detalle, out) is True
        leido = pd.read_excel(out)
        assert "_FACTURA" not in leido.columns
        assert "fecha_correo" not in leido.columns


class TestObjeciones:
    def _detalle(self, processor, path):
        detalle = processor.homologate(processor.extract_data([path]))
        return detalle

    def test_columnas_y_crnclaobj_vacia(self, tmp_path, processor, xlsx_simple):
        detalle = self._detalle(processor, xlsx_simple)
        obj = processor._build_objeciones_df(detalle, EMAIL_DATE)
        assert list(obj.columns) == OBJECIONES_COLUMNS
        assert (obj["CRNCLAOBJ"] == "").all()
        assert obj.loc[0, "CROCLAOBJ"] == 0
        assert obj.loc[0, "GENUSUARIO4"] == 1103858268

    def test_fecha_y_observacion_general(self, tmp_path, processor, xlsx_simple):
        detalle = self._detalle(processor, xlsx_simple)
        obj = processor._build_objeciones_df(detalle, EMAIL_DATE)
        assert obj.loc[0, "CROFECOBJ"] == "10/03/2026"
        assert obj.loc[0, "CROOBSERV"] == "REG, GLOSA SEGÚN RAD N. 10/03/2026"

    def test_au_ta_unificado_con_doble_slash(self, tmp_path, processor):
        path = _xlsx(
            tmp_path / "au.xlsx",
            [
                _fila_base(**{
                    "CODIGO CONCEPTO GENERAL": "AU",
                    "CODIGO CONCEPTO ESPECIFICO": "01",
                    "CODIGO CONCEPTO APLICACIÓN": "",
                    "OBSERVACIONES": "Obs AU",
                }),
                _fila_base(**{
                    "CODIGO CONCEPTO GENERAL": "TA",
                    "CODIGO CONCEPTO ESPECIFICO": "02",
                    "CODIGO CONCEPTO APLICACIÓN": "",
                    "OBSERVACIONES": "Obs TA",
                }),
            ],
        )
        detalle = self._detalle(processor, path)
        obj = processor._build_objeciones_df(detalle, EMAIL_DATE)
        assert len(obj) == 1
        # GENERAL letras se conservan; ESPECIFICO "01"; APLICACIÓN vacía -> "01".
        assert obj.loc[0, "CRNCONOBJ"] == "AU0101"
        assert obj.loc[0, "CRDOBSERV"] == "Obs AU // Obs TA"


class TestProcessGlosas:
    def test_genera_archivos_con_nombres(self, tmp_path, xlsx_simple):
        proc = SanitasProcessor(homologador_path="")
        result, message = proc.process_glosas(
            [xlsx_simple], output_dir=str(tmp_path), email_date=EMAIL_DATE
        )
        assert result is not None
        assert {"detalle", "glosa", "objeciones"} <= set(result.keys())
        assert isinstance(result["detalle"], pd.DataFrame)
        archivos = os.listdir(str(tmp_path))
        assert any(a.startswith("SANITAS_GLOSAS_") and a.endswith(".xlsx") for a in archivos)
        assert any(a.startswith("Objeciones_SANITAS_") and a.endswith(".xlsx") for a in archivos)
        assert message.startswith("[OK]")

    def test_sin_archivos_falla_explicito(self, tmp_path):
        proc = SanitasProcessor(homologador_path="")
        result, message = proc.process_glosas([], output_dir=str(tmp_path))
        assert result is None
        assert "xlsx" in message.lower()


class TestWiring:
    def test_settings_rutas_sanitas(self):
        assert "sanitas_output" in settings.NETWORK_PATHS
        assert settings.NETWORK_PATHS["sanitas_output"].endswith("SANITAS")
        assert "sanitas" in settings.HOMOLOGADOR_FILES
        assert settings.HOMOLOGADOR_FILES["sanitas"].endswith("sanitas_homologador.xlsx")
        assert settings.get_output_dir("Sanitas") == settings.NETWORK_PATHS["sanitas_output"] \
            if settings.is_network_available() else isinstance(settings.get_output_dir("Sanitas"), str)

    def test_eps_config_processor(self):
        eps = get_eps_by_name("Sanitas")
        assert eps.processor_class == "SanitasProcessor"
        assert eps.enabled is True
        assert eps.homologador_path == settings.HOMOLOGADOR_FILES["sanitas"]

    def test_processors_export(self):
        from app.service import processors

        assert processors.SanitasProcessor is SanitasProcessor

    def test_email_service_procesar_sanitas_contrato(self, tmp_path, xlsx_simple):
        service = EmailService()
        service.sanitas_output_dir = str(tmp_path)
        resultado = service.procesar_sanitas([xlsx_simple], email_date=EMAIL_DATE)
        assert resultado["success"] is True
        for key in ("message", "output_file", "objeciones_file", "path", "resumen"):
            assert key in resultado
        assert resultado["output_file"] and resultado["output_file"].endswith(".xlsx")
        assert resultado["objeciones_file"] and resultado["objeciones_file"].endswith(".xlsx")
        assert resultado["resumen"]["total_registros"] == 1
        assert resultado["resumen"]["facturas_unicas"] == 1

    def test_email_service_sin_archivos(self):
        service = EmailService()
        resultado = service.procesar_sanitas([])
        assert resultado["success"] is False
