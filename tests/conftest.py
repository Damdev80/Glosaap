"""
Configuración global de pytest
Fixtures compartidas entre todos los tests
"""
import pytest
import pandas as pd
from pathlib import Path
import os
import sys

# Agregar el root del proyecto al path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


@pytest.fixture
def sample_detalle_df():
    """DataFrame de ejemplo para DETALLE"""
    return pd.DataFrame({
        'id_detalle': [1, 2, 3],
        'codigo_servicio': ['890201', '890301', '999999'],
        'descripcion': ['Consulta', 'Procedimiento', 'Desconocido'],
        'valor': [50000, 150000, 100000]
    })


@pytest.fixture
def sample_glosa_df():
    """DataFrame de ejemplo para GLOSA"""
    return pd.DataFrame({
        'id_detalle': [1, 1, 2],
        'codigo_glosa': ['XX123', 'AU456', 'SO789'],
        'justificacion_glosa': ['Falta doc', 'Sin autorización', 'Observación']
    })


@pytest.fixture
def sample_glosa_with_duplicates():
    """DataFrame con id_detalle duplicados para probar merge"""
    return pd.DataFrame({
        'id_detalle': [1, 1, 1, 2, 3],
        'codigo_glosa': ['XX123', 'AU456', 'SO789', 'CL111', 'ZZ999'],
        'justificacion_glosa': ['Just 1', 'Just 2', 'Just 3', 'Just 4', 'Just 5']
    })


@pytest.fixture
def sample_homologador_df():
    """DataFrame de homologación de ejemplo"""
    return pd.DataFrame({
        'Código Servicio de la ERP': ['890201', '890301'],
        'Código producto en DGH': ['CUPS001', 'CUPS002'],
        'COD_SERV_FACT': ['FACT001', 'FACT002']
    })


@pytest.fixture
def temp_excel_file(tmp_path):
    """Crea un archivo Excel temporal para testing"""
    file_path = tmp_path / "test_file.xlsx"
    df = pd.DataFrame({'col1': [1, 2, 3], 'col2': ['a', 'b', 'c']})
    df.to_excel(file_path, index=False)
    return file_path


@pytest.fixture
def mock_file_pairs(tmp_path):
    """Crea archivos de prueba para pares DETALLE/GLOSA"""
    # Crear archivos temporales
    detalle_path = tmp_path / "DETALLE FC12345.xlsx"
    glosa_path = tmp_path / "GLOSAS FC12345.xlsx"
    
    detalle_df = pd.DataFrame({
        'id_detalle': [1, 2],
        'codigo_servicio': ['890201', '890301'],
        'valor': [50000, 100000]
    })
    
    glosa_df = pd.DataFrame({
        'id_detalle': [1],
        'codigo_glosa': ['AU123'],
        'justificacion_glosa': ['Falta documento']
    })
    
    detalle_df.to_excel(detalle_path, index=False)
    glosa_df.to_excel(glosa_path, index=False)
    
    return {
        'detalle': str(detalle_path),
        'glosa': str(glosa_path),
        'factura': 'FC12345'
    }
