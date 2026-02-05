"""
Procesador específico para archivos de Coosalud EPS

Coosalud envía archivos de:
- GLOSAS: 2 archivos por factura (DETALLE FC{numero}.xlsx + GLOSAS FC{numero}.xlsx)
- DEVOLUCIONES: 2 archivos (diferente estructura) - SE IGNORAN

Archivos de GLOSAS:
- DETALLE FC{numero}.xlsx: contiene codigo_servicio (a homologar)
- GLOSAS FC{numero}.xlsx: contiene codigo_glosa (resolución 2284)

El procesador agrupa los archivos por número de factura y procesa TODOS los pares.
El resultado se guarda en un Excel con 2 hojas: "Detalles" y "Glosa"
"""
import os
import re
import pandas as pd
from datetime import datetime
from typing import List, Dict, Tuple, Optional, Any

from .base_processor import BaseProcessor


class CoosaludProcessor(BaseProcessor):
    """Procesador de archivos de Coosalud EPS"""
    
    # Identificadores para reconocer los archivos por nombre
    DETALLE_KEYWORDS = ["detalle"]
    GLOSA_KEYWORDS = ["glosa"]
    DEVOLUCION_KEYWORDS = ["devolucion", "devolución"]  # Archivos a IGNORAR
    
    # Columnas exactas de los archivos de Coosalud
    DETALLE_CODE_COLUMN = "codigo_servicio"  # Código del servicio a homologar
    GLOSA_CODE_COLUMN = "codigo_glosa"  # Código resolución 2284
    
    # Mapeo de primer dígito a prefijo de código de glosa
    CODIGO_GLOSA_PREFIJOS = {
        "1": "FA",
        "2": "TA",
        "3": "SO",
        "4": "AU",
        "5": "CO",
        "6": "CL"
    }
    
    # Casos especiales de homologación de codigo_glosa
    CODIGO_GLOSA_ESPECIALES = {
        "430": "AU2103"
    }
    
    def __init__(self, homologador_path: Optional[str] = None):
        
        super().__init__(homologador_path or "")
        self.detalle_df: Optional[pd.DataFrame] = None
        self.glosa_df: Optional[pd.DataFrame] = None
    
    def _homologar_codigo_glosa(self, codigo: str) -> str:
        """
        Homologa un codigo_glosa numérico a formato estándar según resolución 2284.
        
        Aplica las siguientes reglas de transformación:
        - Si el código comienza con letra: se retorna sin modificación
        - Si comienza con número: se aplica PREFIJO + resto_números + "01" 
        - Casos especiales predefinidos (ej: "430" -> "AU2103")
        
        Mapeo de primer dígito a prefijo:
        - "1" -> "FA" (Factor de riesgo)
        - "2" -> "TA" (Tarifas)
        - "3" -> "SO" (Soporte)
        - "4" -> "AU" (Auditoría)
        - "5" -> "CO" (Cobertura)
        - "6" -> "CL" (Clínica)
        
        Args:
            codigo (str): Código de glosa original (puede ser numérico o alfanumérico)
            
        Returns:
            str: Código homologado según resolución 2284
            
        Examples:
            >>> processor = CoosaludProcessor()
            >>> 
            >>> # Casos numéricos estándar
            >>> processor._homologar_codigo_glosa("203")
            'TA0301'
            >>> processor._homologar_codigo_glosa("15")
            'FA1501'
            >>> processor._homologar_codigo_glosa("4")
            'AU0401'
            >>> 
            >>> # Caso especial
            >>> processor._homologar_codigo_glosa("430")
            'AU2103'
            >>> 
            >>> # Códigos ya formateados (no se modifican)
            >>> processor._homologar_codigo_glosa("AU01")
            'AU01'
            >>> processor._homologar_codigo_glosa("FA0301")
            'FA0301'
            >>> 
            >>> # Casos edge con padding
            >>> processor._homologar_codigo_glosa("17")
            'FA0701'
            >>> processor._homologar_codigo_glosa("205")
            'TA0501'
            >>> 
            >>> # Casos inválidos
            >>> processor._homologar_codigo_glosa("")
            ''
            >>> processor._homologar_codigo_glosa(None)
            ''
            >>> processor._homologar_codigo_glosa("9999")
            '9999'  # Primer dígito no mapeado, retorna original
        
        Note:
            - Se asegura que el resto numérico tenga al menos 2 dígitos (padding con ceros)
            - Los códigos vacíos, None o NaN se convierten en string vacío
            - Si el primer dígito no está en el mapeo, retorna el código original
            - Es case-insensitive y elimina espacios automáticamente
        """
        if not codigo:
            return ""
        
        codigo_str = str(codigo).strip().upper()
        
        # Si está vacío o es NaN
        if not codigo_str or codigo_str in ['NAN', 'NONE', '']:
            return ""
        
        # Si ya comienza con letra, retornar tal cual
        if codigo_str[0].isalpha():
            return codigo_str
        
        # Verificar casos especiales primero
        if codigo_str in self.CODIGO_GLOSA_ESPECIALES:
            return self.CODIGO_GLOSA_ESPECIALES[codigo_str]
        
        # Si comienza con número, aplicar regla de homologación
        primer_digito = codigo_str[0]
        
        if primer_digito in self.CODIGO_GLOSA_PREFIJOS:
            prefijo = self.CODIGO_GLOSA_PREFIJOS[primer_digito]
            resto = codigo_str[1:]  # Dígitos después del primero
            
            # Asegurar que resto tenga al menos 2 dígitos
            if len(resto) < 2:
                resto = resto.zfill(2)
            
            # Construir código: PREFIJO + resto + "01"
            codigo_homologado = f"{prefijo}{resto}01"
            return codigo_homologado
        
        # Si el primer dígito no está en el mapeo, retornar original
        return codigo_str
            
    def _extract_factura_number(self, filename: str) -> Optional[str]:
        """
        Extrae el número de factura del nombre del archivo.
        Ej: "DETALLE FC12345.xlsx" -> "FC12345"
            "GLOSAS FC12345.xlsx" -> "FC12345"
        """
        # Patrón: FC seguido de números
        match = re.search(r'(FC\d+)', filename, re.IGNORECASE)
        if match:
            return match.group(1).upper()
        return None
        
    def identify_file_pairs(self, file_paths: List[str]) -> List[Dict[str, str]]:
        """
        Identifica y empareja archivos de Coosalud por número de factura para procesamiento masivo.
        
        Los archivos de Coosalud vienen en pares por cada factura:
        - DETALLE FC{número}.xlsx: contiene códigos de servicio a homologar
        - GLOSAS FC{número}.xlsx: contiene códigos de glosa (resolución 2284)
        
        Funcionalidades principales:
        - Extrae números de factura de nombres como "DETALLE FC12345.xlsx"
        - Empareja archivos del mismo número de factura
        - Ignora automáticamente archivos de devolución
        - Reporta archivos sin pareja para diagnóstico
        - Maneja grandes volúmenes con progreso visible
        
        Args:
            file_paths (List[str]): Lista completa de rutas de archivos a clasificar
            
        Returns:
            List[Dict[str, str]]: Lista de pares identificados, cada uno con:
                - "detalle": ruta del archivo DETALLE FC{num}.xlsx
                - "glosa": ruta del archivo GLOSAS FC{num}.xlsx  
                - "factura": número de factura extraído (ej: "FC12345")
                
        Examples:
            >>> processor = CoosaludProcessor()
            >>> 
            >>> # Ejemplo básico con archivos pareados
            >>> archivos = [
            ...     "/tmp/DETALLE FC12345.xlsx",
            ...     "/tmp/GLOSAS FC12345.xlsx",
            ...     "/tmp/DETALLE FC67890.xlsx",
            ...     "/tmp/GLOSAS FC67890.xlsx",
            ...     "/tmp/DEVOLUCION FC99999.xlsx"  # Se ignora
            ... ]
            >>> pares = processor.identify_file_pairs(archivos)
            >>> print(len(pares))  # 2
            >>> print(pares[0])
            {
                'detalle': '/tmp/DETALLE FC12345.xlsx',
                'glosa': '/tmp/GLOSAS FC12345.xlsx', 
                'factura': 'FC12345'
            }
            >>> 
            >>> # Procesamiento de directorio completo
            >>> import glob
            >>> archivos_coosalud = glob.glob("/ruta/coosalud/*.xlsx")
            >>> pares = processor.identify_file_pairs(archivos_coosalud)
            >>> print(f"Encontrados {len(pares)} pares de factura para procesar")
            >>> 
            >>> # Análisis detallado de resultados
            >>> for i, par in enumerate(pares[:3]):  # Primeros 3
            ...     print(f"Par {i+1}: Factura {par['factura']}")
            ...     print(f"  DETALLE: {os.path.basename(par['detalle'])}")
            ...     print(f"  GLOSA: {os.path.basename(par['glosa'])}")
            >>> 
            >>> # Verificar warnings de archivos sin pareja
            >>> if processor.warnings:
            ...     for warning in processor.warnings:
            ...         print(f"⚠️ {warning}")
        
        Note:
            - Se ignoran automáticamente archivos que contengan "devolucion" en el nombre
            - Archivos sin número de factura se agrupan por nombre completo 
            - Se muestra progreso cada 100 archivos para grandes volúmenes
            - Los warnings se almacenan en self.warnings para revisión posterior
            - Case-insensitive para palabras clave (DETALLE, GLOSA, DEVOLUCION)
        """
        excel_files = [f for f in file_paths if f.endswith(('.xlsx', '.xls', '.xlsm', '.csv'))]
        
        print(f"[DIR] Total archivos recibidos: {len(excel_files)}")
        
        # Clasificar archivos por tipo y número de factura
        detalle_files = {}  # {factura_num: path}
        glosa_files = {}    # {factura_num: path}
        archivos_devolucion_count = 0
        archivos_otros_count = 0
        
        for i, f in enumerate(excel_files):
            fname = os.path.basename(f).lower()
            
            # Mostrar progreso cada 100 archivos
            if (i + 1) % 100 == 0:
                print(f"  ... clasificando {i + 1}/{len(excel_files)} archivos")
            
            # Si tiene "devolucion" en el nombre, ignorar
            if any(kw in fname for kw in self.DEVOLUCION_KEYWORDS):
                archivos_devolucion_count += 1
                continue
            
            # Extraer número de factura
            factura_num = self._extract_factura_number(fname)
            
            # Clasificar por tipo
            if any(kw in fname for kw in self.DETALLE_KEYWORDS):
                if factura_num:
                    detalle_files[factura_num] = f
                else:
                    # Sin número de factura, usar nombre completo como clave
                    detalle_files[fname] = f
            elif any(kw in fname for kw in self.GLOSA_KEYWORDS):
                if factura_num:
                    glosa_files[factura_num] = f
                else:
                    glosa_files[fname] = f
            else:
                archivos_otros_count += 1
        
        print(f"  [!] Ignorados: {archivos_devolucion_count} devoluciones, {archivos_otros_count} otros")
        print(f"  [OK] Archivos DETALLE: {len(detalle_files)}")
        print(f"  [OK] Archivos GLOSA: {len(glosa_files)}")
        
        # Emparejar archivos por número de factura
        pairs = []
        matched_facturas = set(detalle_files.keys()) & set(glosa_files.keys())
        
        for factura in sorted(matched_facturas):
            pairs.append({
                "detalle": detalle_files[factura],
                "glosa": glosa_files[factura],
                "factura": factura
            })
        
        # Reportar archivos sin pareja
        detalles_sin_glosa = set(detalle_files.keys()) - matched_facturas
        glosas_sin_detalle = set(glosa_files.keys()) - matched_facturas
        
        if detalles_sin_glosa:
            self.warnings.append(f"{len(detalles_sin_glosa)} archivos DETALLE sin GLOSA correspondiente")
            print(f"  [!] DETALLE sin pareja: {len(detalles_sin_glosa)}")
            
        if glosas_sin_detalle:
            self.warnings.append(f"{len(glosas_sin_detalle)} archivos GLOSA sin DETALLE correspondiente")
            print(f"  [!] GLOSA sin pareja: {len(glosas_sin_detalle)}")
        
        print(f"[DIR] Pares completos encontrados: {len(pairs)}")
        
        return pairs
    
    def identify_files(self, file_paths: List[str]) -> Dict[str, str]:
        """
        Método legacy - identifica solo UN par (para compatibilidad)
        Usa identify_file_pairs para procesar múltiples pares
        """
        pairs = self.identify_file_pairs(file_paths)
        if pairs:
            return pairs[0]  # Devolver solo el primer par
        return {}
    
    def validate_files(self, identified_files: Dict[str, str]) -> bool:
        """
        Valida que los archivos identificados sean correctos
        """
        if "detalle" not in identified_files:
            self.errors.append("No se encontró el archivo de DETALLE")
            return False
            
        if "glosa" not in identified_files:
            self.errors.append("No se encontró el archivo de GLOSA")
            return False
            
        # Verificar que los archivos existan
        for tipo, path in identified_files.items():
            if not os.path.exists(path):
                self.errors.append(f"Archivo {tipo} no existe: {path}")
                return False
                
        return True
    
    def extract_data(self, identified_files: Dict[str, str]) -> Dict[str, pd.DataFrame]:
        """
        Extrae y carga datos de los archivos DETALLE y GLOSA de Coosalud en DataFrames.
        
        Procesa un par de archivos identificados cargándolos como DataFrames de pandas
        con validación de errores y logging detallado del proceso.
        
        Args:
            identified_files (Dict[str, str]): Diccionario con rutas de archivos:
                - "detalle": ruta del archivo DETALLE FC{num}.xlsx
                - "glosa": ruta del archivo GLOSAS FC{num}.xlsx
                
        Returns:
            Dict[str, pd.DataFrame]: Diccionario con DataFrames cargados:
                - "detalle": DataFrame del archivo de detalle
                - "glosa": DataFrame del archivo de glosa
                Retorna diccionario vacío si hay errores en la carga
                
        Raises:
            Los errores se capturan y almacenan en self.errors, no se propagan
            
        Examples:
            >>> processor = CoosaludProcessor()
            >>> 
            >>> # Extraer datos de un par identificado
            >>> par = {
            ...     "detalle": "/tmp/DETALLE FC12345.xlsx",
            ...     "glosa": "/tmp/GLOSAS FC12345.xlsx"
            ... }
            >>> data = processor.extract_data(par)
            >>> 
            >>> if data:  # Si la carga fue exitosa
            ...     detalle_df = data["detalle"]
            ...     glosa_df = data["glosa"]
            ...     print(f"Detalle: {len(detalle_df)} filas, {len(detalle_df.columns)} columnas")
            ...     print(f"Glosa: {len(glosa_df)} filas, {len(glosa_df.columns)} columnas")
            ...     
            ...     # Verificar columnas esperadas
            ...     if "codigo_servicio" in detalle_df.columns:
            ...         print("✅ Archivo detalle tiene código_servicio")
            ...     if "codigo_glosa" in glosa_df.columns:
            ...         print("✅ Archivo glosa tiene código_glosa")
            ... else:
            ...     print("❌ Error en la carga de archivos")
            ...     for error in processor.errors:
            ...         print(f"   {error}")
            >>> 
            >>> # Acceso directo a atributos del processor
            >>> print(f"DataFrame detalle también disponible en processor.detalle_df")
            >>> print(f"Forma del detalle: {processor.detalle_df.shape}")
            >>> print(f"Forma de la glosa: {processor.glosa_df.shape}")
            >>> 
            >>> # Inspección rápida de estructura
            >>> if data:
            ...     print("\nColumnas DETALLE:")
            ...     print(list(data["detalle"].columns))
            ...     print("\nColumnas GLOSA:")
            ...     print(list(data["glosa"].columns))
        
        Note:
            - Los DataFrames también se almacenan en self.detalle_df y self.glosa_df
            - Se muestra información de filas cargadas para cada archivo
            - Maneja automáticamente diferentes formatos Excel (.xlsx, .xls, .xlsm)
            - Los errores de lectura se capturan y no interrumpen el flujo principal
            - Es responsabilidad del llamador verificar que el diccionario no esté vacío
        """
        data = {}
        
        try:
            # Cargar archivo de detalle
            print(f"\n[FILE] Cargando archivo de Detalle...")
            self.detalle_df = pd.read_excel(identified_files["detalle"])
            data["detalle"] = self.detalle_df
            print(f"   Filas: {len(self.detalle_df)}")
            
            # Cargar archivo de glosa
            print(f"[FILE] Cargando archivo de Glosa...")
            self.glosa_df = pd.read_excel(identified_files["glosa"])
            data["glosa"] = self.glosa_df
            print(f"   Filas: {len(self.glosa_df)}")
            
        except Exception as e:
            self.errors.append(f"Error al cargar archivos: {str(e)}")
            return {}
            
        return data
    
    def _find_code_column(self, df: pd.DataFrame, keywords: List[str]) -> Optional[str]:
        """
        Busca una columna que contenga alguna de las palabras clave
        """
        columns = df.columns.tolist()
        for col in columns:
            col_upper = str(col).upper()
            if any(kw.upper() in col_upper for kw in keywords):
                return col
        return None
    
    def _prepare_glosa_merge(self, glosa_df: pd.DataFrame) -> pd.DataFrame:
        """
        Prepara el DataFrame de glosa para el merge, manejando duplicados:
        1. Homologa codigo_glosa numéricos a formato estándar
        2. Si id_detalle se repite, concatena justificaciones con "//"
        3. Prioriza códigos NO-TA primero (FA, SO, AU, CO, CL), luego TA
        
        Args:
            glosa_df: DataFrame de glosa
            
        Returns:
            DataFrame procesado listo para merge
        """
        if "id_detalle" not in glosa_df.columns:
            return pd.DataFrame()
        
        has_codigo = "codigo_glosa" in glosa_df.columns
        has_justif = "justificacion_glosa" in glosa_df.columns
        
        if not has_codigo and not has_justif:
            return pd.DataFrame()
        
        # Agrupar por id_detalle
        result_rows = []
        
        for id_det, group in glosa_df.groupby("id_detalle"):
            row = {"id_detalle": id_det}
            
            # Procesar codigo_glosa con homologación y priorización
            if has_codigo:
                codigos_raw = group["codigo_glosa"].dropna().astype(str).tolist()
                
                # Homologar todos los códigos
                codigos_homologados = []
                for codigo in codigos_raw:
                    codigo_homolog = self._homologar_codigo_glosa(codigo)
                    if codigo_homolog and codigo_homolog not in codigos_homologados:
                        codigos_homologados.append(codigo_homolog)
                
                # Priorización: FA, SO, AU, CO, CL primero, TA al final
                # Orden de prioridad (mayor a menor): FA > SO > AU > CO > CL > TA
                prioritarios = ["FA", "SO", "AU", "CO", "CL"]
                codigo_final = None
                
                # Buscar primer código que NO sea TA
                for prefijo in prioritarios:
                    for codigo in codigos_homologados:
                        if codigo.upper().startswith(prefijo):
                            codigo_final = codigo
                            break
                    if codigo_final:
                        break
                
                # Si no hay prioritarios, buscar TA
                if not codigo_final:
                    for codigo in codigos_homologados:
                        if codigo.upper().startswith("TA"):
                            codigo_final = codigo
                            break
                
                # Si aún no hay nada, tomar el primero disponible
                if not codigo_final and codigos_homologados:
                    codigo_final = codigos_homologados[0]
                
                row["codigo_glosa"] = codigo_final if codigo_final else ""
            
            # Procesar justificacion_glosa concatenando con //
            # Orden: primero observaciones de códigos NO-TA, luego las de TA
            if has_justif:
                # Obtener justificaciones con sus códigos para ordenar
                justif_con_codigo = []
                for _, row_glosa in group.iterrows():
                    justif = row_glosa.get("justificacion_glosa")
                    codigo_raw = row_glosa.get("codigo_glosa", "")
                    
                    if pd.notna(justif) and str(justif).strip():
                        codigo_homolog = self._homologar_codigo_glosa(str(codigo_raw)) if pd.notna(codigo_raw) else ""
                        es_ta = codigo_homolog.upper().startswith("TA") if codigo_homolog else False
                        justif_con_codigo.append({
                            "justificacion": str(justif).strip(),
                            "es_ta": es_ta,
                            "codigo": codigo_homolog
                        })
                
                # Ordenar: primero NO-TA, luego TA
                justif_ordenadas = sorted(justif_con_codigo, key=lambda x: (x["es_ta"], x["codigo"]))
                
                # Eliminar duplicados manteniendo orden
                justif_unicas = []
                for item in justif_ordenadas:
                    if item["justificacion"] not in justif_unicas:
                        justif_unicas.append(item["justificacion"])
                
                row["justificacion_glosa"] = " // ".join(justif_unicas) if justif_unicas else ""
            
            result_rows.append(row)
        
        return pd.DataFrame(result_rows)
    
    def _prepare_glosa_merge_multi(self, glosa_df: pd.DataFrame, merge_columns: List[str]) -> pd.DataFrame:
        """
        Prepara el DataFrame de glosa para merge usando múltiples columnas,
        manejando duplicados y concatenando justificaciones correctamente.
        
        Args:
            glosa_df: DataFrame de glosa original
            merge_columns: Lista de columnas para agrupar (ej: ['id_cuenta', 'numero_factura', 'DocPaciente'])
            
        Returns:
            DataFrame procesado listo para merge
        """
        # Verificar que todas las columnas existan
        missing_cols = [c for c in merge_columns if c not in glosa_df.columns]
        if missing_cols:
            print(f"   [DEBUG] Columnas faltantes en glosa: {missing_cols}")
            return pd.DataFrame()
        
        has_codigo = "codigo_glosa" in glosa_df.columns
        has_justif = "justificacion_glosa" in glosa_df.columns
        
        if not has_codigo and not has_justif:
            print(f"   [DEBUG] No hay columnas codigo_glosa ni justificacion_glosa")
            return pd.DataFrame()
        
        print(f"   [DEBUG] Agrupando glosa por: {merge_columns}")
        print(f"   [DEBUG] Total filas en glosa: {len(glosa_df)}")
        
        # Agrupar por las columnas de merge
        result_rows = []
        
        for keys, group in glosa_df.groupby(merge_columns):
            # Crear diccionario base con las columnas de merge
            row: Dict[str, Any] = {}
            if isinstance(keys, tuple):
                row = dict(zip(merge_columns, keys))
            else:
                row = {merge_columns[0]: keys}
            
            print(f"   [DEBUG] Procesando grupo {keys} con {len(group)} filas")
            
            # Si hay más de 3 filas en el grupo, mostrar advertencia
            if len(group) > 3:
                print(f"   [WARN] Grupo con {len(group)} observaciones - esto puede resultar en texto muy largo")
            
            # Procesar codigo_glosa con homologación y priorización
            if has_codigo:
                codigos_raw = group["codigo_glosa"].dropna().astype(str).tolist()
                print(f"     [DEBUG] Códigos raw: {codigos_raw}")
                
                # Homologar todos los códigos
                codigos_homologados = []
                for codigo in codigos_raw:
                    codigo_homolog = self._homologar_codigo_glosa(codigo)
                    if codigo_homolog and codigo_homolog not in codigos_homologados:
                        codigos_homologados.append(codigo_homolog)
                
                print(f"     [DEBUG] Códigos homologados: {codigos_homologados}")
                
                # Priorización: FA, SO, AU, CO, CL primero, TA al final
                prioritarios = ["FA", "SO", "AU", "CO", "CL"]
                codigo_final = None
                
                for prefijo in prioritarios:
                    for codigo in codigos_homologados:
                        if codigo.upper().startswith(prefijo):
                            codigo_final = codigo
                            break
                    if codigo_final:
                        break
                
                if not codigo_final:
                    for codigo in codigos_homologados:
                        if codigo.upper().startswith("TA"):
                            codigo_final = codigo
                            break
                
                if not codigo_final and codigos_homologados:
                    codigo_final = codigos_homologados[0]
                
                row["codigo_glosa"] = codigo_final if codigo_final else ""
                print(f"     [DEBUG] Código final seleccionado: {codigo_final}")
            
            # Procesar justificacion_glosa concatenando correctamente
            if has_justif:
                # Obtener todas las justificaciones válidas
                justificaciones_raw = []
                for _, row_glosa in group.iterrows():
                    justif = row_glosa.get("justificacion_glosa")
                    codigo_raw = row_glosa.get("codigo_glosa", "")
                    
                    if pd.notna(justif) and str(justif).strip():
                        justif_text = str(justif).strip()
                        codigo_homolog = self._homologar_codigo_glosa(str(codigo_raw)) if pd.notna(codigo_raw) else ""
                        es_ta = codigo_homolog.upper().startswith("TA") if codigo_homolog else False
                        justificaciones_raw.append({
                            "justificacion": justif_text,
                            "es_ta": es_ta,
                            "codigo": codigo_homolog
                        })
                
                print(f"     [DEBUG] Justificaciones encontradas: {len(justificaciones_raw)}")
                
                # Ordenar: primero NO-TA, luego TA
                justif_ordenadas = sorted(justificaciones_raw, key=lambda x: (x["es_ta"], x["codigo"]))
                
                # Eliminar duplicados manteniendo orden
                justif_unicas = []
                for item in justif_ordenadas:
                    justif_text = item["justificacion"]
                    if justif_text not in justif_unicas:
                        justif_unicas.append(justif_text)
                
                # Concatenar con " // "
                justificacion_final = " // ".join(justif_unicas) if justif_unicas else ""
                row["justificacion_glosa"] = justificacion_final
                
                # Advertir sobre justificaciones muy largas
                if len(justificacion_final) > 2000:
                    print(f"     [WARN] Justificación muy larga ({len(justificacion_final)} caracteres) para grupo {keys}")
                    print(f"     [HINT] Considere revisar si el merge debe ser más específico (incluir código de servicio)")
                
                print(f"     [DEBUG] Justificación final (longitud: {len(justificacion_final)}): {justificacion_final[:150]}...")
            
            result_rows.append(row)
        
        print(f"   [DEBUG] Grupos procesados: {len(result_rows)}")
        return pd.DataFrame(result_rows)
    
    def _prepare_glosa_merge_by_id_detalle(self, glosa_df: pd.DataFrame, merge_columns: List[str]) -> pd.DataFrame:
        """
        Prepara el DataFrame de glosa aplicando la nueva regla de id_detalle:
        
        REGLA:
        - Si id_detalle aparece 2+ veces en GLOSA → usar esas observaciones específicas
        - Si id_detalle NO está repetido → usar esa observación única, no pegar con otras
        
        Args:
            glosa_df: DataFrame de glosa
            merge_columns: Columnas para hacer merge
            
        Returns:
            DataFrame procesado con las observaciones correctas
        """
        print(f"   [DEBUG] Aplicando nueva lógica de id_detalle...")
        
        if "id_detalle" not in glosa_df.columns:
            print(f"   [WARN] No hay columna id_detalle en GLOSA")
            return pd.DataFrame()
        
        has_codigo = "codigo_glosa" in glosa_df.columns
        has_justif = "justificacion_glosa" in glosa_df.columns
        
        if not has_codigo and not has_justif:
            print(f"   [WARN] No hay columnas de observaciones en GLOSA")
            return pd.DataFrame()
        
        # Analizar frecuencia de id_detalle
        id_detalle_counts = glosa_df['id_detalle'].value_counts()
        id_repetidos = id_detalle_counts[id_detalle_counts >= 2].index.tolist()
        id_unicos = id_detalle_counts[id_detalle_counts == 1].index.tolist()
        
        print(f"   [INFO] ID_detalle repetidos (2+): {len(id_repetidos)}")
        print(f"   [INFO] ID_detalle únicos: {len(id_unicos)}")
        
        result_rows = []
        
        # Agrupar por las columnas de merge
        for keys, group in glosa_df.groupby(merge_columns):
            # Crear diccionario base con las columnas de merge
            row: Dict[str, Any] = {}
            if isinstance(keys, tuple):
                row = dict(zip(merge_columns, keys))
            else:
                row = {merge_columns[0]: keys}
            
            # Obtener todos los id_detalle en este grupo
            ids_en_grupo = group['id_detalle'].unique()
            
            # Separar según la regla
            ids_para_pegar = []  # IDs que aparecen 2+ veces
            ids_individuales = []  # IDs que aparecen solo 1 vez
            
            for id_det in ids_en_grupo:
                if id_det in id_repetidos:
                    ids_para_pegar.append(id_det)
                else:
                    ids_individuales.append(id_det)
            
            print(f"   [DEBUG] Grupo {keys}: IDs a pegar: {len(ids_para_pegar)}, IDs individuales: {len(ids_individuales)}")
            
            # Filtrar observaciones según la regla
            filas_a_procesar = pd.DataFrame()
            
            if ids_para_pegar:
                # Solo incluir observaciones de IDs repetidos
                filas_a_procesar = group[group['id_detalle'].isin(ids_para_pegar)]
                print(f"     [RULE] Usando {len(filas_a_procesar)} observaciones de IDs repetidos")
            elif ids_individuales:
                # Si no hay IDs repetidos, tomar solo uno de los individuales
                primer_id = ids_individuales[0]
                filas_a_procesar = group[group['id_detalle'] == primer_id]
                print(f"     [RULE] Usando 1 observación del ID individual: {primer_id}")
            
            if filas_a_procesar.empty:
                print(f"     [WARN] No hay observaciones para procesar en grupo {keys}")
                row["codigo_glosa"] = ""
                row["justificacion_glosa"] = ""
            else:
                # Procesar codigo_glosa con homologación y priorización
                if has_codigo:
                    codigos_raw = filas_a_procesar["codigo_glosa"].dropna().astype(str).tolist()
                    
                    # Homologar códigos
                    codigos_homologados = []
                    for codigo in codigos_raw:
                        codigo_homolog = self._homologar_codigo_glosa(codigo)
                        if codigo_homolog and codigo_homolog not in codigos_homologados:
                            codigos_homologados.append(codigo_homolog)
                    
                    # Priorización: FA, SO, AU, CO, CL primero, TA al final
                    prioritarios = ["FA", "SO", "AU", "CO", "CL"]
                    codigo_final = None
                    
                    for prefijo in prioritarios:
                        for codigo in codigos_homologados:
                            if codigo.upper().startswith(prefijo):
                                codigo_final = codigo
                                break
                        if codigo_final:
                            break
                    
                    if not codigo_final:
                        for codigo in codigos_homologados:
                            if codigo.upper().startswith("TA"):
                                codigo_final = codigo
                                break
                    
                    if not codigo_final and codigos_homologados:
                        codigo_final = codigos_homologados[0]
                    
                    row["codigo_glosa"] = codigo_final if codigo_final else ""
                
                # Procesar justificacion_glosa - ORDENAR por prioridad de códigos
                if has_justif:
                    # Crear lista de justificaciones con sus códigos asociados
                    justif_con_codigo = []
                    for _, row_glosa in filas_a_procesar.iterrows():
                        justif = row_glosa.get("justificacion_glosa")
                        codigo_raw = row_glosa.get("codigo_glosa", "")
                        
                        if pd.notna(justif) and str(justif).strip():
                            justif_text = str(justif).strip()
                            codigo_homolog = self._homologar_codigo_glosa(str(codigo_raw)) if pd.notna(codigo_raw) else ""
                            
                            # Solo agregar si no existe (evitar duplicados)
                            ya_existe = any(item["justificacion"] == justif_text for item in justif_con_codigo)
                            if not ya_existe:
                                justif_con_codigo.append({
                                    "justificacion": justif_text,
                                    "codigo": codigo_homolog,
                                    "es_ta": codigo_homolog.upper().startswith("TA") if codigo_homolog else True
                                })
                    
                    # ORDENAR según prioridad: FA > SO > AU > CO > CL > TA
                    prioritarios = ["FA", "SO", "AU", "CO", "CL"]
                    
                    def get_priority(item):
                        codigo = item["codigo"].upper() if item["codigo"] else ""
                        
                        # Asignar prioridad numérica (menor = mayor prioridad)
                        for i, prefijo in enumerate(prioritarios):
                            if codigo.startswith(prefijo):
                                return i  # FA=0, SO=1, AU=2, CO=3, CL=4
                        
                        # TA o desconocido = menor prioridad
                        return 999
                    
                    # Ordenar justificaciones por prioridad
                    justif_ordenadas = sorted(justif_con_codigo, key=get_priority)
                    
                    # Extraer solo los textos de justificación ordenados
                    justificaciones_finales = [item["justificacion"] for item in justif_ordenadas]
                    
                    # Concatenar con " // "
                    justificacion_final = " // ".join(justificaciones_finales) if justificaciones_finales else ""
                    row["justificacion_glosa"] = justificacion_final
                    
                    print(f"     [DEBUG] Justificaciones procesadas: {len(justificaciones_finales)}")
                    if justificaciones_finales:
                        print(f"     [DEBUG] Orden aplicado: {[item['codigo'] for item in justif_ordenadas]}")
            
            result_rows.append(row)
        
        print(f"   [DEBUG] Grupos procesados con nueva regla: {len(result_rows)}")
        return pd.DataFrame(result_rows)
    
    def _prepare_glosa_merge_by_id_detalle_direct(self, glosa_df: pd.DataFrame) -> pd.DataFrame:
        """
        Prepara el DataFrame de glosa para merge DIRECTO por id_detalle.
        
        REGLA SIMPLE:
        - Agrupar por id_detalle
        - Si un id_detalle tiene múltiples observaciones → concatenar solo esas
        - Si un id_detalle tiene una sola observación → usar esa
        
        Esto garantiza que cada servicio en DETALLE reciba SOLO sus observaciones específicas.
        
        Args:
            glosa_df: DataFrame de glosa
            
        Returns:
            DataFrame con id_detalle, codigo_glosa, justificacion_glosa
        """
        print(f"   [DEBUG] Preparando merge directo por id_detalle...")
        
        if "id_detalle" not in glosa_df.columns:
            print(f"   [ERROR] No existe columna id_detalle en GLOSA")
            return pd.DataFrame()
        
        has_codigo = "codigo_glosa" in glosa_df.columns
        has_justif = "justificacion_glosa" in glosa_df.columns
        
        if not has_codigo and not has_justif:
            print(f"   [ERROR] No existen columnas de observaciones")
            return pd.DataFrame()
        
        result_rows = []
        
        # Agrupar por id_detalle (columna directa de conexión)
        for id_detalle, group in glosa_df.groupby("id_detalle"):
            row = {"id_detalle": id_detalle}
            
            # Procesar codigo_glosa con homologación y priorización
            if has_codigo:
                codigos_raw = group["codigo_glosa"].dropna().astype(str).tolist()
                
                # Homologar todos los códigos
                codigos_homologados = []
                for codigo in codigos_raw:
                    codigo_homolog = self._homologar_codigo_glosa(codigo)
                    if codigo_homolog and codigo_homolog not in codigos_homologados:
                        codigos_homologados.append(codigo_homolog)
                
                # Priorización: FA, SO, AU, CO, CL primero, TA al final
                prioritarios = ["FA", "SO", "AU", "CO", "CL"]
                codigo_final = None
                
                for prefijo in prioritarios:
                    for codigo in codigos_homologados:
                        if codigo.upper().startswith(prefijo):
                            codigo_final = codigo
                            break
                    if codigo_final:
                        break
                
                if not codigo_final:
                    for codigo in codigos_homologados:
                        if codigo.upper().startswith("TA"):
                            codigo_final = codigo
                            break
                
                if not codigo_final and codigos_homologados:
                    codigo_final = codigos_homologados[0]
                
                row["codigo_glosa"] = codigo_final if codigo_final else ""
            
            # Procesar justificacion_glosa - ORDENAR por prioridad de códigos
            if has_justif:
                # Crear lista de justificaciones con sus códigos asociados
                justif_con_codigo = []
                for _, row_glosa in group.iterrows():
                    justif = row_glosa.get("justificacion_glosa")
                    codigo_raw = row_glosa.get("codigo_glosa", "")
                    
                    if pd.notna(justif) and str(justif).strip():
                        justif_text = str(justif).strip()
                        codigo_homolog = self._homologar_codigo_glosa(str(codigo_raw)) if pd.notna(codigo_raw) else ""
                        
                        # Solo agregar si no existe (evitar duplicados)
                        ya_existe = any(item["justificacion"] == justif_text for item in justif_con_codigo)
                        if not ya_existe:
                            justif_con_codigo.append({
                                "justificacion": justif_text,
                                "codigo": codigo_homolog,
                                "es_ta": codigo_homolog.upper().startswith("TA") if codigo_homolog else True
                            })
                
                # ORDENAR según prioridad: FA > SO > AU > CO > CL > TA
                prioritarios = ["FA", "SO", "AU", "CO", "CL"]
                
                def get_priority(item):
                    codigo = item["codigo"].upper() if item["codigo"] else ""
                    
                    # Asignar prioridad numérica (menor = mayor prioridad)
                    for i, prefijo in enumerate(prioritarios):
                        if codigo.startswith(prefijo):
                            return i  # FA=0, SO=1, AU=2, CO=3, CL=4
                    
                    # TA o desconocido = menor prioridad
                    return 999
                
                # Ordenar justificaciones por prioridad
                justif_ordenadas = sorted(justif_con_codigo, key=get_priority)
                
                # Extraer solo los textos de justificación ordenados
                justificaciones_finales = [item["justificacion"] for item in justif_ordenadas]
                
                # Concatenar SOLO las justificaciones de este id_detalle específico
                justificacion_final = " // ".join(justificaciones_finales) if justificaciones_finales else ""
                row["justificacion_glosa"] = justificacion_final
            
            result_rows.append(row)
        
        print(f"   [INFO] Procesados {len(result_rows)} id_detalle únicos")
        return pd.DataFrame(result_rows)
    
    def homologate(self, data: Dict[str, pd.DataFrame]) -> Dict[str, pd.DataFrame]:
        """
        Realiza el proceso de homologación para Coosalud
        
        1. Del archivo de Detalle: homologa codigo_servicio
        2. Del archivo de Glosa: agrega fecha de proceso
        3. Agrega columnas: FECHA_PROCESO y CODIGO_NO_HOMOLOGADO
        4. Agrega a Detalles las columnas codigo_glosa y justificacion_glosa desde Glosa por id_detalle
        
        Returns:
            Diccionario con DataFrames procesados {"detalle": df, "glosa": df}
        """
        detalle_df = data.get("detalle")
        glosa_df = data.get("glosa")
        
        if detalle_df is None or glosa_df is None:
            self.errors.append("Faltan datos para homologar")
            return {}
        
        # Procesar DETALLE - agregar columnas de homologación
        print(f"\n[PROC] Procesando homologación del archivo DETALLE...")
        detalle_result = self._homologate_detalle(detalle_df)
        
        # Procesar GLOSA - agregar fecha de proceso
        print(f"[PROC] Procesando archivo GLOSA...")
        glosa_result = glosa_df.copy()
        glosa_result["FECHA_PROCESO"] = self.processing_date
        
        # Merge usando columnas comunes para traer codigo_glosa y justificacion_glosa a Detalles
        print(f"[PROC] Agregando codigo_glosa y justificacion_glosa a Detalles...")
        
        # DEBUG: Mostrar columnas disponibles
        print(f"   [DEBUG] Columnas en DETALLE: {list(detalle_result.columns)}")
        print(f"   [DEBUG] Columnas en GLOSA: {list(glosa_result.columns)}")
        
        # Buscar columnas comunes para merge
        detalle_cols = set(col.lower() for col in detalle_result.columns)
        glosa_cols = set(col.lower() for col in glosa_result.columns)
        
        # Mapeo para preservar case original
        detalle_col_map = {c.lower(): c for c in detalle_result.columns}
        
        # PRIORIDAD: usar id_detalle si existe en ambos (conexión directa)
        if 'id_detalle' in detalle_cols and 'id_detalle' in glosa_cols:
            print(f"   [INFO] Usando id_detalle para merge directo (conexión específica)")
            
            if "codigo_glosa" in glosa_result.columns or "justificacion_glosa" in glosa_result.columns:
                # Preparar glosa para merge por id_detalle
                glosa_merge = self._prepare_glosa_merge_by_id_detalle_direct(glosa_result)
                
                if not glosa_merge.empty:
                    # Hacer merge directo por id_detalle
                    detalle_result = detalle_result.merge(
                        glosa_merge, 
                        on='id_detalle', 
                        how='left'
                    )
                    
                    cols_added = []
                    if "codigo_glosa" in glosa_merge.columns:
                        cols_added.append("codigo_glosa")
                    if "justificacion_glosa" in glosa_merge.columns:
                        cols_added.append("justificacion_glosa")
                        
                    print(f"   [OK] Columnas agregadas por id_detalle: {cols_added}")
                else:
                    print(f"   [!] No se pudo preparar datos de glosa para merge")
                    detalle_result["codigo_glosa"] = ""
                    detalle_result["justificacion_glosa"] = ""
            else:
                self.warnings.append("No se encontraron columnas codigo_glosa o justificacion_glosa en archivo Glosa")
                print(f"   [!] No se encontraron columnas codigo_glosa o justificacion_glosa en Glosa")
                detalle_result["codigo_glosa"] = ""
                detalle_result["justificacion_glosa"] = ""
        else:
            print(f"   [WARN] No existe id_detalle en ambos archivos, no se puede hacer merge específico")
            detalle_result["codigo_glosa"] = ""
            detalle_result["justificacion_glosa"] = ""
        
        return {
            "detalle": detalle_result,
            "glosa": glosa_result
        }
    
    def _homologate_detalle(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Homologa el archivo de detalle con el homologador
        
        Homologación en línea:
        - Busca codigo_servicio en columna "Código Servicio de la ERP" del homologador
        - Si lo encuentra, trae el "Código producto en DGH" 
        - Agrega columnas: FECHA_PROCESO, Codigo homologado DGH, Codigo no homologado
        
        Args:
            df: DataFrame del archivo de detalle
            
        Returns:
            DataFrame con columnas de homologación
        """
        result_df = df.copy()
        result_df["FECHA_PROCESO"] = self.processing_date
        
        # 1. Obtener columna de código en detalle
        code_column = self._find_detalle_code_column(result_df)
        if code_column is None:
            result_df["Codigo homologado DGH"] = ""
            result_df["Codigo no homologado"] = ""
            return result_df
        
        print(f"   Columna de código: {code_column}")
        
        # 2. Verificar homologador
        if self.homologador_df is None:
            self.warnings.append("No hay archivo de homologación cargado")
            result_df["Codigo homologado DGH"] = ""
            result_df["Codigo no homologado"] = result_df[code_column]
            return result_df
        
        # 3. Crear diccionario de homologación
        homolog_dict = self._build_homologation_dict()
        if not homolog_dict:
            result_df["Codigo homologado DGH"] = ""
            result_df["Codigo no homologado"] = result_df[code_column]
            return result_df
        
        print(f"   Códigos en homologador: {len(homolog_dict)}")
        
        # 4. Aplicar homologación
        result_df = self._apply_homologation(result_df, code_column, homolog_dict)
        
        return result_df
    
    def _find_detalle_code_column(self, df: pd.DataFrame) -> Optional[str]:
        """Encuentra la columna de código en el archivo de detalle."""
        code_column = self.DETALLE_CODE_COLUMN
        
        if code_column in df.columns:
            return code_column
        
        # Buscar columna similar
        for col in df.columns:
            if "codigo" in col.lower() and "servicio" in col.lower():
                return col
        
        self.warnings.append(f"No se encontró columna '{self.DETALLE_CODE_COLUMN}'")
        return None
    
    def _find_homolog_column(self, keywords: List[str], exact_match: Optional[str] = None) -> Optional[str]:
        """
        Busca una columna en el homologador por nombre exacto o keywords.
        
        Args:
            keywords: Lista de palabras clave a buscar (todas deben estar)
            exact_match: Nombre exacto a buscar primero
        """
        if self.homologador_df is None:
            return None
        
        # Buscar nombre exacto primero
        if exact_match:
            for col in self.homologador_df.columns:
                if str(col).strip() == exact_match:
                    return col
        
        # Buscar por keywords
        for col in self.homologador_df.columns:
            col_lower = str(col).lower()
            if all(kw in col_lower for kw in keywords):
                return col
        
        return None
    
    def _build_homologation_dict(self) -> Dict[str, str]:
        """Construye el diccionario de homologación {codigo_erp: codigo_dgh}."""
        # Buscar columna origen
        homolog_code_col = self._find_homolog_column(
            keywords=["codigo", "servicio", "erp"],
            exact_match="Código Servicio de la ERP"
        )
        if homolog_code_col is None:
            if self.homologador_df is not None and len(self.homologador_df.columns) > 0:
                homolog_code_col = self.homologador_df.columns[0]
                self.warnings.append(f"No se encontró 'Código Servicio de la ERP', usando: {homolog_code_col}")
            else:
                return {}
        
        print(f"   Columna en homologador (origen): {homolog_code_col}")
        
        # Buscar columna destino
        homolog_dgh_col = self._find_homolog_column(
            keywords=["codigo", "dgh"],
            exact_match="Código producto en DGH"
        )
        if homolog_dgh_col is None:
            if self.homologador_df is not None and len(self.homologador_df.columns) > 1:
                homolog_dgh_col = self.homologador_df.columns[1]
            elif self.homologador_df is not None and len(self.homologador_df.columns) > 0:
                homolog_dgh_col = self.homologador_df.columns[0]
            else:
                return {}
            self.warnings.append(f"No se encontró 'Código producto en DGH', usando: {homolog_dgh_col}")
        
        print(f"   Columna en homologador (destino): {homolog_dgh_col}")
        
        # Crear diccionario
        homolog_dict = {}
        if self.homologador_df is not None:
            for _, row in self.homologador_df.iterrows():
                codigo_erp = self._normalize_code(row[homolog_code_col])
                codigo_dgh = self._normalize_code(row[homolog_dgh_col])
                
                # Validar código origen
                if not codigo_erp or codigo_erp in ['NAN', 'NONE', '']:
                    continue
                
                # Si el código destino es "0" o inválido, NO agregarlo al diccionario
                # Esto hará que estos códigos vayan a "Codigo no homologado"
                if codigo_dgh and codigo_dgh not in ['0', 'NAN', 'NONE', '']:
                    homolog_dict[codigo_erp] = codigo_dgh
                # Si no hay código destino válido, no agregar al diccionario
                # (no hacer autoasignación)
        
        return homolog_dict
    
    def _normalize_code(self, code) -> str:
        """
        Normaliza un código manejando correctamente floats, ints, strings y NaN.
        
        Args:
            code: Código a normalizar
            
        Returns:
            String normalizado en MAYÚSCULAS
        """
        if pd.isna(code):
            return ""
        
        # Si es número (float/int), convertir a int primero para eliminar .0
        if isinstance(code, (int, float)):
            try:
                return str(int(code)).strip().upper()
            except (ValueError, OverflowError):
                return str(code).strip().upper()
        
        # Si es string, limpiar y normalizar
        return str(code).strip().upper()
    
    def _apply_homologation(self, df: pd.DataFrame, code_column: str, homolog_dict: Dict[str, str]) -> pd.DataFrame:
        """
        Aplica la homologación al DataFrame.
        
        Args:
            df: DataFrame a homologar
            code_column: Nombre de la columna con códigos
            homolog_dict: Diccionario de homologación
        """
        codigos_homologados = []
        codigos_no_homologados = []
        
        for codigo in df[code_column]:
            codigo_norm = self._normalize_code(codigo)
            
            # Si el código normalizado es válido y existe en el diccionario
            if codigo_norm and codigo_norm in homolog_dict:
                codigos_homologados.append(homolog_dict[codigo_norm])
                codigos_no_homologados.append("")
            else:
                # No homologado: dejar vacío el homologado y poner el original en no_homologado
                codigos_homologados.append("")
                codigos_no_homologados.append(str(codigo) if not pd.isna(codigo) else "")
        
        df["Codigo homologado DGH"] = codigos_homologados
        df["Codigo no homologado"] = codigos_no_homologados
        
        # Estadísticas
        self._print_homologation_stats(codigos_homologados, codigos_no_homologados)
        
        return df
    
    def _print_homologation_stats(self, codigos_homologados: List[str], codigos_no_homologados: List[str]):
        """Imprime estadísticas de homologación."""
        total = len(codigos_homologados)
        homologados = sum(1 for c in codigos_homologados if c)
        no_homologados = total - homologados
        
        print(f"\n[STATS] Estadísticas de homologación:")
        print(f"   Total registros: {total}")
        if total > 0:
            print(f"   Homologados: {homologados} ({homologados/total*100:.1f}%)")
            print(f"   No homologados: {no_homologados} ({no_homologados/total*100:.1f}%)")
        
        if no_homologados > 0:
            codigos_unicos = len(set([c for c in codigos_no_homologados if c]))
            print(f"   Códigos únicos no homologados: {codigos_unicos}")
    
    def get_non_homologated_summary(self, detalle_df: pd.DataFrame) -> pd.DataFrame:
        """
        Obtiene un resumen de los códigos no homologados
        
        Returns:
            DataFrame con código y cantidad de ocurrencias
        """
        if "Codigo no homologado" not in detalle_df.columns:
            return pd.DataFrame(columns=["CODIGO", "CANTIDAD"])
            
        no_homolog = detalle_df[detalle_df["Codigo no homologado"] != ""]
        
        if len(no_homolog) == 0:
            return pd.DataFrame(columns=["CODIGO", "CANTIDAD"])
            
        summary = no_homolog.groupby("Codigo no homologado").size().reset_index()
        summary.columns = ["CODIGO", "CANTIDAD"]
        summary = summary.sort_values("CANTIDAD", ascending=False)
        
        return summary
    
    def save_to_excel(self, data: Dict[str, pd.DataFrame], output_path: str) -> bool:
        """
        Guarda los resultados en un archivo Excel con 2 hojas:
        - Hoja "Detalles": datos del archivo de detalle con homologación
        - Hoja "Glosa": datos del archivo de glosa
        
        Args:
            data: Diccionario con {"detalle": df, "glosa": df}
            output_path: Ruta del archivo de salida
            
        Returns:
            True si se guardó correctamente
        """
        try:
            with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
                # Hoja 1: Detalles
                if "detalle" in data:
                    data["detalle"].to_excel(writer, sheet_name="Detalles", index=False)
                    print(f"   [OK] Hoja 'Detalles' guardada ({len(data['detalle'])} filas)")
                
                # Hoja 2: Glosa
                if "glosa" in data:
                    data["glosa"].to_excel(writer, sheet_name="Glosa", index=False)
                    print(f"   [OK] Hoja 'Glosa' guardada ({len(data['glosa'])} filas)")
            
            print(f"\n[SAVE] Archivo guardado: {output_path}")
            return True
            
        except Exception as e:
            self.errors.append(f"Error al guardar archivo: {str(e)}")
            return False
    
    def process_glosas(self, file_paths: List[str], output_dir: Optional[str] = None, email_date: Optional[str] = None, attachment_service=None) -> Tuple[Optional[Dict[str, pd.DataFrame]], str]:
        """
        Método principal para procesar archivos de GLOSAS de Coosalud
        Procesa TODOS los pares de archivos (DETALLE + GLOSA) y los combina
        
        Args:
            file_paths: Lista de rutas a los archivos
            output_dir: Directorio de salida (opcional)
            email_date: Fecha del correo recibido (formato string) - DEPRECATED, usar attachment_service
            attachment_service: Servicio de adjuntos con metadatos de fechas por archivo
            
        Returns:
            Tupla con (Diccionario de DataFrames combinados, mensaje de estado)
        """
        self.errors = []
        self.warnings = []
        
        print("=" * 60)
        print("[COOSALUD] PROCESADOR COOSALUD - GLOSAS")
        print("=" * 60)
        
        # 1. Cargar homologador
        if self.homologador_path:
            print(f"\n[LIST] Cargando homologador...")
            if not self.load_homologador():
                return None, f"[ERROR] Error: {'; '.join(self.errors)}"
        else:
            print(f"\n[!] Sin archivo de homologación")
        
        # 2. Identificar TODOS los pares de archivos
        print(f"\n[SEARCH] Identificando pares de archivos...")
        pairs = self.identify_file_pairs(file_paths)
        
        if not pairs:
            self.errors.append("No se encontraron pares de archivos DETALLE+GLOSA")
            return None, f"[ERROR] Error: {'; '.join(self.errors)}"
        
        print(f"\n[PROC] Procesando {len(pairs)} pares de archivos...")
        
        # 3. Procesar cada par y acumular resultados
        all_detalles = []
        all_glosas = []
        pares_procesados = 0
        pares_error = 0
        
        for i, pair in enumerate(pairs):
            factura = pair.get("factura", f"Par {i+1}")
            
            # Mostrar progreso
            if (i + 1) % 10 == 0 or i == 0:
                print(f"  ... procesando par {i + 1}/{len(pairs)} ({factura})")
            
            try:
                # Cargar archivos del par
                detalle_df = pd.read_excel(pair["detalle"])
                glosa_df = pd.read_excel(pair["glosa"])
                
                # Agregar columna de factura para tracking
                detalle_df["_FACTURA"] = factura
                glosa_df["_FACTURA"] = factura
                
                # Homologar el detalle
                detalle_result = self._homologate_detalle_silent(detalle_df)
                
                # Agregar fecha de proceso a glosa
                glosa_df["FECHA_PROCESO"] = self.processing_date
                
                all_detalles.append(detalle_result)
                all_glosas.append(glosa_df)
                pares_procesados += 1
                
            except Exception as e:
                pares_error += 1
                self.warnings.append(f"Error en {factura}: {str(e)}")
        
        print(f"\n[STATS] Pares procesados: {pares_procesados}/{len(pairs)}")
        if pares_error > 0:
            print(f"  [!] Pares con error: {pares_error}")
        
        # 4. Combinar todos los resultados
        if not all_detalles:
            self.errors.append("No se pudo procesar ningún par de archivos")
            return None, f"[ERROR] Error: {'; '.join(self.errors)}"
        
        # Combinar DataFrames
        combined_detalle = pd.concat(all_detalles, ignore_index=True)
        combined_glosa = pd.concat(all_glosas, ignore_index=True)
        
        # Agregar fecha del correo INDIVIDUAL por archivo
        if attachment_service:
            print(f"\n{'='*60}")
            print(f"[INFO] ASIGNANDO FECHAS DE CORREOS A ARCHIVOS")
            print(f"{'='*60}")
            print(f"[DEBUG] Total metadatos disponibles: {len(attachment_service.file_metadata)}")
            
            # Mostrar muestra de metadatos disponibles
            if attachment_service.file_metadata:
                print(f"[DEBUG] Muestra de metadatos (primeros 5):")
                for idx, (path, meta) in enumerate(list(attachment_service.file_metadata.items())[:5]):
                    import os
                    print(f"   {idx+1}. {os.path.basename(path)}")
                    print(f"      Fecha: {meta.get('email_date', 'SIN FECHA')}")
            else:
                print(f"[WARN] ⚠️ NO HAY METADATOS - Los archivos no tienen fecha asociada")
                print(f"[WARN] Esto ocurre cuando los archivos fueron descargados antes de implementar el sistema de metadatos")
            
            # Crear columna de fecha vacía
            combined_detalle["fecha_correo"] = ""
            
            archivos_con_fecha = 0
            archivos_sin_fecha = 0
            
            # Asignar fecha según el archivo de origen (_FACTURA)
            print(f"\n[PROC] Procesando {len(pairs)} pares de archivos...")
            for i, pair in enumerate(pairs):
                factura = pair.get("factura", f"Par {i+1}")
                detalle_path = pair["detalle"]
                
                # Debug para primeros 3
                if i < 3:
                    import os
                    print(f"\n[{i+1}] Factura: {factura}")
                    print(f"    Archivo: {os.path.basename(detalle_path)}")
                
                # Buscar metadatos del archivo DETALLE
                metadata = None
                if attachment_service:  # type: ignore
                    metadata = attachment_service.get_file_metadata(detalle_path)
                
                if i < 3:
                    print(f"    Metadata: {'✅ ENCONTRADO' if metadata else '❌ NO ENCONTRADO'}")
                    if metadata:
                        print(f"    Fecha: {metadata.get('email_date', 'SIN CAMPO email_date')}")
                
                if metadata and "email_date" in metadata:
                    file_date = metadata["email_date"]
                    # Asignar fecha a todos los registros de esta factura
                    mask = combined_detalle["_FACTURA"] == factura
                    combined_detalle.loc[mask, "fecha_correo"] = file_date
                    archivos_con_fecha += 1
                else:
                    # Fallback a fecha actual para este archivo
                    fallback_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    mask = combined_detalle["_FACTURA"] == factura
                    combined_detalle.loc[mask, "fecha_correo"] = fallback_date
                    archivos_sin_fecha += 1
            
            print(f"\n[RESULTADO] Archivos procesados:")
            print(f"   ✅ Con fecha del correo: {archivos_con_fecha}/{len(pairs)}")
            print(f"   ⚠️ Sin fecha (usando actual): {archivos_sin_fecha}/{len(pairs)}")
            
            if archivos_sin_fecha > 0:
                print(f"\n[AYUDA] Para que las fechas funcionen correctamente:")
                print(f"   1. Los archivos antiguos NO tienen metadatos")
                print(f"   2. Haz una nueva búsqueda de correos para descargar archivos con metadatos")
                print(f"   3. Los archivos antiguos se limpian automáticamente al buscar correos")
            print(f"{'='*60}\n")
        elif email_date:
            # Fallback antiguo: usar fecha global (menos preciso)
            combined_detalle["fecha_correo"] = email_date
            print(f"[INFO] ✅ Fecha global agregada: {email_date}")
        else:
            # Fallback a fecha actual
            combined_detalle["fecha_correo"] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            print(f"[WARN] ⚠️ No se recibió fecha del correo, usando fecha actual")
        
        # Merge usando columnas comunes para traer codigo_glosa y justificacion_glosa a Detalles
        print(f"\n[PROC] Agregando codigo_glosa y justificacion_glosa a Detalles...")
        
        # DEBUG: Mostrar columnas disponibles
        print(f"   [DEBUG] Columnas en DETALLE combinado: {list(combined_detalle.columns)}")
        print(f"   [DEBUG] Columnas en GLOSA combinado: {list(combined_glosa.columns)}")
        
        # Buscar columnas comunes para merge
        detalle_cols = set(col.lower() for col in combined_detalle.columns)
        glosa_cols = set(col.lower() for col in combined_glosa.columns)
        
        # Mapeo para preservar case original
        detalle_col_map = {c.lower(): c for c in combined_detalle.columns}
        glosa_col_map = {c.lower(): c for c in combined_glosa.columns}
        
        # PRIORIDAD: usar id_detalle si existe en ambos (conexión directa)
        if 'id_detalle' in detalle_cols and 'id_detalle' in glosa_cols:
            print(f"   [INFO] Usando id_detalle para merge directo (conexión específica)")
            
            if "codigo_glosa" in combined_glosa.columns or "justificacion_glosa" in combined_glosa.columns:
                # Preparar glosa para merge por id_detalle
                glosa_merge = self._prepare_glosa_merge_by_id_detalle_direct(combined_glosa)
                
                if not glosa_merge.empty:
                    # Hacer merge directo por id_detalle
                    combined_detalle = combined_detalle.merge(
                        glosa_merge, 
                        on='id_detalle', 
                        how='left'
                    )
                    
                    cols_added = []
                    if "codigo_glosa" in glosa_merge.columns:
                        cols_added.append("codigo_glosa")
                    if "justificacion_glosa" in glosa_merge.columns:
                        cols_added.append("justificacion_glosa")
                        
                    print(f"   [OK] Columnas agregadas por id_detalle: {cols_added}")
                else:
                    print(f"   [!] No se pudo preparar datos de glosa para merge")
                    combined_detalle["codigo_glosa"] = ""
                    combined_detalle["justificacion_glosa"] = ""
            else:
                print(f"   [!] No se encontraron columnas codigo_glosa o justificacion_glosa")
                combined_detalle["codigo_glosa"] = ""
                combined_detalle["justificacion_glosa"] = ""
        else:
            print(f"   [WARN] No existe id_detalle en ambos archivos, no se puede hacer merge específico")
            combined_detalle["codigo_glosa"] = ""
            combined_detalle["justificacion_glosa"] = ""
        
        result_data = {
            "detalle": combined_detalle,
            "glosa": combined_glosa
        }
        
        # 5. Guardar resultados si hay directorio de salida
        output_files = []
        if output_dir:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            # 5.1 Guardar archivo consolidado de glosas
            output_filename = f"COOSALUD_GLOSAS_{timestamp}.xlsx"
            output_path = os.path.join(output_dir, output_filename)
            
            print(f"\n[SAVE] Guardando resultado consolidado...")
            if self.save_to_excel(result_data, output_path):
                output_files.append(output_filename)
            
            # 5.2 Generar archivo de objeciones
            objeciones_path = self._generar_archivo_objeciones(
                combined_detalle, 
                output_dir, 
                email_date
            )
            if objeciones_path:
                output_files.append(os.path.basename(objeciones_path))
            
            if output_files:
                files_str = ", ".join(output_files)
                return result_data, f"[OK] Procesado exitosamente. Archivos: {files_str}"
            else:
                return result_data, f"[WARNING] Procesado pero error al guardar: {'; '.join(self.errors)}"
        
        return result_data, f"[OK] Procesados {pares_procesados} pares de archivos"
        
            
    def _homologate_detalle_silent(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Versión silenciosa de _homologate_detalle (sin prints)
        Para uso en procesamiento masivo
        """
        result_df = df.copy()
        result_df["FECHA_PROCESO"] = self.processing_date
        
        code_column = self.DETALLE_CODE_COLUMN
        if code_column not in result_df.columns:
            for col in result_df.columns:
                if "codigo" in col.lower() and "servicio" in col.lower():
                    code_column = col
                    break
            else:
                result_df["Codigo homologado DGH"] = ""
                result_df["Codigo no homologado"] = ""
                return result_df
        
        if self.homologador_df is None:
            result_df["Codigo homologado DGH"] = ""
            result_df["Codigo no homologado"] = result_df[code_column]
            return result_df
        
        # Buscar columnas del homologador
        homolog_code_col = None
        homolog_dgh_col = None
        
        for col in self.homologador_df.columns:
            col_str = str(col).strip()
            if col_str == "Código Servicio de la ERP":
                homolog_code_col = col
            elif col_str == "Código producto en DGH":
                homolog_dgh_col = col
        
        if homolog_code_col is None:
            homolog_code_col = self.homologador_df.columns[0]
        if homolog_dgh_col is None:
            homolog_dgh_col = self.homologador_df.columns[1] if len(self.homologador_df.columns) > 1 else self.homologador_df.columns[0]
        
        # Crear diccionario de homologación
        homolog_dict = {}
        for _, row in self.homologador_df.iterrows():
            codigo_erp = self._normalize_code(row[homolog_code_col])
            codigo_dgh = self._normalize_code(row[homolog_dgh_col])
            
            # Validar código origen
            if not codigo_erp or codigo_erp in ['NAN', 'NONE', '']:
                continue
            
            # Solo agregar si el código destino es válido (no "0")
            if codigo_dgh and codigo_dgh not in ['0', 'NAN', 'NONE', '']:
                homolog_dict[codigo_erp] = codigo_dgh
        
        # Homologar
        codigos_homologados = []
        codigos_no_homologados = []
        
        for codigo in result_df[code_column]:
            codigo_norm = self._normalize_code(codigo)
            
            # Si el código normalizado es válido y existe en el diccionario
            if codigo_norm and codigo_norm in homolog_dict:
                codigos_homologados.append(homolog_dict[codigo_norm])
                codigos_no_homologados.append("")
            else:
                codigos_homologados.append("")
                codigos_no_homologados.append(str(codigo) if not pd.isna(codigo) else "")
        
        result_df["Codigo homologado DGH"] = codigos_homologados
        result_df["Codigo no homologado"] = codigos_no_homologados
        
        return result_df
    
    # ==================== GENERACIÓN DE ARCHIVO OBJECIONES ====================
    
    def _find_column(self, df: pd.DataFrame, keywords: List[str], exact_match: Optional[str] = None) -> Optional[str]:
        """
        Busca una columna en el DataFrame por nombre exacto o keywords.
        
        Args:
            df: DataFrame donde buscar
            keywords: Lista de palabras clave (todas deben estar en el nombre)
            exact_match: Nombre exacto a buscar primero
            
        Returns:
            Nombre de la columna encontrada o None
        """
        # Buscar match exacto primero
        if exact_match:
            for col in df.columns:
                if str(col).strip().lower() == exact_match.lower():
                    return col
        
        # Buscar por keywords
        for col in df.columns:
            col_lower = str(col).lower()
            if all(kw.lower() in col_lower for kw in keywords):
                return col
        
        return None
    
    def _formatear_crncxc(self, valor) -> str:
        """
        Formatea el número de factura al formato CRNCXC.
        Ej: "12345" -> "FC000012345", "FC12345" -> "FC000012345"
        """
        if pd.isna(valor) or not valor:
            return ''
        
        valor_str = str(valor).strip()
        
        # Si ya tiene FC, extraer solo los números
        if valor_str.upper().startswith('FC'):
            numeros = valor_str[2:]
        else:
            numeros = valor_str
        
        # Limpiar caracteres no numéricos
        numeros = ''.join(filter(str.isdigit, numeros))
        
        if not numeros:
            return ''
        
        return f"FC0000{numeros}"
    
    def _formatear_fecha_dmy(self, fecha) -> str:
        """Convierte fecha a formato DD/MM/YYYY"""
        if pd.isna(fecha) or not fecha:
            return ''
        try:
            if isinstance(fecha, (pd.Timestamp, datetime)):
                return fecha.strftime('%d/%m/%Y')
            fecha_dt = pd.to_datetime(str(fecha), errors='coerce')
            return fecha_dt.strftime('%d/%m/%Y') if pd.notna(fecha_dt) else ''
        except:
            return ''
    
    def _obtener_valor_numerico(self, valor) -> float:
        """Convierte un valor a float, manejando formatos con $ y separadores, manteniendo decimales"""
        if pd.isna(valor) or not valor:
            return 0.0
        try:
            if isinstance(valor, (int, float)):
                return float(valor)
            
            # Limpiar formato monetario
            valor_str = str(valor).strip()
            valor_str = valor_str.replace('$', '').replace(' ', '')
            
            # Manejar separadores: punto para miles, coma para decimales (formato colombiano)
            # o coma para miles, punto para decimales (formato internacional)
            if ',' in valor_str and '.' in valor_str:
                # Determinar cuál es decimal
                pos_coma = valor_str.rfind(',')
                pos_punto = valor_str.rfind('.')
                if pos_punto > pos_coma:
                    # Formato: 1.234.567,89 -> punto es miles, coma es decimal
                    valor_str = valor_str.replace('.', '').replace(',', '.')
                else:
                    # Formato: 1,234,567.89 -> coma es miles, punto es decimal
                    valor_str = valor_str.replace(',', '')
            elif ',' in valor_str:
                # Solo coma: puede ser miles o decimal
                # Si hay más de una coma, es separador de miles
                if valor_str.count(',') > 1:
                    valor_str = valor_str.replace(',', '')
                else:
                    # Una sola coma: verificar posición
                    partes = valor_str.split(',')
                    if len(partes[1]) <= 2:
                        # Probablemente decimal
                        valor_str = valor_str.replace(',', '.')
                    else:
                        # Probablemente miles
                        valor_str = valor_str.replace(',', '')
            elif '.' in valor_str:
                # Solo punto: puede ser miles o decimal
                if valor_str.count('.') > 1:
                    valor_str = valor_str.replace('.', '')
                # Si es un solo punto, asumir que es decimal
            
            return float(valor_str) if valor_str else 0.0
        except:
            return 0.0
    
    def _procesar_au_ta(self, df_obj: pd.DataFrame) -> pd.DataFrame:
        """
        Procesa filas AU/TA: Si hay AU y TA para la misma factura+servicio,
        combina las observaciones en la fila AU y elimina las filas TA.
        """
        print("🔄 Procesando AU/TA...")
        
        filas_eliminar: List[Any] = []  # Cambiar a List[Any] para aceptar cualquier tipo de índice
        procesadas = 0
        
        for (factura, tec), grupo in df_obj.groupby(['CRNCXC', 'SLNSERPRO']):
            if len(grupo) < 2:
                continue
            
            # Convertir índices de forma segura (el índice puede ser int, str, o cualquier hashable)
            filas_au = [i for i, r in grupo.iterrows() if str(r.get('CRNCONOBJ', '')).upper().startswith('AU')]
            filas_ta = [i for i, r in grupo.iterrows() if str(r.get('CRNCONOBJ', '')).upper().startswith('TA')]
            
            if filas_au and filas_ta:
                idx_au = filas_au[0]
                
                for idx_ta in filas_ta:
                    # Usar .at para acceso a celda individual (más rápido y sin problemas de tipo)
                    obs_ta = str(df_obj.at[idx_ta, 'CRDOBSERV']).strip()  # type: ignore
                    if obs_ta:
                        obs_au = str(df_obj.at[idx_au, 'CRDOBSERV']).strip()  # type: ignore
                        df_obj.at[idx_au, 'CRDOBSERV'] = f"{obs_au} \\\\ {obs_ta}" if obs_au else f"\\\\ {obs_ta}"  # type: ignore
                    
                    filas_eliminar.append(idx_ta)
                    procesadas += 1
        
        if filas_eliminar:
            df_obj = df_obj.drop(filas_eliminar).reset_index(drop=True)
            print(f"   ✅ {procesadas} filas TA procesadas")
        
        return df_obj
    
    def _generar_archivo_objeciones(self, detalle_df: pd.DataFrame, output_dir: str, email_date: Optional[str] = None) -> Optional[str]:
        """
        Genera archivo Objeciones.xlsx a partir del DataFrame de detalle procesado.
        
        Columnas de salida:
        - CDCONSEC: Consecutivo por factura
        - CDFECDOC: Fecha del documento (hoy en formato D/M/A)
        - CRNCXC: Número de factura formateado (FC0000{numero})
        - CROFECOBJ: Fecha de la objeción (fecha del correo)
        - CROREFERE: Vacío
        - CROOBSERV: REG GLOSA según número de glosa
        - CROCLAOBJ: 0
        - GENUSUARIO4: 1103858268
        - CRNCONOBJ: Código de glosa homologado
        - SLNSERPRO: Código servicio homologado DGH
        - CTNCENCOS: Vacío
        - IDRIPS: Vacío  
        - CROVALOBJ: Valor glosado
        - CRDOBSERV: Justificación/observaciones de la glosa
        
        Args:
            detalle_df: DataFrame de detalle con homologación aplicada
            output_dir: Directorio de salida
            email_date: Fecha del correo (para CROFECOBJ)
            
        Returns:
            Ruta del archivo generado o None si hay error
        """
        if detalle_df is None or detalle_df.empty:
            self.errors.append("No hay datos para generar objeciones")
            return None
        
        try:
            print("\n📄 Generando Objeciones.xlsx...")
            
            df_obj = pd.DataFrame()
            
            # Buscar columnas en el detalle
            col_factura = self._find_column(detalle_df, ['numero', 'factura'], 'numero_factura')
            col_glosa_num = self._find_column(detalle_df, ['numero', 'glosa'], 'numero_glosa') or self._find_column(detalle_df, ['id', 'glosa'])
            col_valor_glosado = self._find_column(detalle_df, ['valor', 'glosado'], 'valor_glosado')
            
            print(f"   Columna factura: {col_factura}")
            print(f"   Columna número glosa: {col_glosa_num}")
            print(f"   Columna valor glosado: {col_valor_glosado}")
            
            # CDCONSEC - Consecutivo por factura
            if col_factura:
                facturas = detalle_df[col_factura]
                factura_consecutivo = {f: i+1 for i, f in enumerate(facturas.unique())}
                df_obj['CDCONSEC'] = facturas.map(factura_consecutivo)
            else:
                df_obj['CDCONSEC'] = range(1, len(detalle_df) + 1)
            
            # CDFECDOC - Fecha del documento (hoy)
            df_obj['CDFECDOC'] = datetime.now().strftime('%#d/%#m/%Y') if os.name == 'nt' else datetime.now().strftime('%-d/%-m/%Y')
            
            # CRNCXC - Número de factura formateado
            if col_factura:
                df_obj['CRNCXC'] = detalle_df[col_factura].apply(self._formatear_crncxc)
            else:
                df_obj['CRNCXC'] = ''
            
            # CROFECOBJ - Fecha de objeción (fecha del correo individual por registro)
            # Usar la columna fecha_correo que tiene la fecha específica de cada archivo
            if 'fecha_correo' in detalle_df.columns:
                def format_fecha_correo(fecha_str):
                    if pd.isna(fecha_str) or not fecha_str:
                        return ''
                    try:
                        # Parsear y formatear solo la fecha (sin hora)
                        fecha_dt = pd.to_datetime(fecha_str)
                        return fecha_dt.strftime('%d/%m/%Y')
                    except:
                        return ''
                
                df_obj['CROFECOBJ'] = detalle_df['fecha_correo'].apply(format_fecha_correo)
            elif email_date:
                # Fallback a fecha global si no hay fecha_correo
                try:
                    fecha_correo = pd.to_datetime(email_date)
                    df_obj['CROFECOBJ'] = fecha_correo.strftime('%d/%m/%Y')
                except:
                    df_obj['CROFECOBJ'] = email_date
            else:
                df_obj['CROFECOBJ'] = ''
            
            # CROREFERE - Vacío
            df_obj['CROREFERE'] = ''
            
            # CROOBSERV - REG, GLOSA SEGUN RAD N. + fecha CROFECOBJ
            df_obj['CROOBSERV'] = df_obj['CROFECOBJ'].apply(
                lambda fecha: f"REG, GLOSA SEGUN RAD N. {fecha}" if fecha else ""
            )
            
            # CROCLAOBJ - Siempre 0
            df_obj['CROCLAOBJ'] = 0
            
            # GENUSUARIO4 - ID fijo
            df_obj['GENUSUARIO4'] = 1103858268
            
            # CRNCONOBJ - Código de glosa (ya homologado)
            if 'codigo_glosa' in detalle_df.columns:
                df_obj['CRNCONOBJ'] = detalle_df['codigo_glosa']
            else:
                df_obj['CRNCONOBJ'] = ''
            
            # SLNSERPRO - Código servicio homologado DGH
            if 'Codigo homologado DGH' in detalle_df.columns:
                df_obj['SLNSERPRO'] = detalle_df['Codigo homologado DGH']
            else:
                df_obj['SLNSERPRO'] = ''
            
            # CTNCENCOS - Vacío
            df_obj['CTNCENCOS'] = ''
            
            # IDRIPS - Vacío
            df_obj['IDRIPS'] = ''
            
            # CROVALOBJ - Valor glosado (mantener decimales para centavos)
            if col_valor_glosado and col_valor_glosado in detalle_df.columns:
                df_obj['CROVALOBJ'] = detalle_df[col_valor_glosado].apply(self._obtener_valor_numerico)
            else:
                df_obj['CROVALOBJ'] = 0.0
            
            # CRDOBSERV - Justificación/observaciones
            if 'justificacion_glosa' in detalle_df.columns:
                df_obj['CRDOBSERV'] = detalle_df['justificacion_glosa'].fillna('')
            else:
                df_obj['CRDOBSERV'] = ''
            
            # Procesar AU/TA (combinar observaciones)
            df_obj = self._procesar_au_ta(df_obj)
            
            # Exportar
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            output_path = os.path.join(output_dir, f"Objeciones_COOSALUD_{timestamp}.xlsx")
            
            with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
                df_obj.to_excel(writer, sheet_name='OBJECIONES', index=False)
            
            print(f"✅ Objeciones generadas: {output_path} ({len(df_obj)} registros)")
            return output_path
            
        except Exception as e:
            self.errors.append(f"Error generando objeciones: {str(e)}")
            print(f"❌ Error generando objeciones: {e}")
            return None
