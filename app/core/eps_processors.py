"""
Procesadores específicos para cada EPS
Maneja la extracción y transformación de datos según la estructura de cada EPS
"""
import pandas as pd
import os
from datetime import datetime


class MutualserProcessor:
    """
    Procesador específico para archivos de MUTUALSER
    Extrae columnas específicas y consolida en un nuevo Excel
    """
    
    # Columnas requeridas para MUTUALSER
    COLUMNAS_REQUERIDAS = [
        'Número de factura',
        'Número de glosa',
        'Tecnología',
        'Cantidad facturada',
        'Valor Facturado',
        'Cantidad glosada',
        'Valor glosado',
        'Concepto de glosa',
        'Código de glosa',
        'Observacion',
        'Fecha'
    ]
    
    def __init__(self, output_dir='outputs', homologacion_path='app/databaseExcel/archivo_de_homologacion.xlsx'):
        """
        Inicializa el procesador
        
        Args:
            output_dir: Directorio donde se guardará el archivo consolidado
            homologacion_path: Ruta al archivo de homologación
        """
        self.output_dir = output_dir
        self.homologacion_path = homologacion_path
        self.df_consolidado = None
        self.df_homologacion = None
        self.archivos_procesados = []
        self.errores = []
        
        # Crear directorio de salida si no existe
        os.makedirs(output_dir, exist_ok=True)
        
        # Cargar archivo de homologación
        self._cargar_homologacion()
    
    def _cargar_homologacion(self):
        """
        Carga el archivo de homologación de códigos
        """
        try:
            if not os.path.exists(self.homologacion_path):
                print(f"⚠️ Archivo de homologación no encontrado: {self.homologacion_path}")
                print("   El proceso continuará sin homologación")
                self.df_homologacion = None
                return
            
            self.df_homologacion = pd.read_excel(self.homologacion_path)
            
            # Normalizar nombres de columnas
            self.df_homologacion.columns = self.df_homologacion.columns.str.strip()
            
            print(f"✅ Archivo de homologación cargado: {len(self.df_homologacion)} registros")
            print(f"   Columnas disponibles: {list(self.df_homologacion.columns)}")
            
        except Exception as e:
            print(f"⚠️ Error al cargar archivo de homologación: {e}")
            print("   El proceso continuará sin homologación")
            self.df_homologacion = None
    
    def _buscar_codigo_homologado(self, codigo_tecnologia):
        """
        Busca el código homologado según las reglas de negocio
        
        Args:
            codigo_tecnologia: Código a buscar (de la columna Tecnología)
            
        Returns:
            Código homologado encontrado o None si no se encuentra
        """
        if self.df_homologacion is None or pd.isna(codigo_tecnologia):
            return None
        
        try:
            # Convertir código a string y limpiar
            codigo_str = str(codigo_tecnologia).strip()
            
            # Si está vacío, retornar None
            if not codigo_str or codigo_str == 'nan':
                return None
            
            # Determinar si es numérico para contar dígitos
            codigo_numerico = ''.join(filter(str.isdigit, codigo_str))
            num_digitos = len(codigo_numerico)
            
            # Usar los nombres exactos de las columnas
            columna_erp = 'Código Servicio de la ERP'
            columna_codigo_interno = 'Codigo Interno Ips'
            columna_codigo_producto = 'Código producto en DGH'
            
            # Verificar que las columnas existen
            if columna_erp not in self.df_homologacion.columns:
                print(f"❌ Columna '{columna_erp}' no encontrada")
                return None
            if columna_codigo_interno not in self.df_homologacion.columns:
                print(f"❌ Columna '{columna_codigo_interno}' no encontrada")
                columna_codigo_interno = None
            if columna_codigo_producto not in self.df_homologacion.columns:
                print(f"❌ Columna '{columna_codigo_producto}' no encontrada")
                columna_codigo_producto = None
            
            resultado = None
            
            # Según el número de dígitos, buscar en la columna correspondiente
            if num_digitos <= 6 and columna_codigo_interno:
                # Buscar en "Codigo Interno Ips"
                mask = self.df_homologacion[columna_codigo_interno].astype(str).str.strip() == codigo_str
                resultado = self.df_homologacion[mask]
                
                # Si no se encuentra, intentar búsqueda flexible (solo números)
                if resultado.empty and codigo_numerico:
                    mask = self.df_homologacion[columna_codigo_interno].astype(str).str.replace(r'\D', '', regex=True) == codigo_numerico
                    resultado = self.df_homologacion[mask]
                
            elif num_digitos > 6 and columna_codigo_producto:
                # Buscar en "Código producto en DGH"
                mask = self.df_homologacion[columna_codigo_producto].astype(str).str.strip() == codigo_str
                resultado = self.df_homologacion[mask]
                
                # Si no se encuentra, intentar búsqueda flexible
                if resultado.empty and codigo_numerico:
                    mask = self.df_homologacion[columna_codigo_producto].astype(str).str.replace(r'\D', '', regex=True) == codigo_numerico
                    resultado = self.df_homologacion[mask]
            
            # Si encontramos la fila, retornar el valor de "Código Servicio de la ERP"
            if resultado is not None and not resultado.empty:
                valor = resultado.iloc[0][columna_erp]
                if pd.notna(valor):
                    return str(valor).strip()
            
            # Si no se encontró, buscar también en "Código Servicio de la ERP" por si acaso
            mask = self.df_homologacion[columna_erp].astype(str).str.strip() == codigo_str
            resultado = self.df_homologacion[mask]
            
            if resultado.empty and codigo_numerico:
                mask = self.df_homologacion[columna_erp].astype(str).str.replace(r'\D', '', regex=True) == codigo_numerico
                resultado = self.df_homologacion[mask]
            
            if not resultado.empty:
                valor = resultado.iloc[0][columna_erp]
                if pd.notna(valor):
                    return str(valor).strip()
            
            return None
            
        except Exception as e:
            print(f"   ⚠️ Error buscando código {codigo_tecnologia}: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def _aplicar_homologacion(self):
        """
        Aplica el proceso de homologación al DataFrame consolidado
        Agrega la columna "Codigo homologado DGH"
        """
        if self.df_consolidado is None or self.df_consolidado.empty:
            print("⚠️ No hay datos para homologar")
            return
        
        if self.df_homologacion is None:
            print("⚠️ No se puede aplicar homologación: archivo de homologación no disponible")
            # Agregar columna vacía
            self.df_consolidado['Codigo homologado DGH'] = None
            return
        
        print("\n🔄 Aplicando homologación de códigos...")
        print(f"   Columnas disponibles en archivo de homologación:")
        for col in self.df_homologacion.columns:
            print(f"     - {col}")
        
        # Mostrar algunos ejemplos de códigos a buscar
        print(f"\n   Ejemplos de códigos a buscar (primeros 5):")
        for idx, codigo in enumerate(self.df_consolidado['Tecnología'].head(5)):
            if pd.notna(codigo):
                codigo_str = str(codigo).strip()
                codigo_num = ''.join(filter(str.isdigit, codigo_str))
                print(f"     {idx+1}. '{codigo_str}' -> {len(codigo_num)} dígitos -> Buscar en: {'Código Interno IPS' if len(codigo_num) <= 6 else 'Código Producto DGH'}")
        
        # Crear nueva columna con códigos homologados
        codigos_homologados = []
        total = len(self.df_consolidado)
        encontrados = 0
        errores_busqueda = []
        
        for idx, row in self.df_consolidado.iterrows():
            codigo_tecnologia = row.get('Tecnología')
            codigo_homologado = self._buscar_codigo_homologado(codigo_tecnologia)
            codigos_homologados.append(codigo_homologado)
            
            if codigo_homologado is not None:
                encontrados += 1
                # Mostrar los primeros 3 encontrados como ejemplo
                if encontrados <= 3:
                    print(f"   ✓ Encontrado: {codigo_tecnologia} -> {codigo_homologado}")
            else:
                if len(errores_busqueda) < 3 and pd.notna(codigo_tecnologia):
                    errores_busqueda.append(str(codigo_tecnologia))
            
            # Mostrar progreso cada 10%
            if (idx + 1) % max(1, total // 10) == 0:
                porcentaje = ((idx + 1) / total) * 100
                print(f"   Progreso: {porcentaje:.0f}% ({idx + 1}/{total}) - Encontrados: {encontrados}")
        
        # Agregar la columna al DataFrame
        self.df_consolidado['Codigo homologado DGH'] = codigos_homologados
        
        print(f"\n✅ Homologación completada:")
        print(f"   • Total de registros: {total}")
        print(f"   • Códigos homologados encontrados: {encontrados}")
        print(f"   • Sin homologar: {total - encontrados}")
        
        if errores_busqueda:
            print(f"\n   ⚠️ Ejemplos de códigos NO encontrados:")
            for codigo in errores_busqueda:
                print(f"     - {codigo}")
            #hay que agregar un mensaje de error en esa columna si no se encuentra el código homologado
            self.df_consolidado['Codigo homologado DGH'] = self.df_consolidado['Codigo homologado DGH'].fillna('Código no encontrado')        
        
        # Cargar archivo de homologación
        self._cargar_homologacion()
    
    def procesar_archivo(self, file_path):
        """
        Procesa un archivo individual de MUTUALSER
        
        Args:
            file_path: Ruta del archivo Excel a procesar
            
        Returns:
            DataFrame con las columnas extraídas o None si hay error
        """
        try:
            # Leer el archivo Excel completo sin headers para analizarlo
            if file_path.endswith(('.xlsx', '.xls')):
                df_raw = pd.read_excel(file_path, header=None)
            elif file_path.endswith('.csv'):
                df_raw = pd.read_csv(file_path, header=None)
            else:
                self.errores.append({
                    'archivo': file_path,
                    'error': 'Formato no soportado'
                })
                return None
            
            print(f"📄 Analizando estructura de {os.path.basename(file_path)}")
            
            # Buscar la fila que contiene "DETALLE DE GLOSA GENERADA" o los encabezados de columnas
            header_row_idx = None
            fecha_documento = None
            num_factura_general = None
            
            # Buscar información del encabezado
            for idx, row in df_raw.iterrows():
                row_str = ' '.join([str(cell) for cell in row if pd.notna(cell)]).upper()
                
                # Buscar fecha
                if 'FECHA' in row_str and fecha_documento is None:
                    for cell in row:
                        if pd.notna(cell) and ('/' in str(cell) or '-' in str(cell)):
                            try:
                                fecha_documento = pd.to_datetime(cell).strftime('%Y-%m-%d')
                                break
                            except:
                                pass
                
                # Buscar número de factura en el encabezado
                if 'FACTURA' in row_str and num_factura_general is None:
                    for cell in row:
                        cell_str = str(cell).strip()
                        if cell_str.startswith('FC') or cell_str.isdigit():
                            num_factura_general = cell_str
                            break
                
                # Buscar la fila de encabezados de la tabla
                if 'NUMERO DE FACTURA' in row_str or 'NÚMERO DE FACTURA' in row_str:
                    header_row_idx = idx
                    break
                elif 'DETALLE DE GLOSA' in row_str:
                    # La siguiente fila debería ser los encabezados
                    header_row_idx = idx + 1
                    break
            
            if header_row_idx is None:
                raise Exception("No se encontró la tabla de detalles de glosa")
            
            # Leer el DataFrame usando la fila de encabezados encontrada
            df = pd.read_excel(file_path, header=header_row_idx) if file_path.endswith(('.xlsx', '.xls')) else pd.read_csv(file_path, header=header_row_idx)
            
            # Normalizar nombres de columnas
            df.columns = df.columns.str.strip()
            
            print(f"   Columnas encontradas: {list(df.columns)}")
            
            # Mapeo de columnas (búsqueda flexible)
            columnas_mapeadas = {}
            
            for col_requerida in self.COLUMNAS_REQUERIDAS:
                col_encontrada = None
                col_req_clean = col_requerida.lower().replace('ó', 'o').replace('á', 'a').replace('é', 'e').replace('í', 'i').replace('ú', 'u')
                
                for col_df in df.columns:
                    col_df_clean = str(col_df).lower().strip().replace('ó', 'o').replace('á', 'a').replace('é', 'e').replace('í', 'i').replace('ú', 'u')
                    
                    if col_req_clean in col_df_clean or col_df_clean in col_req_clean:
                        col_encontrada = col_df
                        break
                
                if col_encontrada:
                    columnas_mapeadas[col_requerida] = col_encontrada
            
            # Crear DataFrame con las columnas requeridas
            df_extraido = pd.DataFrame()
            
            for col_requerida in self.COLUMNAS_REQUERIDAS:
                if col_requerida in columnas_mapeadas:
                    df_extraido[col_requerida] = df[columnas_mapeadas[col_requerida]]
                elif col_requerida == 'Fecha' and fecha_documento:
                    df_extraido[col_requerida] = fecha_documento
                else:
                    df_extraido[col_requerida] = None
                    print(f"   ⚠️ Columna '{col_requerida}' no encontrada")
            
            # Limpiar filas vacías o de resumen
            df_extraido = df_extraido[df_extraido['Número de factura'].notna()].copy()
            df_extraido = df_extraido[~df_extraido['Número de factura'].astype(str).str.upper().str.contains('TOTAL|SUMA', na=False)]
            
            if df_extraido.empty:
                print(f"   ⚠️ No se encontraron registros válidos")
                return None
            
            
            
            self.archivos_procesados.append(file_path)
            print(f"   ✅ {len(df_extraido)} registros extraídos")
            
            return df_extraido
            
        except Exception as e:
            self.errores.append({
                'archivo': file_path,
                'error': str(e)
            })
            print(f"❌ Error procesando {file_path}: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def procesar_multiples_archivos(self, file_paths):
        """
        Procesa múltiples archivos y los consolida en un único DataFrame
        
        Args:
            file_paths: Lista de rutas de archivos a procesar
            
        Returns:
            DataFrame consolidado con todos los registros
        """
        dfs = []
        
        for file_path in file_paths:
            print(f"📄 Procesando: {os.path.basename(file_path)}")
            df = self.procesar_archivo(file_path)
            
            if df is not None and not df.empty:
                dfs.append(df)
                print(f"  ✓ {len(df)} registros extraídos")
        
        if dfs:
            self.df_consolidado = pd.concat(dfs, ignore_index=True)
            print(f"\n✅ Consolidación completada: {len(self.df_consolidado)} registros totales")
            print(f"📋 Columnas extraídas: {list(self.df_consolidado.columns)}")
            
            # NO aplicar homologación aquí - se hará después al exportar
            
            return self.df_consolidado
        else:
            print("\n⚠️ No se pudo procesar ningún archivo")
            return None
    
    def _generar_columna_reg_glosa(self):
        """
        Genera la columna con formato: REG, GLOSA SEGUN RAD N. [número_de_glosa]
        """
        if 'Número de glosa' not in self.df_consolidado.columns:
            print("⚠️ Columna 'Número de glosa' no encontrada")
            return
        
        def crear_reg_glosa(numero_glosa):
            if pd.isna(numero_glosa):
                return ""
            return f"REG, GLOSA SEGUN RAD N. {numero_glosa}"
        
        self.df_consolidado['REG GLOSA'] = self.df_consolidado['Número de glosa'].apply(crear_reg_glosa)
        print("✓ Columna 'REG GLOSA' agregada")
    
    def _generar_archivo_objeciones(self):
        """
        Genera el archivo Objeciones.xlsx con la estructura requerida
        """
        if self.df_consolidado is None or self.df_consolidado.empty:
            print("❌ No hay datos para generar archivo de objeciones")
            return None
        
        try:
            print("\n" + "="*70)
            print("GENERANDO ARCHIVO OBJECIONES.XLSX")
            print("="*70)
            
            # Crear DataFrame con la estructura requerida
            df_objeciones = pd.DataFrame()
            
            # Mapeo de columnas (consolidado -> objeciones)
            # CDCONSEC: Número secuencial (1, 2, 3...)
            df_objeciones['CDCONSEC'] = range(1, len(self.df_consolidado) + 1)
            
            # CDFECDOC: Número de factura
            df_objeciones['CDFECDOC'] = self.df_consolidado.get('Número de factura', '')
            
            # CRNCXC: Número de factura con formato (si es FC0000682556)
            df_objeciones['CRNCXC'] = self.df_consolidado.get('Número de factura', '')
            
            # CROFECOBJ: Fecha - convertir a formato serial de Excel
            def convertir_fecha(fecha):
                if pd.isna(fecha):
                    return ''
                
                # Si ya es un objeto datetime
                if isinstance(fecha, pd.Timestamp) or isinstance(fecha, datetime):
                    # Convertir a número serial de Excel (días desde 1899-12-30)
                    delta = fecha - pd.Timestamp('1899-12-30')
                    return delta.days + (delta.seconds / 86400)
                
                # Si es un string, intentar parsearlo
                if isinstance(fecha, str):
                    try:
                        fecha_dt = pd.to_datetime(fecha, dayfirst=True, errors='coerce')
                        if pd.notna(fecha_dt):
                            delta = fecha_dt - pd.Timestamp('1899-12-30')
                            return delta.days + (delta.seconds / 86400)
                    except:
                        pass
                
                # Si es un número, asumir que ya está en formato serial
                try:
                    return float(fecha)
                except:
                    return ''
            
            df_objeciones['CROFECOBJ'] = self.df_consolidado.get('Fecha', '').apply(convertir_fecha)
            
            # CROREFERE: Valor fijo 0
            df_objeciones['CROREFERE'] = 0
            
            # CROOBSERV: REG, GLOSA SEGUN RAD N. [número_de_glosa]
            df_objeciones['CROOBSERV'] = self.df_consolidado.get('REG GLOSA', '')
            
            # CROCLAOBJ: Valor fijo 0
            df_objeciones['CROCLAOBJ'] = 0
            
            # GENUSUARIO4: Valor fijo 1103858268
            df_objeciones['GENUSUARIO4'] = 1103858268
            
            # CRNCONOBJ: Código de glosa
            df_objeciones['CRNCONOBJ'] = self.df_consolidado.get('Código de glosa', '')
            
            # SLNSERPRO: Código homologado DGH (Tecnología)
            df_objeciones['SLNSERPRO'] = self.df_consolidado.get('Codigo homologado DGH', '')
            
            # CTNCENCOS: Vacío
            df_objeciones['CTNCENCOS'] = ''
            
            # IDRIPS: Vacío
            df_objeciones['IDRIPS'] = ''
            
            # CROVALOBJ: Valor glosado
            df_objeciones['CROVALOBJ'] = self.df_consolidado.get('Valor glosado', 0)
            
            # CRDOBSERV: Concepto de glosa + Observacion
            def combinar_observaciones(row):
                concepto = row.get('Concepto de glosa', '')
                observacion = row.get('Observacion', '')
                
                partes = []
                if pd.notna(concepto) and str(concepto).strip():
                    partes.append(str(concepto).strip())
                if pd.notna(observacion) and str(observacion).strip():
                    partes.append(str(observacion).strip())
                
                return ' - '.join(partes) if partes else ''
            
            df_objeciones['CRDOBSERV'] = self.df_consolidado.apply(combinar_observaciones, axis=1)
            
            # Generar archivo
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            output_path = os.path.join(self.output_dir, f"Objeciones_{timestamp}.xlsx")
            
            # Exportar con nombre de hoja específico
            with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
                df_objeciones.to_excel(writer, sheet_name='OBJECIONES', index=False)
            
            print(f"\n✅ Archivo Objeciones.xlsx generado: {output_path}")
            print(f"   📊 {len(df_objeciones)} registros")
            print(f"   📋 14 columnas")
            
            return output_path
            
        except Exception as e:
            print(f"❌ Error al generar archivo de objeciones: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def exportar_consolidado(self, nombre_archivo=None):
        """
        Exporta el DataFrame consolidado a un archivo Excel
        
        Args:
            nombre_archivo: Nombre del archivo de salida (opcional)
            
        Returns:
            Tupla (ruta_consolidado, ruta_objeciones) o None si hay error
        """
        if self.df_consolidado is None or self.df_consolidado.empty:
            print("❌ No hay datos para exportar")
            return None
        
        try:
            print("\n" + "="*70)
            print("PASO FINAL: APLICANDO HOMOLOGACIÓN DE CÓDIGOS")
            print("="*70)
            
            # Aplicar homologación ANTES de exportar
            self._aplicar_homologacion()
            
            # Generar columna REG GLOSA
            self._generar_columna_reg_glosa()
            
            print("\n" + "="*70)
            print("EXPORTANDO ARCHIVO CONSOLIDADO")
            print("="*70)
            
            # Generar nombre de archivo si no se proporciona
            if nombre_archivo is None:
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                nombre_archivo = f"MUTUALSER_consolidado_{timestamp}.xlsx"
            
            output_path = os.path.join(self.output_dir, nombre_archivo)
            
            # Reordenar columnas para que REG GLOSA esté después de Número de glosa
            columnas = list(self.df_consolidado.columns)
            if 'REG GLOSA' in columnas and 'Número de glosa' in columnas:
                columnas.remove('REG GLOSA')
                idx_glosa = columnas.index('Número de glosa')
                columnas.insert(idx_glosa + 1, 'REG GLOSA')
                self.df_consolidado = self.df_consolidado[columnas]
            
            # Exportar a Excel
            self.df_consolidado.to_excel(output_path, index=False)
            
            print(f"\n✅ Archivo consolidado exportado: {output_path}")
            print(f"   📊 {len(self.df_consolidado)} registros")
            print(f"   📁 {len(self.archivos_procesados)} archivos procesados")
            
            # Generar archivo de objeciones
            objeciones_path = self._generar_archivo_objeciones()
            
            return (output_path, objeciones_path)
            
        except Exception as e:
            print(f"❌ Error al exportar: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def get_resumen(self):
        """
        Obtiene un resumen del procesamiento
        
        Returns:
            Diccionario con estadísticas del procesamiento
        """
        if self.df_consolidado is None:
            return {
                'total_registros': 0,
                'archivos_procesados': 0,
                'errores': len(self.errores)
            }
        
        resumen = {
            'total_registros': len(self.df_consolidado),
            'archivos_procesados': len(self.archivos_procesados),
            'errores': len(self.errores),
            'facturas_unicas': self.df_consolidado['Número de factura'].nunique() if 'Número de factura' in self.df_consolidado.columns else 0,
            'glosas_unicas': self.df_consolidado['Número de glosa'].nunique() if 'Número de glosa' in self.df_consolidado.columns else 0,
            'valor_total_facturado': self.df_consolidado['Valor Facturado'].sum() if 'Valor Facturado' in self.df_consolidado.columns else 0,
            'valor_total_glosado': self.df_consolidado['Valor glosado'].sum() if 'Valor glosado' in self.df_consolidado.columns else 0,
            'codigos_homologados': self.df_consolidado['Codigo homologado DGH'].notna().sum() if 'Codigo homologado DGH' in self.df_consolidado.columns else 0,
        }
        
        return resumen
    
    def get_facturas_unicas(self):
        """
        Obtiene lista de facturas únicas procesadas
        
        Returns:
            Lista de números de factura únicos
        """
        if self.df_consolidado is None or 'Número de factura' not in self.df_consolidado.columns:
            return []
        
        return self.df_consolidado['Número de factura'].unique().tolist()


class CosaludProcessor:
    """
    Procesador específico para archivos de COSALUD
    (A implementar según estructura de COSALUD)
    """
    
    def __init__(self, output_dir='outputs'):
        self.output_dir = output_dir
        self.df_consolidado = None
        os.makedirs(output_dir, exist_ok=True)
    
    def procesar_archivo(self, file_path):
        """
        Procesa un archivo individual de COSALUD
        TODO: Implementar según estructura específica de COSALUD
        """
        raise NotImplementedError("Procesador de COSALUD pendiente de implementar")
    
    def procesar_multiples_archivos(self, file_paths):
        """
        Procesa múltiples archivos de COSALUD
        TODO: Implementar según estructura específica de COSALUD
        """
        raise NotImplementedError("Procesador de COSALUD pendiente de implementar")
