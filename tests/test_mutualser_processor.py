"""
Tests para el procesador de Mutualser (mutualser_processor.py).

Este módulo contiene tests unitarios para verificar:
- Inicialización del procesador
- Estructura de columnas requeridas
- Validación de archivos
- Procesamiento de datos
"""
import pytest
import pandas as pd
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from app.core.mutualser_processor import MutualserProcessor


class TestMutualserProcessorInit:
    """Tests para la inicialización del procesador."""
    
    @patch('os.path.exists', return_value=False)
    @patch('os.makedirs')
    def test_processor_creation(self, mock_makedirs, mock_exists):
        """Crea el procesador correctamente"""
        processor = MutualserProcessor(output_dir='test_output')
        assert processor is not None
    
    @patch('os.path.exists', return_value=False)
    @patch('os.makedirs')
    def test_processor_has_output_dir(self, mock_makedirs, mock_exists):
        """Tiene directorio de salida"""
        processor = MutualserProcessor(output_dir='my_output')
        assert processor.output_dir == 'my_output'
    
    @patch('os.path.exists', return_value=False)
    @patch('os.makedirs')
    def test_processor_has_df_consolidado(self, mock_makedirs, mock_exists):
        """Tiene df_consolidado inicialmente None"""
        processor = MutualserProcessor()
        assert processor.df_consolidado is None
    
    @patch('os.path.exists', return_value=False)
    @patch('os.makedirs')
    def test_processor_has_archivos_procesados(self, mock_makedirs, mock_exists):
        """Tiene lista de archivos procesados vacía"""
        processor = MutualserProcessor()
        assert processor.archivos_procesados == []
    
    @patch('os.path.exists', return_value=False)
    @patch('os.makedirs')
    def test_processor_has_errores(self, mock_makedirs, mock_exists):
        """Tiene lista de errores vacía"""
        processor = MutualserProcessor()
        assert processor.errores == []


class TestMutualserColumnasRequeridas:
    """Tests para columnas requeridas."""
    
    def test_columnas_requeridas_defined(self):
        """Columnas requeridas están definidas"""
        assert MutualserProcessor.COLUMNAS_REQUERIDAS
        assert len(MutualserProcessor.COLUMNAS_REQUERIDAS) > 0
    
    def test_numero_factura_required(self):
        """Número de factura es requerida"""
        assert 'Número de factura' in MutualserProcessor.COLUMNAS_REQUERIDAS
    
    def test_numero_glosa_required(self):
        """Número de glosa es requerida"""
        assert 'Número de glosa' in MutualserProcessor.COLUMNAS_REQUERIDAS
    
    def test_tecnologia_required(self):
        """Tecnología es requerida"""
        assert 'Tecnología' in MutualserProcessor.COLUMNAS_REQUERIDAS
    
    def test_cantidad_facturada_required(self):
        """Cantidad facturada es requerida"""
        assert 'Cantidad facturada' in MutualserProcessor.COLUMNAS_REQUERIDAS
    
    def test_valor_facturado_required(self):
        """Valor Facturado es requerida"""
        assert 'Valor Facturado' in MutualserProcessor.COLUMNAS_REQUERIDAS
    
    def test_concepto_glosa_required(self):
        """Concepto de glosa es requerida"""
        assert 'Concepto de glosa' in MutualserProcessor.COLUMNAS_REQUERIDAS
    
    def test_codigo_glosa_required(self):
        """Código de glosa es requerida"""
        assert 'Código de glosa' in MutualserProcessor.COLUMNAS_REQUERIDAS
    
    def test_observacion_required(self):
        """Observacion es requerida"""
        assert 'Observacion' in MutualserProcessor.COLUMNAS_REQUERIDAS


class TestMutualserHomologacionPath:
    """Tests para path de homologación."""
    
    def test_homologacion_path_defined(self):
        """Path de homologación está definido"""
        assert MutualserProcessor.HOMOLOGACION_PATH
    
    def test_homologacion_path_is_network(self):
        """Path es ruta de red"""
        assert MutualserProcessor.HOMOLOGACION_PATH.startswith(r"\\")
    
    def test_homologacion_path_is_xlsx(self):
        """Path apunta a archivo xlsx"""
        assert MutualserProcessor.HOMOLOGACION_PATH.endswith('.xlsx')
    
    @patch('os.path.exists', return_value=False)
    @patch('os.makedirs')
    def test_custom_homologacion_path(self, mock_makedirs, mock_exists):
        """Puede especificar path de homologación personalizado"""
        custom_path = r"C:\custom\homologacion.xlsx"
        processor = MutualserProcessor(homologacion_path=custom_path)
        # El procesador intenta cargar el archivo y puede modificar el path
        assert processor is not None


class TestMutualserDataStructures:
    """Tests para estructuras de datos del procesador."""
    
    @patch('os.path.exists', return_value=False)
    @patch('os.makedirs')
    def test_df_homologacion_attribute(self, mock_makedirs, mock_exists):
        """Tiene atributo df_homologacion"""
        processor = MutualserProcessor()
        assert hasattr(processor, 'df_homologacion')
    
    @patch('os.path.exists', return_value=False)
    @patch('os.makedirs')
    def test_todos_cod_serv_fact_attribute(self, mock_makedirs, mock_exists):
        """Tiene atributo _todos_cod_serv_fact"""
        processor = MutualserProcessor()
        assert hasattr(processor, '_todos_cod_serv_fact')


class TestMutualserProcessorMethods:
    """Tests para métodos del procesador."""
    
    @patch('os.path.exists', return_value=False)
    @patch('os.makedirs')
    def test_has_cargar_homologacion(self, mock_makedirs, mock_exists):
        """Tiene método _cargar_homologacion"""
        processor = MutualserProcessor()
        assert hasattr(processor, '_cargar_homologacion')
    
    def test_has_procesar_archivo(self):
        """Tiene método procesar_archivo"""
        assert hasattr(MutualserProcessor, 'procesar_archivo')


class TestMutualserConstants:
    """Tests para constantes del procesador."""
    
    def test_columnas_count(self):
        """Número correcto de columnas requeridas"""
        # Debe tener todas las columnas necesarias para procesar
        assert len(MutualserProcessor.COLUMNAS_REQUERIDAS) >= 10
    
    def test_columnas_all_strings(self):
        """Todas las columnas son strings"""
        for col in MutualserProcessor.COLUMNAS_REQUERIDAS:
            assert isinstance(col, str)
    
    def test_columnas_no_empty(self):
        """Ninguna columna está vacía"""
        for col in MutualserProcessor.COLUMNAS_REQUERIDAS:
            assert col.strip() != ""


class TestMutualserOutputDir:
    """Tests para directorio de salida."""
    
    @patch('os.path.exists', return_value=False)
    @patch('os.makedirs')
    def test_default_output_dir(self, mock_makedirs, mock_exists):
        """Directorio de salida por defecto es 'outputs'"""
        processor = MutualserProcessor()
        assert processor.output_dir == 'outputs'
    
    @patch('os.path.exists', return_value=False)
    @patch('os.makedirs')
    def test_creates_output_directory(self, mock_makedirs, mock_exists):
        """Crea directorio de salida si no existe"""
        MutualserProcessor(output_dir='new_output')
        mock_makedirs.assert_called()


class TestMutualserProcessorClass:
    """Tests para la clase en general."""
    
    def test_is_class(self):
        """MutualserProcessor es una clase"""
        assert isinstance(MutualserProcessor, type)
    
    def test_has_docstring(self):
        """La clase tiene docstring"""
        assert MutualserProcessor.__doc__ is not None


# ==================== EXTENSIÓN T2.3 (tmp_path, sin red) ====================

import os as _os_mut


def _write_homologador_mutualser_tmp(path):
    import pandas as pd
    df = pd.DataFrame({
        'Código Servicio de la ERP': ['890201', '890301'],
        'Código producto en DGH': ['CUPS001', 'CUPS002'],
        'COD_SERV_FACT': ['CUPS001', 'CUPS002'],
    })
    df.to_excel(str(path), index=False)
    return str(path)


def _write_mutualser_input_tmp(path, filas):
    """Escribe archivo Mutualser sintético con fila FECHA + encabezado real."""
    import pandas as pd
    header = list(MutualserProcessor.COLUMNAS_REQUERIDAS)
    rows = [
        ["REPORTE DE GLOSAS MUTUALSER"] + [None] * (len(header) - 1),
        ["FECHA", "01/01/2024"] + [None] * (len(header) - 2),
        header,
    ]
    rows.extend(filas)
    pd.DataFrame(rows).to_excel(str(path), index=False, header=False)
    return str(path)


def _fila_mutualser(fact="F001", glosa="G001", tec="890201", concepto="Concepto A",
                    cod_glosa="AU001", obs="Obs A"):
    return [fact, glosa, tec, 1, 50000, 1, 10000, concepto, cod_glosa, obs, "01/01/2024"]


class TestMutualserLoadHomologadorTmp:
    """load_homologador con xlsx real en tmp_path."""

    def test_load_homologador_tmp_ok(self, tmp_path):
        hom = _write_homologador_mutualser_tmp(tmp_path / "hom.xlsx")
        out = tmp_path / "out_load"
        proc = MutualserProcessor(output_dir=str(out), homologacion_path=hom)
        assert proc.df_homologacion is not None
        assert len(proc.df_homologacion) == 2
        assert proc.load_homologador() is True
        assert proc.df_homologacion is not None
        assert "CUPS001" in (proc._todos_cod_serv_fact or set())

    def test_load_homologador_tmp_inexistente_falla_explicito(self, tmp_path):
        faltante = str(tmp_path / "noexiste.xlsx")
        out = tmp_path / "out_load_miss"
        proc = MutualserProcessor(output_dir=str(out), homologacion_path=faltante)
        assert proc.df_homologacion is None
        assert proc.homologador_df is None
        assert proc.load_homologador() is False
        assert len(proc.errors) > 0


class TestMutualserBuscarCodigoTmp:
    """_buscar_codigo_homologado hit/miss sin red."""

    def _proc_con_hom(self, tmp_path):
        hom = _write_homologador_mutualser_tmp(tmp_path / "hom.xlsx")
        out = tmp_path / "out_buscar"
        return MutualserProcessor(output_dir=str(out), homologacion_path=hom)

    def test_buscar_hit(self, tmp_path):
        proc = self._proc_con_hom(tmp_path)
        assert proc._buscar_codigo_homologado("890201") == "CUPS001"
        assert proc._buscar_codigo_homologado("890301") == "CUPS002"

    def test_buscar_miss_retorna_vacio(self, tmp_path):
        proc = self._proc_con_hom(tmp_path)
        assert proc._buscar_codigo_homologado("999999") == ""

    def test_buscar_nulos_retorna_vacio(self, tmp_path):
        import math
        proc = self._proc_con_hom(tmp_path)
        assert proc._buscar_codigo_homologado(None) == ""
        assert proc._buscar_codigo_homologado(float("nan")) == ""
        assert proc._buscar_codigo_homologado("") == ""

    def test_buscar_sin_homologacion_retorna_vacio(self, tmp_path):
        out = tmp_path / "out_sinhom"
        proc = MutualserProcessor(
            output_dir=str(out),
            homologacion_path=str(tmp_path / "faltante.xlsx"),
        )
        assert proc.df_homologacion is None
        assert proc._buscar_codigo_homologado("890201") == ""


class TestMutualserMultiplesArchivosTmp:
    """procesar_multiples_archivos con 2 archivos sintéticos."""

    def test_procesar_dos_archivos_sinteticos(self, tmp_path):
        hom = _write_homologador_mutualser_tmp(tmp_path / "hom.xlsx")
        out = tmp_path / "out_multi"
        f1 = _write_mutualser_input_tmp(
            tmp_path / "rep1.xlsx",
            [_fila_mutualser("F001", "G001", "890201"),
             _fila_mutualser("F001", "G002", "890301")],
        )
        f2 = _write_mutualser_input_tmp(
            tmp_path / "rep2.xlsx",
            [_fila_mutualser("F002", "G003", "890201")],
        )
        proc = MutualserProcessor(output_dir=str(out), homologacion_path=hom)
        consolidado = proc.procesar_multiples_archivos([f1, f2])

        assert consolidado is not None
        assert len(consolidado) == 3
        assert len(proc.archivos_procesados) == 2
        assert "Número de factura" in consolidado.columns

    def test_procesar_lista_vacia_retorna_none(self, tmp_path):
        hom = _write_homologador_mutualser_tmp(tmp_path / "hom.xlsx")
        out = tmp_path / "out_multi_vacio"
        proc = MutualserProcessor(output_dir=str(out), homologacion_path=hom)
        assert proc.procesar_multiples_archivos([]) is None


class TestMutualserExportarTmp:
    """exportar_consolidado verifica xlsx de salida en tmp_path."""

    def test_exportar_consolidado_genera_xlsx(self, tmp_path):
        hom = _write_homologador_mutualser_tmp(tmp_path / "hom.xlsx")
        out = tmp_path / "out_exp"
        f1 = _write_mutualser_input_tmp(
            tmp_path / "a.xlsx", [_fila_mutualser("F001", "G001", "890201")]
        )
        f2 = _write_mutualser_input_tmp(
            tmp_path / "b.xlsx", [_fila_mutualser("F002", "G002", "890301")]
        )
        proc = MutualserProcessor(output_dir=str(out), homologacion_path=hom)
        proc.procesar_multiples_archivos([f1, f2])

        resultado = proc.exportar_consolidado(nombre_archivo="consolidado_test.xlsx")

        assert resultado is not None
        output_path, objeciones_path = resultado
        assert _os_mut.path.exists(output_path)
        assert output_path.endswith("consolidado_test.xlsx")
        import pandas as pd
        cargado = pd.read_excel(output_path)
        assert len(cargado) == 2
        assert "Codigo homologado DGH" in cargado.columns
        # Homologación efectiva con homologador mínimo
        assert "CUPS001" in cargado["Codigo homologado DGH"].values
        # Objeciones también se genera en el mismo output_dir
        assert objeciones_path is not None
        assert _os_mut.path.exists(objeciones_path)

    def test_exportar_sin_datos_retorna_none(self, tmp_path):
        hom = _write_homologador_mutualser_tmp(tmp_path / "hom.xlsx")
        out = tmp_path / "out_exp_vacio"
        proc = MutualserProcessor(output_dir=str(out), homologacion_path=hom)
        assert proc.exportar_consolidado() is None
