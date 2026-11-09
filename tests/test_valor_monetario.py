"""Regresión de valores monetarios (CROVALOBJ) en todas las EPS.

Mutualser entrega el valor glosado como texto tipo ``"$\\xa03.404"``
(peso + espacio duro + separador de miles). El parser anterior veía un
solo punto y lo trataba como decimal: ``3.404`` -> ``3.404``, que Excel
en español muestra como ``3,404``. Debe salir ``3404``.

El parser es compartido por BaseProcessor, así que se valida en los
cuatro procesadores (Mutualser, Coosalud, Sanitas y Previsora) y con una
exportación real de objeciones de Mutualser.
"""
import openpyxl
import pandas as pd
import pytest

from app.core.mutualser_processor import MutualserProcessor
from app.service.processors.coosalud_processor import CoosaludProcessor
from app.service.processors.previsora_processor import PrevisoraProcessor
from app.service.processors.sanitas_processor import SanitasProcessor

# (texto de entrada, valor esperado)
CASOS_MONETARIOS = [
    ("$\xa03.404", 3404.0),
    ("$\xa0220.000", 220000.0),
    ("$\xa01.904", 1904.0),
    ("$\xa010.080", 10080.0),
    ("$\xa052.000", 52000.0),
    ("$\xa01.040", 1040.0),
    ("$\xa0133.952", 133952.0),
    ("$\xa0245.000", 245000.0),
    ("1.234,56", 1234.56),
    ("1,234.56", 1234.56),
    ("1500.50", 1500.5),
    ("0,00", 0.0),
    ("37.900,00", 37900.0),
    ("1.234.567", 1234567.0),
    ("1,234,567.89", 1234567.89),
    ("($ 1.500,50)", -1500.5),
    ("1.500,50-", -1500.5),
    ("", 0.0),
    (None, 0.0),
    (3404, 3404.0),
    (3404.5, 3404.5),
]


def _procesador(nombre: str, tmp_path):
    """Instancia cada procesador sin depender de la red."""
    faltante = str(tmp_path / "homologador_inexistente.xlsx")
    if nombre == "mutualser":
        return MutualserProcessor(
            output_dir=str(tmp_path / "out"), homologacion_path=faltante
        )
    if nombre == "coosalud":
        return CoosaludProcessor(homologador_path=faltante)
    if nombre == "sanitas":
        return SanitasProcessor(homologador_path=faltante)
    if nombre == "previsora":
        return PrevisoraProcessor(homologador_path=faltante)
    raise AssertionError(nombre)


@pytest.mark.parametrize("eps", ["mutualser", "coosalud", "sanitas", "previsora"])
@pytest.mark.parametrize("texto,esperado", CASOS_MONETARIOS)
def test_parser_monetario_en_todas_las_eps(eps, texto, esperado, tmp_path):
    proc = _procesador(eps, tmp_path)
    assert proc._obtener_valor_numerico(texto) == pytest.approx(esperado)


# ==================== Exportación real de Mutualser ====================


def _escribir_homologador(path):
    pd.DataFrame(
        {
            "Código Servicio de la ERP": ["890201"],
            "Código producto en DGH": ["CUPS001"],
            "COD_SERV_FACT": ["CUPS001"],
        }
    ).to_excel(path, index=False)
    return str(path)


def _fila_mutualser(factura, valor_glosado):
    return [
        factura,
        f"G-{factura}",
        "890201",
        1,
        50000,
        1,
        valor_glosado,
        "Concepto",
        "AU001",
        "Observación",
        "01/01/2024",
    ]


def _escribir_entrada_mutualser(path, filas):
    header = list(MutualserProcessor.COLUMNAS_REQUERIDAS)
    rows = [
        ["REPORTE DE GLOSAS MUTUALSER"] + [None] * (len(header) - 1),
        ["FECHA", "01/01/2024"] + [None] * (len(header) - 2),
        header,
    ]
    rows.extend(filas)
    pd.DataFrame(rows).to_excel(path, index=False, header=False)
    return str(path)


def test_objeciones_mutualser_exporta_miles_sin_decimales(tmp_path):
    hom = _escribir_homologador(tmp_path / "hom.xlsx")
    entrada = _escribir_entrada_mutualser(
        tmp_path / "reporte.xlsx",
        [
            _fila_mutualser("F001", "$\xa03.404"),
            _fila_mutualser("F002", "$\xa010.080"),
            _fila_mutualser("F003", "$\xa0220.000"),
        ],
    )
    out = tmp_path / "out"
    proc = MutualserProcessor(output_dir=str(out), homologacion_path=hom)
    assert proc.procesar_multiples_archivos([entrada]) is not None

    resultado = proc.exportar_consolidado()
    assert resultado is not None
    _consolidado, objeciones = resultado
    assert objeciones

    # El valor debe quedar numérico y sin el punto de miles interpretado
    # como decimal (3404, no 3.404).
    cargado = pd.read_excel(objeciones)
    assert sorted(cargado["CROVALOBJ"].tolist()) == [3404.0, 10080.0, 220000.0]

    wb = openpyxl.load_workbook(objeciones, data_only=True, read_only=True)
    ws = wb[wb.sheetnames[0]]
    rows = ws.iter_rows(values_only=True)
    header = list(next(rows))
    idx = header.index("CROVALOBJ")
    valores = [row[idx] for row in rows]
    wb.close()
    assert all(isinstance(v, (int, float)) for v in valores)
    assert sorted(float(v) for v in valores) == [3404.0, 10080.0, 220000.0]
