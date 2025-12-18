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
from typing import List, Dict, Tuple, Optional

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
    
    def __init__(self, homologador_path: str = None):
        super().__init__(homologador_path)
        self.detalle_df = None
        self.glosa_df = None
        
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
        Identifica TODOS los pares de archivos de Coosalud agrupados por factura
        
        Args:
            file_paths: Lista de rutas a los archivos
            
        Returns:
            Lista de diccionarios con pares {"detalle": path, "glosa": path, "factura": "FC..."}
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
        Extrae los datos de los archivos de Coosalud
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
    
    def homologate(self, data: Dict[str, pd.DataFrame]) -> Dict[str, pd.DataFrame]:
        """
        Realiza el proceso de homologación para Coosalud
        
        1. Del archivo de Detalle: homologa codigo_servicio
        2. Del archivo de Glosa: agrega fecha de proceso
        3. Agrega columnas: FECHA_PROCESO y CODIGO_NO_HOMOLOGADO
        
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
        
        # Agregar fecha de proceso
        result_df["FECHA_PROCESO"] = self.processing_date
        
        # Verificar que existe la columna de código
        code_column = self.DETALLE_CODE_COLUMN
        if code_column not in result_df.columns:
            # Buscar columna similar
            for col in result_df.columns:
                if "codigo" in col.lower() and "servicio" in col.lower():
                    code_column = col
                    break
            else:
                self.warnings.append(f"No se encontró columna '{self.DETALLE_CODE_COLUMN}'")
                result_df["Codigo homologado DGH"] = ""
                result_df["Codigo no homologado"] = ""
                return result_df
        
        print(f"   Columna de código: {code_column}")
        
        # Si no hay homologador, marcar todos como no homologados
        if self.homologador_df is None:
            self.warnings.append("No hay archivo de homologación cargado")
            result_df["Codigo homologado DGH"] = ""
            result_df["Codigo no homologado"] = result_df[code_column]
            return result_df
        
        # Buscar columna "Código Servicio de la ERP" en el homologador
        homolog_code_col = None
        for col in self.homologador_df.columns:
            col_str = str(col).strip()
            if col_str == "Código Servicio de la ERP":
                homolog_code_col = col
                break
        
        if homolog_code_col is None:
            # Intentar buscar por palabras clave
            for col in self.homologador_df.columns:
                col_lower = str(col).lower()
                if "codigo" in col_lower and "servicio" in col_lower and "erp" in col_lower:
                    homolog_code_col = col
                    break
        
        if homolog_code_col is None:
            homolog_code_col = self.homologador_df.columns[0]
            self.warnings.append(f"No se encontró 'Código Servicio de la ERP', usando: {homolog_code_col}")
        
        print(f"   Columna en homologador (origen): {homolog_code_col}")
        
        # Buscar columna "Código producto en DGH" en el homologador
        homolog_dgh_col = None
        for col in self.homologador_df.columns:
            col_str = str(col).strip()
            if col_str == "Código producto en DGH":
                homolog_dgh_col = col
                break
        
        if homolog_dgh_col is None:
            # Intentar buscar por palabras clave
            for col in self.homologador_df.columns:
                col_lower = str(col).lower()
                if "codigo" in col_lower and "dgh" in col_lower:
                    homolog_dgh_col = col
                    break
        
        if homolog_dgh_col is None:
            homolog_dgh_col = self.homologador_df.columns[1] if len(self.homologador_df.columns) > 1 else self.homologador_df.columns[0]
            self.warnings.append(f"No se encontró 'Código producto en DGH', usando: {homolog_dgh_col}")
        
        print(f"   Columna en homologador (destino): {homolog_dgh_col}")
        
        # Crear diccionario de homologación: {codigo_erp: codigo_dgh}
        homolog_dict = {}
        for _, row in self.homologador_df.iterrows():
            codigo_erp = str(row[homolog_code_col]).strip().upper()
            codigo_dgh = str(row[homolog_dgh_col]).strip()
            if codigo_erp and codigo_erp != 'NAN':
                homolog_dict[codigo_erp] = codigo_dgh
        
        print(f"   Códigos en homologador: {len(homolog_dict)}")
        
        # Homologar cada código
        codigos_homologados = []
        codigos_no_homologados = []
        
        for codigo in result_df[code_column]:
            codigo_norm = str(codigo).strip().upper()
            
            if codigo_norm in homolog_dict:
                # Encontrado - agregar código DGH
                codigos_homologados.append(homolog_dict[codigo_norm])
                codigos_no_homologados.append("")
            else:
                # No encontrado - marcar como no homologado
                codigos_homologados.append("")
                codigos_no_homologados.append(str(codigo))
        
        # Agregar columnas al resultado
        result_df["Codigo homologado DGH"] = codigos_homologados
        result_df["Codigo no homologado"] = codigos_no_homologados
        
        # Estadísticas
        total = len(result_df)
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
        
        return result_df
    
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
        
        if len(no_homolog) == 0:
            return pd.DataFrame(columns=["CODIGO", "CANTIDAD"])
            
        summary = no_homolog.groupby("CODIGO_NO_HOMOLOGADO").size().reset_index()
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
    
    def process_glosas(self, file_paths: List[str], output_dir: str = None) -> Tuple[Optional[Dict[str, pd.DataFrame]], str]:
        """
        Método principal para procesar archivos de GLOSAS de Coosalud
        Procesa TODOS los pares de archivos (DETALLE + GLOSA) y los combina
        
        Args:
            file_paths: Lista de rutas a los archivos
            output_dir: Directorio de salida (opcional)
            
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
        
        combined_detalle = pd.concat(all_detalles, ignore_index=True)
        combined_glosa = pd.concat(all_glosas, ignore_index=True)
        
        print(f"\n[COMBINED] Resultados combinados:")
        print(f"   Total registros DETALLE: {len(combined_detalle)}")
        print(f"   Total registros GLOSA: {len(combined_glosa)}")
        
        # Estadísticas de homologación
        if "Codigo homologado DGH" in combined_detalle.columns:
            homologados = combined_detalle["Codigo homologado DGH"].astype(str).str.strip().ne("").sum()
            no_homologados = len(combined_detalle) - homologados
            print(f"   Homologados: {homologados} ({homologados/len(combined_detalle)*100:.1f}%)")
            print(f"   No homologados: {no_homologados}")
        
        result_data = {
            "detalle": combined_detalle,
            "glosa": combined_glosa
        }
        
        # 5. Construir mensaje de resultado
        message = f"[OK] Procesamiento completado.\n   Pares procesados: {pares_procesados}\n   Detalles: {len(combined_detalle)} registros\n   Glosas: {len(combined_glosa)} registros"
        
        if self.warnings:
            message += f"\n[!] Advertencias: {len(self.warnings)}"
        
        # 6. Guardar si se especificó directorio de salida
        if output_dir and result_data:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = os.path.join(output_dir, f"COOSALUD_GLOSAS_{timestamp}.xlsx")
            
            print(f"\n[SAVE] Guardando resultados...")
            if self.save_to_excel(result_data, output_file):
                message += f"\n[SAVE] Guardado en: {output_file}"
                
                # Guardar también resumen de no homologados
                summary = self.get_non_homologated_summary(combined_detalle)
                if len(summary) > 0:
                    summary_file = os.path.join(output_dir, f"COOSALUD_NO_HOMOLOGADOS_{timestamp}.xlsx")
                    summary.to_excel(summary_file, index=False)
                    message += f"\n[LIST] Códigos no homologados: {summary_file}"
        
        print("\n" + "=" * 60)
        return result_data, message
    
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
            codigo_erp = str(row[homolog_code_col]).strip().upper()
            codigo_dgh = str(row[homolog_dgh_col]).strip()
            if codigo_erp and codigo_erp != 'NAN':
                homolog_dict[codigo_erp] = codigo_dgh
        
        # Homologar
        codigos_homologados = []
        codigos_no_homologados = []
        
        for codigo in result_df[code_column]:
            codigo_norm = str(codigo).strip().upper()
            if codigo_norm in homolog_dict:
                codigos_homologados.append(homolog_dict[codigo_norm])
                codigos_no_homologados.append("")
            else:
                codigos_homologados.append("")
                codigos_no_homologados.append(str(codigo))
        
        result_df["Codigo homologado DGH"] = codigos_homologados
        result_df["Codigo no homologado"] = codigos_no_homologados
        
        return result_df
