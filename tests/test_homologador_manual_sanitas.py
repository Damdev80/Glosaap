"""
Tests del homologador manual para Sanitas (dos vías de homologación).

Cubre:
- get_homologador_paths() devuelve los dos archivos para Sanitas.
- Vía normal (ERP -> DGH) con floats enteros de Excel.
- Vía insumos (cascada CUM / IUM RDA / CODIGO PRODUCTO) con claves flexibles.
- Detección de filas INSUMOS según modo (Auto / Normal / Insumos).
"""
from types import SimpleNamespace

import pandas as pd
import pytest

from app.config.settings import get_homologador_paths
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
    """Vista del homologador manual con los dos homologadores cargados."""
    page = SimpleNamespace(overlay=[])
    view = HomologadorManualView(page=page)
    view.selected_eps = "SANITAS"
    view.sanitas_modo = "Normal"
    view._sanitas_processor = SanitasProcessor(
        homologador_path=sanitas_homologadores["normal"],
        homologador_insumos_path=sanitas_homologadores["insumos"],
    )
    assert view._sanitas_processor.load_homologador()
    assert view._sanitas_processor.load_homologador_insumos()
    view.df_homologacion = view._sanitas_processor.homologador_df
    return view


# ==================== RUTAS ====================

def test_get_homologador_paths_sanitas_dos_archivos():
    paths = get_homologador_paths("sanitas")
    assert len(paths) == 2
    assert paths[0].endswith("sanitas_homologador_2.xlsx")
    assert paths[1].endswith("sanitas_homologador.xlsx")


def test_get_homologador_paths_otras_eps_un_archivo():
    paths = get_homologador_paths("coosalud")
    assert len(paths) == 1
    assert "coosalud_homologacion" in paths[0]


# ==================== VÍA NORMAL (ERP -> DGH) ====================

def test_homologacion_normal_match(vista):
    proc = vista._sanitas_processor
    assert proc.homologar_codigo_servicio("890201", es_insumo=False) == "CUPS001"


def test_homologacion_normal_sin_match_vacia(vista):
    proc = vista._sanitas_processor
    assert proc.homologar_codigo_servicio("999999", es_insumo=False) == ""


def test_homologacion_normal_float_entero_de_excel(vista):
    proc = vista._sanitas_processor
    assert proc.homologar_codigo_servicio(7.0, es_insumo=False) == "CUPS007"


# ==================== VÍA INSUMOS (CUM / IUM / PRODUCTO) ====================

def test_insumos_por_cum(vista):
    proc = vista._sanitas_processor
    assert proc.homologar_codigo_servicio("CUM123", es_insumo=True) == "PROD-A"


def test_insumos_por_ium(vista):
    proc = vista._sanitas_processor
    assert proc.homologar_codigo_servicio("IUM111", es_insumo=True) == "PROD-A"


def test_insumos_por_producto_directo(vista):
    proc = vista._sanitas_processor
    assert proc.homologar_codigo_servicio("PROD-B", es_insumo=True) == "PROD-B"


def test_insumos_clave_flexible_sin_guiones(vista):
    proc = vista._sanitas_processor
    assert proc.homologar_codigo_servicio("cum-123", es_insumo=True) == "PROD-A"


def test_insumos_sin_match_vacia(vista):
    proc = vista._sanitas_processor
    assert proc.homologar_codigo_servicio("ZZZ", es_insumo=True) == ""


# ==================== DETECCIÓN DE INSUMOS ====================

def test_es_insumo_etiqueta_normalizada():
    assert SanitasProcessor.es_insumo("  INSUMOS Y MEDICAMENTOS INTRAHOSPITALARIOS ") is True
    assert SanitasProcessor.es_insumo("insumos y medicamentos intrahospitalarios") is True
    assert SanitasProcessor.es_insumo("CONSULTA EXTERNA") is False
    assert SanitasProcessor.es_insumo(None) is False


def test_es_insumo_para_fila_segun_modo(vista):
    df = pd.DataFrame(
        {
            "PROC": [
                "INSUMOS Y MEDICAMENTOS INTRAHOSPITALARIOS",
                "CONSULTA EXTERNA",
            ]
        }
    )
    vista.columna_procedimiento = "PROC"

    vista.sanitas_modo = "Auto"
    assert vista._es_insumo_para_fila(df, 0) is True
    assert vista._es_insumo_para_fila(df, 1) is False

    vista.sanitas_modo = "Insumos"
    assert vista._es_insumo_para_fila(df, 0) is True
    assert vista._es_insumo_para_fila(df, 1) is True

    vista.sanitas_modo = "Normal"
    assert vista._es_insumo_para_fila(df, 0) is False
    assert vista._es_insumo_para_fila(df, 1) is False


def test_es_insumo_para_fila_otra_eps_siempre_false(vista):
    vista.selected_eps = "MUTUALSER"
    df = pd.DataFrame({"PROC": ["INSUMOS Y MEDICAMENTOS INTRAHOSPITALARIOS"]})
    vista.columna_procedimiento = "PROC"
    vista.sanitas_modo = "Insumos"
    assert vista._es_insumo_para_fila(df, 0) is False
