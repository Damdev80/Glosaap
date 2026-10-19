"""
Tests para el servicio Mix Excel (mix_excel_service.py).

Este módulo contiene tests unitarios para verificar:
- Inicialización del servicio
- Carga de archivos Excel
- Transferencia de datos
"""
import pytest
import pandas as pd
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from app.core.mix_excel_service import MixExcelService


class TestMixExcelServiceInit:
    """Tests para la inicialización del servicio."""
    
    def test_service_creation(self):
        """Crea el servicio correctamente"""
        service = MixExcelService()
        assert service is not None
    
    def test_source_df_initially_none(self):
        """source_df es None inicialmente"""
        service = MixExcelService()
        assert service.source_df is None
    
    def test_dest_df_initially_none(self):
        """dest_df es None inicialmente"""
        service = MixExcelService()
        assert service.dest_df is None
    
    def test_source_file_initially_none(self):
        """source_file es None inicialmente"""
        service = MixExcelService()
        assert service.source_file is None
    
    def test_dest_file_initially_none(self):
        """dest_file es None inicialmente"""
        service = MixExcelService()
        assert service.dest_file is None


class TestMixExcelServiceLoadFile:
    """Tests para carga de archivos."""
    
    def test_cargar_source_file(self, tmp_path):
        """Carga archivo fuente"""
        # Crear archivo Excel de prueba
        file_path = tmp_path / "source.xlsx"
        df = pd.DataFrame({
            'columna1': [1, 2, 3],
            'columna2': ['a', 'b', 'c']
        })
        df.to_excel(file_path, index=False)
        
        service = MixExcelService()
        success, columns, message = service.cargar_archivo(str(file_path), "source")
        
        assert success is True
        assert 'columna1' in columns
        assert 'columna2' in columns
    
    def test_cargar_dest_file(self, tmp_path):
        """Carga archivo destino"""
        file_path = tmp_path / "dest.xlsx"
        df = pd.DataFrame({
            'col_a': [10, 20],
            'col_b': [100, 200]
        })
        df.to_excel(file_path, index=False)
        
        service = MixExcelService()
        success, columns, message = service.cargar_archivo(str(file_path), "dest")
        
        assert success is True
        assert service.dest_df is not None
        assert service.dest_file == str(file_path)
    
    def test_cargar_archivo_nonexistent(self):
        """Error al cargar archivo inexistente"""
        service = MixExcelService()
        success, columns, message = service.cargar_archivo("/no/existe.xlsx", "source")
        
        assert success is False
        assert columns == []
        assert "Error" in message
    
    def test_cargar_archivo_returns_row_count(self, tmp_path):
        """Mensaje incluye número de filas"""
        file_path = tmp_path / "test.xlsx"
        df = pd.DataFrame({'col': range(10)})
        df.to_excel(file_path, index=False)
        
        service = MixExcelService()
        success, columns, message = service.cargar_archivo(str(file_path), "source")
        
        assert "10 filas" in message


class TestMixExcelServiceTransfer:
    """Tests para transferencia de datos."""
    
    def test_transferir_without_files_fails(self):
        """transferir_datos falla sin archivos cargados"""
        service = MixExcelService()
        
        success, matches, message = service.transferir_datos(
            "col1", "ref1", "col2", "ref2", "adj"
        )
        
        assert success is False
        assert "Carga ambos archivos" in message
    
    def test_transferir_with_source_only_fails(self, tmp_path):
        """transferir_datos falla con solo archivo fuente"""
        file_path = tmp_path / "source.xlsx"
        pd.DataFrame({'col': [1]}).to_excel(file_path, index=False)
        
        service = MixExcelService()
        service.cargar_archivo(str(file_path), "source")
        
        success, matches, message = service.transferir_datos(
            "col", "col", "col", "col", "col"
        )
        
        assert success is False


class TestMixExcelServiceMethods:
    """Tests para métodos del servicio."""
    
    def test_has_cargar_archivo(self):
        """Tiene método cargar_archivo"""
        assert hasattr(MixExcelService, 'cargar_archivo')
    
    def test_has_transferir_datos(self):
        """Tiene método transferir_datos"""
        assert hasattr(MixExcelService, 'transferir_datos')


class TestMixExcelServiceClass:
    """Tests para la clase en general."""
    
    def test_is_class(self):
        """MixExcelService es una clase"""
        assert isinstance(MixExcelService, type)
    
    def test_has_docstring(self):
        """La clase tiene docstring"""
        assert MixExcelService.__doc__ is not None


class TestMixExcelServiceDataTypes:
    """Tests para tipos de datos."""
    
    def test_cargar_archivo_returns_tuple(self, tmp_path):
        """cargar_archivo retorna tupla"""
        file_path = tmp_path / "test.xlsx"
        pd.DataFrame({'col': [1]}).to_excel(file_path, index=False)
        
        service = MixExcelService()
        result = service.cargar_archivo(str(file_path), "source")
        
        assert isinstance(result, tuple)
        assert len(result) == 3
    
    def test_transferir_datos_returns_tuple(self):
        """transferir_datos retorna tupla"""
        service = MixExcelService()
        result = service.transferir_datos(
            "col1", "ref1", "col2", "ref2", "adj"
        )
        
        assert isinstance(result, tuple)
        assert len(result) == 3


class TestMixExcelServiceTolerance:
    """Tests para tolerancia en comparaciones."""
    
    def test_default_tolerance(self):
        """Tolerancia por defecto es 0.05 (5%)"""
        import inspect
        sig = inspect.signature(MixExcelService.transferir_datos)
        params = sig.parameters
        
        assert 'tolerance' in params
        assert params['tolerance'].default == 0.05

    def _make_service(self, source_vals, dest_adj_vals):
        service = MixExcelService()
        service.source_df = pd.DataFrame({
            "valor": source_vals,
            "ref": ["F1"] * len(source_vals),
        })
        service.dest_df = pd.DataFrame({
            "out": [0] * len(dest_adj_vals),
            "ref": ["F1"] * len(dest_adj_vals),
            "ady": dest_adj_vals,
        })
        service.source_file = "src.xlsx"
        service.dest_file = "dst.xlsx"
        return service

    def test_tolerance_plus_4_pct_matches(self):
        """Valores +4% con tolerance=0.05 deben matchear"""
        service = self._make_service([100.0, 200.0], [104.0, 208.0])
        success, matches, _ = service.transferir_datos(
            "valor", "ref", "out", "ref", "ady", tolerance=0.05
        )
        assert success is True
        assert matches == 2
        assert sorted(service.dest_df["out"].tolist()) == [100, 200]

    def test_tolerance_minus_4_pct_matches(self):
        """Valores -4% con tolerance=0.05 deben matchear"""
        service = self._make_service([100.0, 200.0], [96.0, 192.0])
        success, matches, _ = service.transferir_datos(
            "valor", "ref", "out", "ref", "ady", tolerance=0.05
        )
        assert success is True
        assert matches == 2

    def test_tolerance_plus_6_pct_no_match(self):
        """Valores +6% con tolerance=0.05 no deben matchear"""
        service = self._make_service([100.0, 200.0], [106.0, 212.0])
        success, matches, _ = service.transferir_datos(
            "valor", "ref", "out", "ref", "ady", tolerance=0.05
        )
        assert success is True
        assert matches == 0

    def test_tolerance_minus_6_pct_no_match(self):
        """Valores -6% con tolerance=0.05 no deben matchear"""
        service = self._make_service([100.0, 200.0], [94.0, 188.0])
        success, matches, _ = service.transferir_datos(
            "valor", "ref", "out", "ref", "ady", tolerance=0.05
        )
        assert success is True
        assert matches == 0


class TestMixExcelServiceRounding:
    """Tests para reparto proporcional sin error acumulado."""

    def test_reparto_suma_exacta(self):
        """La suma repartida cuadra exacta (última fila absorbe diferencia)"""
        service = MixExcelService()
        service.source_df = pd.DataFrame({"valor": [100.0], "ref": ["F1"]})
        service.dest_df = pd.DataFrame({
            "out": [0, 0, 0],
            "ref": ["F1", "F1", "F1"],
            "ady": [1.0, 1.0, 1.0],
        })
        service.source_file = "src.xlsx"
        service.dest_file = "dst.xlsx"

        success, matches, _ = service.transferir_datos(
            "valor", "ref", "out", "ref", "ady", tolerance=0.05
        )
        assert success is True
        assert matches == 3
        assert int(service.dest_df["out"].sum()) == 100

    def test_reparto_dos_filas_impar(self):
        """Reparto 10 en 2 filas iguales suma 10"""
        service = MixExcelService()
        service.source_df = pd.DataFrame({"valor": [10.0], "ref": ["F1"]})
        service.dest_df = pd.DataFrame({
            "out": [0, 0],
            "ref": ["F1", "F1"],
            "ady": [1.0, 1.0],
        })
        service.source_file = "src.xlsx"
        service.dest_file = "dst.xlsx"

        success, matches, _ = service.transferir_datos(
            "valor", "ref", "out", "ref", "ady", tolerance=0.05
        )
        assert success is True
        assert int(service.dest_df["out"].sum()) == 10


class TestMixExcelServiceGuardar:
    """Tests para backup y output_path en guardar_destino."""

    def test_guardar_crea_backup(self, tmp_path):
        """Guardar sin output_path crea .bak antes de sobreescribir"""
        dest = tmp_path / "dest.xlsx"
        pd.DataFrame({"a": [1, 2]}).to_excel(dest, index=False)

        service = MixExcelService()
        service.cargar_archivo(str(dest), "dest")
        service.dest_df = pd.DataFrame({"a": [9, 9]})

        success, _ = service.guardar_destino()
        assert success is True
        assert (tmp_path / "dest.xlsx.bak").exists()
        assert pd.read_excel(dest)["a"].tolist() == [9, 9]

    def test_guardar_output_path_no_sobreescribe(self, tmp_path):
        """Guardar con output_path no modifica el original"""
        dest = tmp_path / "dest.xlsx"
        pd.DataFrame({"a": [1, 2]}).to_excel(dest, index=False)
        out = tmp_path / "salida.xlsx"

        service = MixExcelService()
        service.cargar_archivo(str(dest), "dest")
        service.dest_df = pd.DataFrame({"a": [7, 8]})

        success, _ = service.guardar_destino(output_path=str(out))
        assert success is True
        assert out.exists()
        assert pd.read_excel(out)["a"].tolist() == [7, 8]
        # Original intacto en disco
        assert pd.read_excel(dest)["a"].tolist() == [1, 2]
        # Sin backup cuando se usa output_path
        assert not (tmp_path / "dest.xlsx.bak").exists()
