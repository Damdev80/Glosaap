"""
Tests para coosalud_processor.py
Cubre: lógica crítica de procesamiento de archivos
"""
import pytest
import pandas as pd
from app.service.processors.coosalud_processor import CoosaludProcessor


class TestCoosaludProcessor:
    """Tests para CoosaludProcessor"""
    
    @pytest.fixture
    def processor(self, tmp_path):
        """Crea un procesador básico con homologador temporal vacío"""
        # Crear archivo homologador temporal vacío
        homolog_path = tmp_path / "homologador.xlsx"
        empty_df = pd.DataFrame({
            'Código Servicio de la ERP': [],
            'Código producto en DGH': [],
            'COD_SERV_FACT': []
        })
        empty_df.to_excel(homolog_path, index=False)
        
        return CoosaludProcessor(homologador_path=str(homolog_path))
    
    @pytest.fixture
    def processor_with_homologador(self, sample_homologador_df, tmp_path):
        """Crea un procesador con homologador cargado"""
        # Guardar homologador en archivo temporal
        homolog_path = tmp_path / "homologador.xlsx"
        sample_homologador_df.to_excel(homolog_path, index=False)
        
        # Crear procesador con ruta al homologador
        proc = CoosaludProcessor(homologador_path=str(homolog_path))
        proc.load_homologador()
        
        return proc
    
    # ==================== TESTS DE IDENTIFICACIÓN ====================
    
    def test_extract_factura_number_valid(self, processor):
        """Extrae correctamente el número de factura"""
        filename = "DETALLE FC12345.xlsx"
        result = processor._extract_factura_number(filename)
        assert result == "FC12345"
    
    def test_extract_factura_number_lowercase(self, processor):
        """Extrae número con minúsculas"""
        filename = "detalle fc67890.xlsx"
        result = processor._extract_factura_number(filename)
        assert result == "FC67890"
    
    def test_extract_factura_number_invalid(self, processor):
        """Retorna None para archivos sin número de factura"""
        filename = "archivo_sin_numero.xlsx"
        result = processor._extract_factura_number(filename)
        assert result is None
    
    def test_identify_file_pairs(self, processor, tmp_path):
        """Identifica correctamente pares de archivos"""
        # Crear archivos temporales
        files = []
        for fc_num in ["100", "200"]:
            detalle = tmp_path / f"DETALLE FC{fc_num}.xlsx"
            glosa = tmp_path / f"GLOSAS FC{fc_num}.xlsx"
            
            pd.DataFrame({'col': [1]}).to_excel(detalle, index=False)
            pd.DataFrame({'col': [1]}).to_excel(glosa, index=False)
            
            files.append(str(detalle))
            files.append(str(glosa))
        
        # Agregar archivo de devolución (debe ignorarse)
        devolucion = tmp_path / "DEVOLUCION FC300.xlsx"
        pd.DataFrame({'col': [1]}).to_excel(devolucion, index=False)
        files.append(str(devolucion))
        
        result = processor.identify_file_pairs(files)
        
        assert len(result) == 2  # Solo 2 pares válidos
        assert result[0]["factura"] == "FC100"
        assert result[1]["factura"] == "FC200"
    
    def test_identify_file_pairs_missing_glosa(self, processor, tmp_path):
        """Reporta archivos DETALLE sin GLOSA"""
        detalle = tmp_path / "DETALLE FC100.xlsx"
        pd.DataFrame({'col': [1]}).to_excel(detalle, index=False)
        
        result = processor.identify_file_pairs([str(detalle)])
        
        assert len(result) == 0  # No hay pares completos
        assert len(processor.warnings) > 0  # Debe haber warning
    
    # ==================== TESTS DE MERGE CON GLOSA ====================
    
    def test_prepare_glosa_merge_prioritizes_fa(self, processor):
        """Prioriza códigos que empiezan con FA (mayor prioridad)"""
        glosa_df = pd.DataFrame({
            'id_detalle': [1, 1, 1],
            'codigo_glosa': ['XX123', 'FA456', 'SO789'],
            'justificacion_glosa': ['Just 1', 'Just 2', 'Just 3']
        })
        
        result = processor._prepare_glosa_merge(glosa_df)
        
        # Debe haber solo 1 fila para id_detalle=1
        assert len(result) == 1
        # Debe priorizar FA456 (FA > SO > AU > CO > CL > TA)
        assert result.loc[0, 'codigo_glosa'] == 'FA456'
    
    def test_prepare_glosa_merge_prioritizes_so(self, processor):
        """Prioriza SO si no hay FA"""
        glosa_df = pd.DataFrame({
            'id_detalle': [1, 1],
            'codigo_glosa': ['XX123', 'SO789'],
            'justificacion_glosa': ['Just 1', 'Just 2']
        })
        
        result = processor._prepare_glosa_merge(glosa_df)
        
        assert result.loc[0, 'codigo_glosa'] == 'SO789'
    
    def test_prepare_glosa_merge_prioritizes_au(self, processor):
        """Prioriza AU si no hay FA ni SO"""
        glosa_df = pd.DataFrame({
            'id_detalle': [1, 1],
            'codigo_glosa': ['XX123', 'AU999'],
            'justificacion_glosa': ['Just 1', 'Just 2']
        })
        
        result = processor._prepare_glosa_merge(glosa_df)
        
        assert result.loc[0, 'codigo_glosa'] == 'AU999'

    def test_prepare_glosa_merge_prioritizes_cl(self, processor):
        """Prioriza CL si no hay FA, SO ni AU"""
        glosa_df = pd.DataFrame({
            'id_detalle': [1, 1],
            'codigo_glosa': ['XX123', 'CL999'],
            'justificacion_glosa': ['Just 1', 'Just 2']
        })
        
        result = processor._prepare_glosa_merge(glosa_df)
        
        assert result.loc[0, 'codigo_glosa'] == 'CL999'
    
    def test_prepare_glosa_merge_default_when_no_priority(self, processor):
        """Usa el primero si no hay códigos prioritarios"""
        glosa_df = pd.DataFrame({
            'id_detalle': [1, 1],
            'codigo_glosa': ['XX123', 'YY456'],
            'justificacion_glosa': ['Just 1', 'Just 2']
        })
        
        result = processor._prepare_glosa_merge(glosa_df)
        
        # Debe usar el primero
        assert result.loc[0, 'codigo_glosa'] == 'XX123'
    
    def test_prepare_glosa_merge_concatenates_justifications(self, processor):
        """Concatena justificaciones con //"""
        glosa_df = pd.DataFrame({
            'id_detalle': [1, 1, 1],
            'codigo_glosa': ['XX1', 'XX2', 'XX3'],
            'justificacion_glosa': ['Just A', 'Just B', 'Just C']
        })
        
        result = processor._prepare_glosa_merge(glosa_df)
        
        justification = result.loc[0, 'justificacion_glosa']
        assert 'Just A' in justification
        assert 'Just B' in justification
        assert 'Just C' in justification
        assert '//' in justification
    
    def test_prepare_glosa_merge_removes_duplicate_justifications(self, processor):
        """Elimina justificaciones duplicadas"""
        glosa_df = pd.DataFrame({
            'id_detalle': [1, 1, 1],
            'codigo_glosa': ['XX1', 'XX2', 'XX3'],
            'justificacion_glosa': ['Misma', 'Misma', 'Diferente']
        })
        
        result = processor._prepare_glosa_merge(glosa_df)
        
        justification = result.loc[0, 'justificacion_glosa']
        # "Misma" debe aparecer solo 1 vez
        parts = justification.split(' // ')
        assert parts.count('Misma') == 1
        assert 'Diferente' in justification
    
    def test_prepare_glosa_merge_handles_multiple_ids(self, processor):
        """Maneja múltiples id_detalle correctamente"""
        glosa_df = pd.DataFrame({
            'id_detalle': [1, 1, 2, 2, 3],
            'codigo_glosa': ['XX1', 'AU1', 'SO2', 'XX2', 'CL3'],
            'justificacion_glosa': ['J1', 'J2', 'J3', 'J4', 'J5']
        })
        
        result = processor._prepare_glosa_merge(glosa_df)
        
        assert len(result) == 3  # Debe haber 3 filas (una por id_detalle)
        
        # Verificar priorización correcta
        row_1 = result[result['id_detalle'] == 1].iloc[0]
        assert row_1['codigo_glosa'] == 'AU1'
        
        row_2 = result[result['id_detalle'] == 2].iloc[0]
        assert row_2['codigo_glosa'] == 'SO2'
        
        row_3 = result[result['id_detalle'] == 3].iloc[0]
        assert row_3['codigo_glosa'] == 'CL3'
    
    # ==================== TESTS DE HOMOLOGACIÓN ====================
    
    def test_homologate_with_valid_codes(self, processor_with_homologador, sample_detalle_df):
        """Homologa correctamente códigos que existen"""
        result = processor_with_homologador._homologate_detalle(sample_detalle_df)
        
        # Verificar que se agregaron las columnas
        assert "Codigo homologado DGH" in result.columns
        assert "Codigo no homologado" in result.columns
        
        # Verificar homologaciones correctas (primeros 2 existen)
        assert result.loc[0, "Codigo homologado DGH"] == "CUPS001"
        assert result.loc[0, "Codigo no homologado"] == ""
        
        assert result.loc[1, "Codigo homologado DGH"] == "CUPS002"
        assert result.loc[1, "Codigo no homologado"] == ""
    
    def test_homologate_with_invalid_codes(self, processor_with_homologador, sample_detalle_df):
        """Marca como NO HOMOLOGADO códigos inexistentes"""
        result = processor_with_homologador._homologate_detalle(sample_detalle_df)
        
        # El código 999999 no existe en el homologador
        assert result.loc[2, "Codigo homologado DGH"] == ""
        assert result.loc[2, "Codigo no homologado"] == "999999"
    
    def test_homologate_without_homologador(self, processor, sample_detalle_df):
        """Maneja caso sin homologador cargado"""
        result = processor._homologate_detalle(sample_detalle_df)
        
        # Todos deben estar marcados como no homologados
        assert all(result["Codigo homologado DGH"] == "")
        assert all(result["Codigo no homologado"] != "")
    
    # ==================== TESTS DE INTEGRACIÓN ====================
    
    def test_homologate_full_integration(self, processor_with_homologador, sample_detalle_df, sample_glosa_df):
        """Test de integración completo del método homologate()"""
        data = {
            'detalle': sample_detalle_df.copy(),
            'glosa': sample_glosa_df.copy()
        }
        
        result = processor_with_homologador.homologate(data)
        
        # Verificar que ambas hojas existen
        assert 'detalle' in result
        assert 'glosa' in result
        
        detalle = result['detalle']
        
        # Verificar que se agregaron columnas de homologación
        assert 'Codigo homologado DGH' in detalle.columns
        assert 'Codigo no homologado' in detalle.columns
        
        # Verificar que se agregaron columnas de glosa
        assert 'codigo_glosa' in detalle.columns
        assert 'justificacion_glosa' in detalle.columns
        
        # Verificar merge correcto
        # id_detalle=1 tiene 2 glosas, debe priorizar AU456
        row_1 = detalle[detalle['id_detalle'] == 1].iloc[0]
        assert row_1['codigo_glosa'] == 'AU456'
        assert '//' in row_1['justificacion_glosa']  # Concatenadas
    
    def test_validate_files_missing_detalle(self, processor):
        """Valida que falle sin archivo DETALLE"""
        files = {"glosa": "path/to/glosa.xlsx"}
        
        result = processor.validate_files(files)
        
        assert result is False
        assert len(processor.errors) > 0
    
    def test_validate_files_missing_glosa(self, processor):
        """Valida que falle sin archivo GLOSA"""
        files = {"detalle": "path/to/detalle.xlsx"}
        
        result = processor.validate_files(files)
        
        assert result is False
        assert len(processor.errors) > 0
    
    def test_save_to_excel(self, processor, sample_detalle_df, sample_glosa_df, tmp_path):
        """Verifica que guarde correctamente en Excel"""
        data = {
            'detalle': sample_detalle_df,
            'glosa': sample_glosa_df
        }
        
        output_path = tmp_path / "resultado.xlsx"
        
        result = processor.save_to_excel(data, str(output_path))
        
        assert result is True
        assert output_path.exists()
        
        # Verificar que tiene las 2 hojas
        loaded = pd.read_excel(output_path, sheet_name=None)
        assert 'Detalles' in loaded
        assert 'Glosa' in loaded


# ==================== EXTENSIÓN T2.3 (tmp_path + mocks, sin red) ====================

import os as _os_coo
from unittest.mock import MagicMock as _MagicMock_coo


class _FakeAttachmentServiceCoo:
    """Fake mínimo: dict fecha-por-archivo, sin tocar disco/red."""

    def __init__(self, mapping):
        self.file_metadata = dict(mapping or {})

    def get_file_metadata(self, file_path):
        return self.file_metadata.get(file_path)


def _make_homologador_minimo_coo(path):
    df = pd.DataFrame({
        'Código Servicio de la ERP': ['890201', '890301'],
        'Código producto en DGH': ['CUPS001', 'CUPS002'],
        'COD_SERV_FACT': ['FACT001', 'FACT002'],
    })
    df.to_excel(str(path), index=False)
    return str(path)


def _make_par_detalle_glosa_coo(tmp_path, factura="FC100"):
    detalle_path = tmp_path / f"DETALLE {factura}.xlsx"
    glosa_path = tmp_path / f"GLOSAS {factura}.xlsx"
    detalle_df = pd.DataFrame({
        'id_detalle': [1, 2],
        'codigo_servicio': ['890201', '890301'],
        'numero_factura': [factura, factura],
        'valor_glosado': [15000.50, 20000.00],
        'numero_glosa': ['G1', 'G2'],
    })
    glosa_df = pd.DataFrame({
        'id_detalle': [1, 2],
        'codigo_glosa': ['AU123', 'TA456'],
        'justificacion_glosa': ['Falta autorizacion', 'Tarifa no pactada'],
    })
    detalle_df.to_excel(str(detalle_path), index=False)
    glosa_df.to_excel(str(glosa_path), index=False)
    return str(detalle_path), str(glosa_path)


class TestCoosaludProcessGlosasTmp:
    """process_glosas con par sintético mínimo + homologador mínimo."""

    def test_process_glosas_par_minimo_con_fake_attachment(self, tmp_path):
        hom_path = _make_homologador_minimo_coo(tmp_path / "hom.xlsx")
        det, glo = _make_par_detalle_glosa_coo(tmp_path, factura="FC100")
        out_dir = tmp_path / "out"
        out_dir.mkdir()

        proc = CoosaludProcessor(homologador_path=hom_path)
        fake = _FakeAttachmentServiceCoo({det: {"email_date": "2024-05-01 10:00:00"}})

        result_data, message = proc.process_glosas(
            [det, glo], output_dir=str(out_dir), attachment_service=fake
        )

        assert result_data is not None
        assert "detalle" in result_data and "glosa" in result_data
        detalle = result_data["detalle"]
        assert len(detalle) == 2
        # Homologación aplicada
        assert detalle.loc[0, "Codigo homologado DGH"] == "CUPS001"
        assert detalle.loc[1, "Codigo homologado DGH"] == "CUPS002"
        # Merge de glosa por id_detalle
        assert "codigo_glosa" in detalle.columns
        assert "justificacion_glosa" in detalle.columns
        # Fecha individual por archivo desde el fake
        assert "fecha_correo" in detalle.columns
        assert all(detalle["fecha_correo"] == "2024-05-01 10:00:00")
        assert "[OK]" in message
        # Archivos guardados en out_dir
        generados = list(out_dir.glob("*.xlsx"))
        assert len(generados) >= 2

    def test_process_glosas_con_email_date_fallback(self, tmp_path):
        hom_path = _make_homologador_minimo_coo(tmp_path / "hom.xlsx")
        det, glo = _make_par_detalle_glosa_coo(tmp_path, factura="FC200")
        out_dir = tmp_path / "out2"
        out_dir.mkdir()

        proc = CoosaludProcessor(homologador_path=hom_path)
        result_data, message = proc.process_glosas(
            [det, glo], output_dir=str(out_dir),
            email_date="2024-01-15 00:00:00",
        )

        assert result_data is not None
        detalle = result_data["detalle"]
        assert all(detalle["fecha_correo"] == "2024-01-15 00:00:00")

    def test_process_glosas_sin_pares_retorna_error(self, tmp_path):
        hom_path = _make_homologador_minimo_coo(tmp_path / "hom.xlsx")
        devol = tmp_path / "DEVOLUCION FC300.xlsx"
        pd.DataFrame({'col': [1]}).to_excel(str(devol), index=False)
        out_dir = tmp_path / "out3"
        out_dir.mkdir()

        proc = CoosaludProcessor(homologador_path=hom_path)
        result_data, message = proc.process_glosas(
            [str(devol)], output_dir=str(out_dir)
        )

        assert result_data is None
        assert "[ERROR]" in message
        assert len(proc.errors) > 0

    def test_process_glosas_lista_vacia_retorna_error(self, tmp_path):
        hom_path = _make_homologador_minimo_coo(tmp_path / "hom.xlsx")
        proc = CoosaludProcessor(homologador_path=hom_path)
        result_data, message = proc.process_glosas([], output_dir=str(tmp_path))
        assert result_data is None
        assert "[ERROR]" in message


class TestCoosaludObjecionesTmp:
    """_generar_archivo_objeciones y _procesar_au_ta con datos sintéticos."""

    def _detalle_para_objeciones(self):
        return pd.DataFrame({
            'numero_factura': ['FC100', 'FC100'],
            'codigo_glosa': ['AU123', 'TA456'],
            'justificacion_glosa': ['Falta autorizacion', 'Tarifa'],
            'Codigo homologado DGH': ['CUPS001', 'CUPS001'],
            'valor_glosado': [15000.50, 5000.25],
            'fecha_correo': ['2024-05-01 10:00:00', '2024-05-01 10:00:00'],
        })

    def test_generar_archivo_objeciones_ok(self, tmp_path):
        hom_path = _make_homologador_minimo_coo(tmp_path / "hom.xlsx")
        proc = CoosaludProcessor(homologador_path=hom_path)
        out_dir = tmp_path / "obj"
        out_dir.mkdir()

        detalle_df = self._detalle_para_objeciones()
        ruta = proc._generar_archivo_objeciones(
            detalle_df, str(out_dir), email_date="2024-05-01 10:00:00"
        )

        assert ruta is not None
        assert _os_coo.path.exists(ruta)
        cargado = pd.read_excel(ruta, sheet_name="OBJECIONES")
        for col in ["CDCONSEC", "CRNCXC", "CROFECOBJ", "CRNCONOBJ",
                    "SLNSERPRO", "CROVALOBJ", "CRDOBSERV"]:
            assert col in cargado.columns
        # CRNCXC unificado FC0000{digitos}
        assert all(str(v).startswith("FC0000") for v in cargado["CRNCXC"])
        # CROFECOBJ solo fecha D/M/A derivada de fecha_correo
        assert all(v == "01/05/2024" for v in cargado["CROFECOBJ"])

    def test_generar_archivo_objeciones_vacio_retorna_none(self, tmp_path):
        hom_path = _make_homologador_minimo_coo(tmp_path / "hom.xlsx")
        proc = CoosaludProcessor(homologador_path=hom_path)
        ruta = proc._generar_archivo_objeciones(
            pd.DataFrame(), str(tmp_path)
        )
        assert ruta is None

    def test_procesar_au_ta_combina_y_elimina_ta(self, tmp_path):
        hom_path = _make_homologador_minimo_coo(tmp_path / "hom.xlsx")
        proc = CoosaludProcessor(homologador_path=hom_path)
        df_obj = pd.DataFrame({
            'CRNCXC': ['FC0000100', 'FC0000100', 'FC0000200'],
            'SLNSERPRO': ['CUPS001', 'CUPS001', 'CUPS002'],
            'CRNCONOBJ': ['AU123', 'TA456', 'AU789'],
            'CRDOBSERV': ['Obs AU', 'Obs TA', 'Solo AU'],
        })
        result = proc._procesar_au_ta(df_obj)
        # La fila TA se elimina: 3 -> 2
        assert len(result) == 2
        fila_au = result[result['CRNCONOBJ'] == 'AU123'].iloc[0]
        assert 'Obs AU' in fila_au['CRDOBSERV']
        assert 'Obs TA' in fila_au['CRDOBSERV']
        assert '//' in fila_au['CRDOBSERV']
        assert 'TA456' not in result['CRNCONOBJ'].values

    def test_procesar_au_ta_sin_columnas_retorna_igual(self, tmp_path):
        hom_path = _make_homologador_minimo_coo(tmp_path / "hom.xlsx")
        proc = CoosaludProcessor(homologador_path=hom_path)
        df_obj = pd.DataFrame({'A': [1, 2]})
        result = proc._procesar_au_ta(df_obj)
        assert result.equals(df_obj)
