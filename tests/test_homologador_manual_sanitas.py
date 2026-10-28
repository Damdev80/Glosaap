"""
Tests del homologador manual para Sanitas (homologador normal ERP -> DGH).

La vista del homologador manual trata a SANITAS igual que las demás EPS:
una sola tabla de homologación aplicada a la columna seleccionada.

También se cubre la API reutilizable de SanitasProcessor:
- Vía normal (ERP -> DGH) con floats enteros de Excel.
- Vía insumos (cascada CUM / IUM RDA / CODIGO PRODUCTO) con claves
  flexibles (usada por el procesador automático, no por el manual).
"""
from types import SimpleNamespace

import os

import pandas as pd
import pytest

from app.service.processors.sanitas_processor import SanitasProcessor
from app.ui.views.homologador_manual_view import HomologadorManualView


@pytest.fixture
def sanitas_homologadores(tmp_path):
    """Crea los dos homologadores de Sanitas en un directorio temporal."""
    normal = tmp_path / "sanitas_homologador_2.xlsx"
    pd.DataFrame(
        {
            "CODIGO PROCEDIMIENTO PRESTADOR": ["890201", "890301", 7.0],
            "CODIGO HOMOLOGO": ["CUPS001", "CUPS002", "CUPS007"],
        }
    ).to_excel(normal, index=False)

    insumos = tmp_path / "sanitas_homologador.xlsx"
    pd.DataFrame(
        {
            "CUM": ["CUM123", "CUM456", None],
            "IUM RDA": ["IUM111", None, "IUM333"],
            "CODIGO PRODUCTO": ["PROD-A", "PROD-B", "PROD-C"],
        }
    ).to_excel(insumos, index=False)
    return {"normal": str(normal), "insumos": str(insumos)}


@pytest.fixture
def vista(sanitas_homologadores):
    """Vista del homologador manual con el homologador normal cargado."""
    page = SimpleNamespace(overlay=[])
    view = HomologadorManualView(page=page)
    view.selected_eps = "SANITAS"
    view._sanitas_processor = SanitasProcessor(
        homologador_path=sanitas_homologadores["normal"]
    )
    assert view._sanitas_processor.load_homologador()
    view.df_homologacion = view._sanitas_processor.homologador_df
    return view


# ==================== VÍA NORMAL (ERP -> DGH) — usa el manual ====================

def test_homologacion_normal_match(vista):
    proc = vista._sanitas_processor
    assert proc.homologar_codigo_servicio("890201") == "CUPS001"


def test_homologacion_normal_sin_match_vacia(vista):
    proc = vista._sanitas_processor
    assert proc.homologar_codigo_servicio("999999") == ""


def test_homologacion_normal_float_entero_de_excel(vista):
    proc = vista._sanitas_processor
    assert proc.homologar_codigo_servicio(7.0) == "CUPS007"


# ==================== VÍA INSUMOS (usa el procesador automático) ====================

def test_insumos_por_cum(sanitas_homologadores):
    proc = SanitasProcessor(
        homologador_path=sanitas_homologadores["normal"],
        homologador_insumos_path=sanitas_homologadores["insumos"],
    )
    assert proc.load_homologador_insumos()
    assert proc.homologar_codigo_servicio("CUM123", es_insumo=True) == "PROD-A"


def test_insumos_por_ium(sanitas_homologadores):
    proc = SanitasProcessor(
        homologador_path=sanitas_homologadores["normal"],
        homologador_insumos_path=sanitas_homologadores["insumos"],
    )
    assert proc.load_homologador_insumos()
    assert proc.homologar_codigo_servicio("IUM111", es_insumo=True) == "PROD-A"


def test_insumos_por_producto_directo(sanitas_homologadores):
    proc = SanitasProcessor(
        homologador_path=sanitas_homologadores["normal"],
        homologador_insumos_path=sanitas_homologadores["insumos"],
    )
    assert proc.load_homologador_insumos()
    assert proc.homologar_codigo_servicio("PROD-B", es_insumo=True) == "PROD-B"


def test_insumos_clave_flexible_sin_guiones(sanitas_homologadores):
    proc = SanitasProcessor(
        homologador_path=sanitas_homologadores["normal"],
        homologador_insumos_path=sanitas_homologadores["insumos"],
    )
    assert proc.load_homologador_insumos()
    assert proc.homologar_codigo_servicio("cum-123", es_insumo=True) == "PROD-A"


def test_insumos_sin_match_vacia(sanitas_homologadores):
    proc = SanitasProcessor(
        homologador_path=sanitas_homologadores["normal"],
        homologador_insumos_path=sanitas_homologadores["insumos"],
    )
    assert proc.load_homologador_insumos()
    assert proc.homologar_codigo_servicio("ZZZ", es_insumo=True) == ""


def test_es_insumo_etiqueta_normalizada():
    assert SanitasProcessor.es_insumo("  INSUMOS Y MEDICAMENTOS INTRAHOSPITALARIOS ") is True
    assert SanitasProcessor.es_insumo("insumos y medicamentos intrahospitalarios") is True
    assert SanitasProcessor.es_insumo("CONSULTA EXTERNA") is False
    assert SanitasProcessor.es_insumo(None) is False


# ==================== OBJECIONES DESDE EL MANUAL ====================

def _df_estructurado():
    return pd.DataFrame(
        [
            {
                "NUMERO DE FACTURA": "111",
                "VALOR GLOSADO": 1000.0,
                "NOMBRE PROCEDIMIENTO": "CONSULTA MEDICA",
                "CODIGO PROCEDIMIENTO PRESTADOR": "890201",
                "CODIGO CONCEPTO GENERAL": "4",
                "CODIGO CONCEPTO ESPECIFICO": "30",
                "CODIGO CONCEPTO APLICACIÓN": "2",
                "OBSERVACIONES": "Obs1",
            },
            {
                "NUMERO DE FACTURA": "111",
                "VALOR GLOSADO": 500.0,
                "NOMBRE PROCEDIMIENTO": "INSUMOS Y MEDICAMENTOS INTRAHOSPITALARIOS",
                "CODIGO PROCEDIMIENTO PRESTADOR": "CUM123",
                "CODIGO CONCEPTO GENERAL": 2,
                "CODIGO CONCEPTO ESPECIFICO": 6,
                "CODIGO CONCEPTO APLICACIÓN": "",
                "OBSERVACIONES": "",
            },
        ]
    )


def test_manual_genera_objeciones(vista, sanitas_homologadores, tmp_path, monkeypatch):
    from app.ui.views.homologador_manual_view import HomologadorManualView
    from app.service.processors.sanitas_processor import OBJECIONES_COLUMNS

    monkeypatch.setattr(HomologadorManualView, "OUTPUT_PATH", str(tmp_path))
    proc = vista._sanitas_processor
    proc.homologador_insumos_path = sanitas_homologadores["insumos"]
    assert proc.load_homologador_insumos()

    ruta = vista._generar_objeciones_sanitas(_df_estructurado())

    assert ruta is not None
    assert os.path.basename(ruta).startswith("Objeciones_SANITAS_")
    obj = pd.read_excel(ruta)
    assert list(obj.columns) == OBJECIONES_COLUMNS
    assert len(obj) == 2
    assert obj.loc[0, "SLNSERPRO"] == "CUPS001"
    assert obj.loc[0, "CRNCONOBJ"] == "AU3002"
    assert obj.loc[1, "SLNSERPRO"] == "PROD-A"
    assert obj.loc[1, "CRNCONOBJ"] == "TA0601"
    assert obj.loc[1, "CRDOBSERV"].startswith("MVC EN")


def test_manual_sin_estructura_no_genera(vista, tmp_path, monkeypatch):
    from app.ui.views.homologador_manual_view import HomologadorManualView

    monkeypatch.setattr(HomologadorManualView, "OUTPUT_PATH", str(tmp_path))
    df = pd.DataFrame([{"OTRA": 1}])
    assert vista._generar_objeciones_sanitas(df) is None


def test_manual_sin_processor_no_genera(vista):
    vista._sanitas_processor = None
    assert vista._generar_objeciones_sanitas(_df_estructurado()) is None
