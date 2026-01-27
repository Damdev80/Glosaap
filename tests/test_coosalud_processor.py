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
