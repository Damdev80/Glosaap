"""
Procesador específico para MUTUALSER
Maneja la extracción, homologación y generación de archivos de objeciones
"""
import pandas as pd
import os
from datetime import datetime


class MutualserProcessor:
    """
    Procesador para archivos de MUTUALSER
    """
    
    COLUMNAS_REQUERIDAS = [
        'Número de factura', 'Número de glosa', 'Tecnología',
        'Cantidad facturada', 'Valor Facturado', 'Cantidad glosada',
        'Valor glosado', 'Concepto de glosa', 'Código de glosa',
        'Observacion', 'Fecha'
    ]
    
    # Ruta de red para homologación
    HOMOLOGACION_PATH = r"\\MINERVA\Cartera\GLOSAAP\HOMOLOGADOR\mutualser_homologacion.xlsx"
    
    def __init__(self, output_dir='outputs', homologacion_path=None):
        self.output_dir = output_dir
        self.homologacion_path = homologacion_path or self.HOMOLOGACION_PATH
        self.df_consolidado = None
        self.df_homologacion = None
        self.archivos_procesados = []
        self.errores = []
        self._todos_cod_serv_fact = None
        
        # Crear directorio si no existe (funciona con rutas de red)
        try:
            os.makedirs(output_dir, exist_ok=True)
        except Exception as e:
            print(f"⚠️ No se pudo crear directorio {output_dir}: {e}")
        
        self._cargar_homologacion()
    
    # ==================== HOMOLOGACIÓN ====================
    
    def _cargar_homologacion(self):
        """Carga el archivo de homologación"""
        try:
            # Verificar directorio y listar archivos disponibles
            homolog_dir = r"\\MINERVA\Cartera\GLOSAAP\HOMOLOGADOR"
            print(f"🔍 Buscando archivos de homologación en: {homolog_dir}")
            
            if os.path.exists(homolog_dir):
                archivos = [f for f in os.listdir(homolog_dir) if f.lower().endswith(('.xlsx', '.xls'))]
                print(f"📁 Archivos Excel encontrados: {archivos}")
                
                # Buscar archivo específico o usar el primero disponible
                archivo_encontrado = None
                for archivo in archivos:
                    if 'mutualser' in archivo.lower() and 'homolog' in archivo.lower():
                        archivo_encontrado = os.path.join(homolog_dir, archivo)
                        break
                
                if not archivo_encontrado and archivos:
                    archivo_encontrado = os.path.join(homolog_dir, archivos[0])
                    print(f"⚠️ Usando primer archivo disponible: {archivos[0]}")
                
                if archivo_encontrado:
                    self.homologacion_path = archivo_encontrado
                    print(f"📋 Intentando cargar: {archivo_encontrado}")
                else:
                    print("❌ No se encontraron archivos Excel de homologación")
                    self.df_homologacion = None
                    return
            else:
                print(f"❌ Directorio de homologación no accesible: {homolog_dir}")
                self.df_homologacion = None
                return
            
            # Cargar archivo de homologación
            self.df_homologacion = pd.read_excel(self.homologacion_path)
            self.df_homologacion.columns = self.df_homologacion.columns.str.strip()
            
            print(f"📊 Columnas encontradas: {list(self.df_homologacion.columns)}")
            
            # Pre-calcular conjunto de COD_SERV_FACT para búsquedas rápidas
            if 'COD_SERV_FACT' in self.df_homologacion.columns:
                self._todos_cod_serv_fact = set(
                    self.df_homologacion['COD_SERV_FACT']
                    .dropna().astype(str).str.strip().tolist()
                )
                self._todos_cod_serv_fact.discard('0')
                self._todos_cod_serv_fact.discard('')
                print(f"🔑 Códigos de homologación cargados: {len(self._todos_cod_serv_fact)}")
            else:
                print("⚠️ Columna 'COD_SERV_FACT' no encontrada en archivo de homologación")
            
            print(f"✅ Homologación cargada exitosamente: {len(self.df_homologacion)} registros")
            
        except Exception as e:
            print(f"❌ Error cargando homologación: {e}")
            self.df_homologacion = None
    
    def _buscar_codigo_homologado(self, codigo_tecnologia):
        """
        Busca código homologado:
        1. Buscar en 'Código Servicio de la ERP'
        2. Tomar 'Código producto en DGH' de esa fila
        3. Verificar si existe en COD_SERV_FACT
        """
        if self.df_homologacion is None or pd.isna(codigo_tecnologia):
            return ''
        
        try:
            codigo_str = str(codigo_tecnologia).strip()
            if not codigo_str or codigo_str == 'nan':
                return ''
            
            col_erp = 'Código Servicio de la ERP'
            col_producto = 'Código producto en DGH'
            
            # Verificar columnas
            for col in [col_erp, col_producto, 'COD_SERV_FACT']:
                if col not in self.df_homologacion.columns:
                    return ''
            
            codigo_numerico = ''.join(filter(str.isdigit, codigo_str))
            
            # Buscar en Código Servicio de la ERP
            mask = self.df_homologacion[col_erp].astype(str).str.strip() == codigo_str
            resultado = self.df_homologacion[mask]
            
            if resultado.empty and codigo_numerico:
                mask = self.df_homologacion[col_erp].astype(str).str.replace(r'\D', '', regex=True) == codigo_numerico
                resultado = self.df_homologacion[mask]
            
            if not resultado.empty:
                codigo_producto = resultado.iloc[0][col_producto]
                
                if pd.notna(codigo_producto):
                    cod_str = str(codigo_producto).strip()
                    
                    if cod_str and cod_str != '0' and cod_str != 'nan':
                        # Verificar si existe en COD_SERV_FACT
                        if cod_str in self._todos_cod_serv_fact:
                            return cod_str
                        
                        # Búsqueda flexible
                        cod_numerico = ''.join(filter(str.isdigit, cod_str))
                        if cod_numerico:
                            for cod in self._todos_cod_serv_fact:
                                if ''.join(filter(str.isdigit, cod)) == cod_numerico:
                                    return cod
            
            return ''
            
        except Exception as e:
            print(f"⚠️ Error homologando {codigo_tecnologia}: {e}")
            return ''
    
    def _aplicar_homologacion(self):
        """Aplica homologación a todos los registros"""
        if self.df_consolidado is None or self.df_consolidado.empty:
            return
        
        if self.df_homologacion is None:
            self.df_consolidado['Codigo homologado DGH'] = ''
            return
        
        print("\n🔄 Aplicando homologación...")
        
        codigos = []
        encontrados = 0
        
        for _, row in self.df_consolidado.iterrows():
            codigo = self._buscar_codigo_homologado(row.get('Tecnología'))
            codigos.append(codigo)
            if codigo:
                encontrados += 1
        
        self.df_consolidado['Codigo homologado DGH'] = codigos
        self.df_consolidado['Tecnologia NO homologada'] = self.df_consolidado.apply(
            lambda r: r['Tecnología'] if not r.get('Codigo homologado DGH') else '', axis=1
        )
        
        print(f"✅ Homologados: {encontrados}/{len(self.df_consolidado)}")
    
    # ==================== PROCESAMIENTO DE ARCHIVOS ====================
    
    def procesar_archivo(self, file_path):
        """Procesa un archivo individual"""
        try:
            if not file_path.endswith(('.xlsx', '.xls', '.csv')):
                self.errores.append({'archivo': file_path, 'error': 'Formato no soportado'})
                return None
            
            df_raw = pd.read_excel(file_path, header=None) if file_path.endswith(('.xlsx', '.xls')) else pd.read_csv(file_path, header=None)
            
            # Buscar fila de encabezados
            header_row_idx = None
            fecha_documento = None
            
            for idx, row in df_raw.iterrows():
                row_str = ' '.join([str(c) for c in row if pd.notna(c)]).upper()
                
                if 'FECHA' in row_str and fecha_documento is None:
                    for cell in row:
                        if pd.notna(cell) and ('/' in str(cell) or '-' in str(cell)):
                            try:
                                fecha_documento = pd.to_datetime(cell).strftime('%Y-%m-%d')
                                break
                            except:
                                pass
                
                if 'NUMERO DE FACTURA' in row_str or 'NÚMERO DE FACTURA' in row_str:
                    header_row_idx = idx
                    break
                elif 'DETALLE DE GLOSA' in row_str:
                    header_row_idx = idx + 1
                    break
            
            if header_row_idx is None:
                raise Exception("No se encontró tabla de detalles")
            
            df = pd.read_excel(file_path, header=header_row_idx) if file_path.endswith(('.xlsx', '.xls')) else pd.read_csv(file_path, header=header_row_idx)
            df.columns = df.columns.str.strip()
            
            # Mapear columnas
            df_extraido = self._mapear_columnas(df, fecha_documento)
            
            if df_extraido.empty:
                return None
            
            self.archivos_procesados.append(file_path)
            print(f"   ✅ {len(df_extraido)} registros de {os.path.basename(file_path)}")
            
            return df_extraido
            
        except Exception as e:
            self.errores.append({'archivo': file_path, 'error': str(e)})
            print(f"❌ Error: {file_path}: {e}")
            return None
    
    def _mapear_columnas(self, df, fecha_documento):
        """Mapea columnas del archivo a las requeridas"""
        print(f"   🔍 Columnas disponibles: {list(df.columns)}")
        
        df_extraido = pd.DataFrame()
        columnas_no_encontradas = []
        
        for col_req in self.COLUMNAS_REQUERIDAS:
            col_encontrada = self._buscar_columna(df, col_req)
            
            if col_encontrada:
                df_extraido[col_req] = df[col_encontrada]
                print(f"   ✅ '{col_req}' → '{col_encontrada}'")
            elif col_req == 'Fecha' and fecha_documento:
                df_extraido[col_req] = fecha_documento
                print(f"   ✅ '{col_req}' → fecha extraída: {fecha_documento}")
            else:
                df_extraido[col_req] = None
                columnas_no_encontradas.append(col_req)
        
        if columnas_no_encontradas:
            print(f"   ⚠️  Columnas no encontradas: {columnas_no_encontradas}")
        
        # Limpiar filas
        filas_antes = len(df_extraido)
        df_extraido = df_extraido[df_extraido['Número de factura'].notna()].copy()
        df_extraido = df_extraido[~df_extraido['Número de factura'].astype(str).str.upper().str.contains('TOTAL|SUMA', na=False)]
        filas_despues = len(df_extraido)
        
        print(f"   🧹 Limpieza: {filas_antes} → {filas_despues} registros")
        
        return df_extraido
    
    def _buscar_columna(self, df, col_requerida):
        """Busca columna de forma flexible"""
        col_clean = col_requerida.lower().replace('ó', 'o').replace('á', 'a').replace('é', 'e').replace('í', 'i').replace('ú', 'u')
        
        for col_df in df.columns:
            col_df_clean = str(col_df).lower().strip().replace('ó', 'o').replace('á', 'a').replace('é', 'e').replace('í', 'i').replace('ú', 'u')
            if col_clean in col_df_clean or col_df_clean in col_clean:
                return col_df
        return None
    
    def procesar_multiples_archivos(self, file_paths):
        """Procesa múltiples archivos"""
        print(f"\n🔄 Procesando {len(file_paths)} archivos:")
        for fp in file_paths:
            print(f"   📄 {os.path.basename(fp)}")
        
        dfs = []
        
        for i, file_path in enumerate(file_paths):
            print(f"\n📄 Procesando archivo {i+1}/{len(file_paths)}: {os.path.basename(file_path)}")
            df = self.procesar_archivo(file_path)
            if df is not None and not df.empty:
                dfs.append(df)
                # Debug: mostrar facturas únicas en este archivo
                facturas = df['Número de factura'].unique()
                print(f"   📊 Facturas en este archivo: {len(facturas)}")
                print(f"   🏷️  Primeras 5 facturas: {facturas[:5]}")
            else:
                print(f"   ❌ Archivo vacío o con errores: {os.path.basename(file_path)}")
        
        if dfs:
            self.df_consolidado = pd.concat(dfs, ignore_index=True)
            print(f"\n✅ Consolidado final: {len(self.df_consolidado)} registros")
            facturas_totales = self.df_consolidado['Número de factura'].unique()
            print(f"📊 Total facturas únicas: {len(facturas_totales)}")
            print(f"🏷️  Primeras 10 facturas: {facturas_totales[:10]}")
            return self.df_consolidado
        
        return None
    
    # ==================== GENERACIÓN DE OBJECIONES ====================
    
    def _generar_archivo_objeciones(self):
        """Genera archivo Objeciones.xlsx"""
        if self.df_consolidado is None or self.df_consolidado.empty:
            return None
        
        try:
            print("\n📄 Generando Objeciones.xlsx...")
            
            df_obj = pd.DataFrame()
            
            # Columnas básicas
            facturas = self.df_consolidado.get('Número de factura', pd.Series())
            factura_consecutivo = {f: i+1 for i, f in enumerate(facturas.unique())}
            
            df_obj['CDCONSEC'] = facturas.map(factura_consecutivo)
            df_obj['CDFECDOC'] = datetime.now().strftime('%#m/%#d/%Y') if os.name == 'nt' else datetime.now().strftime('%-m/%-d/%Y')
            df_obj['CRNCXC'] = self.df_consolidado.get('Número de factura', '').apply(self._formatear_crncxc)
            df_obj['CROFECOBJ'] = self.df_consolidado.get('Fecha', '').apply(self._formatear_fecha_dmy)
            df_obj['CROREFERE'] = ''
            df_obj['CROOBSERV'] = self.df_consolidado.get('REG GLOSA', '')
            df_obj['CROCLAOBJ'] = 0
            df_obj['GENUSUARIO4'] = 1103858268
            df_obj['CRNCONOBJ'] = self.df_consolidado.get('Código de glosa', '')
            df_obj['SLNSERPRO'] = self.df_consolidado.get('Codigo homologado DGH', '')
            df_obj['CTNCENCOS'] = ''
            df_obj['IDRIPS'] = ''
            df_obj['CROVALOBJ'] = self.df_consolidado.get('Valor glosado', 0).apply(self._obtener_valor_numerico)
            df_obj['CRDOBSERV'] = self.df_consolidado.apply(self._combinar_observaciones, axis=1)
            
            # Procesar AU/TA
            df_obj = self._procesar_au_ta(df_obj)
            
            # Exportar
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            output_path = os.path.join(self.output_dir, f"Objeciones_{timestamp}.xlsx")
            
            with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
                df_obj.to_excel(writer, sheet_name='OBJECIONES', index=False)
            
            print(f"✅ Generado: {output_path} ({len(df_obj)} registros)")
            return output_path
            
        except Exception as e:
            print(f"❌ Error generando objeciones: {e}")
            return None
    
    def _procesar_au_ta(self, df_obj):
        """Procesa filas AU/TA: combina y elimina duplicados"""
        print("🔄 Procesando AU/TA...")
        
        filas_eliminar = []
        procesadas = 0
        
        for (factura, tec), grupo in df_obj.groupby(['CRNCXC', 'SLNSERPRO']):
            if len(grupo) < 2:
                continue
            
            filas_au = [i for i, r in grupo.iterrows() if str(r.get('CRNCONOBJ', '')).upper().startswith('AU')]
            filas_ta = [i for i, r in grupo.iterrows() if str(r.get('CRNCONOBJ', '')).upper().startswith('TA')]
            
            if filas_au and filas_ta:
                idx_au = filas_au[0]
                
                for idx_ta in filas_ta:
                    obs_ta = str(df_obj.at[idx_ta, 'CRDOBSERV']).strip()
                    if obs_ta:
                        obs_au = str(df_obj.at[idx_au, 'CRDOBSERV']).strip()
                        df_obj.at[idx_au, 'CRDOBSERV'] = f"{obs_au} \\\\ {obs_ta}" if obs_au else f"\\\\ {obs_ta}"
                    
                    filas_eliminar.append(idx_ta)
                    procesadas += 1
        
        if filas_eliminar:
            df_obj = df_obj.drop(filas_eliminar).reset_index(drop=True)
            print(f"   ✅ {procesadas} filas TA procesadas")
        
        return df_obj
    
    # ==================== UTILIDADES DE FORMATO ====================
    
    def _formatear_crncxc(self, valor):
        if pd.isna(valor) or not valor:
            return ''
        valor_str = str(valor).strip()
        if valor_str.upper().startswith('FC'):
            return f"FC0000{valor_str[2:]}"
        return f"FC0000{valor_str}"
    
    def _formatear_fecha_dmy(self, fecha):
        if pd.isna(fecha) or not fecha:
            return ''
        try:
            if isinstance(fecha, (pd.Timestamp, datetime)):
                return fecha.strftime('%d/%m/%Y')
            fecha_dt = pd.to_datetime(str(fecha), errors='coerce')
            return fecha_dt.strftime('%d/%m/%Y') if pd.notna(fecha_dt) else ''
        except:
            return ''
    
    def _obtener_valor_numerico(self, valor):
        if pd.isna(valor) or not valor:
            return 0
        try:
            if isinstance(valor, (int, float)):
                return int(valor)
            valor_str = str(valor).replace('$', '').replace(' ', '').replace('.', '').replace(',', '').strip()
            return int(float(valor_str)) if valor_str else 0
        except:
            return 0
    
    def _combinar_observaciones(self, row):
        partes = []
        for col in ['Concepto de glosa', 'Observacion']:
            val = row.get(col, '')
            if pd.notna(val) and str(val).strip():
                partes.append(str(val).strip())
        return ' - '.join(partes)
    
    # ==================== EXPORTACIÓN ====================
    
    def exportar_consolidado(self, nombre_archivo=None):
        """Exporta consolidado y genera objeciones"""
        if self.df_consolidado is None or self.df_consolidado.empty:
            print("❌ No hay datos")
            return None
        
        try:
            # Filtrar filas vacías (sin Tecnología o sin Número de factura)
            filas_antes = len(self.df_consolidado)
            self.df_consolidado = self.df_consolidado[
                self.df_consolidado['Tecnología'].notna() & 
                self.df_consolidado['Número de factura'].notna()
            ].copy()
            filas_despues = len(self.df_consolidado)
            
            if filas_antes != filas_despues:
                print(f"🧹 Filtrado: {filas_antes} → {filas_despues} registros (eliminadas {filas_antes - filas_despues} filas vacías)")
            
            if self.df_consolidado.empty:
                print("❌ No hay datos válidos después del filtrado")
                return None
            
            # Homologar
            self._aplicar_homologacion()
            
            # Generar REG GLOSA
            self.df_consolidado['REG GLOSA'] = self.df_consolidado['Número de glosa'].apply(
                lambda x: f"REG, GLOSA SEGUN RAD N. {x}" if pd.notna(x) else ""
            )
            
            # Exportar consolidado
            if nombre_archivo is None:
                nombre_archivo = f"MUTUALSER_consolidado_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
            
            output_path = os.path.join(self.output_dir, nombre_archivo)
            self.df_consolidado.to_excel(output_path, index=False)
            print(f"\n✅ Consolidado: {output_path}")
            
            # Generar objeciones
            objeciones_path = self._generar_archivo_objeciones()
            
            return (output_path, objeciones_path)
            
        except Exception as e:
            print(f"❌ Error: {e}")
            return None
    
    def get_resumen(self):
        """Obtiene resumen del procesamiento"""
        if self.df_consolidado is None:
            return {'total_registros': 0, 'archivos_procesados': 0, 'errores': len(self.errores)}
        
        return {
            'total_registros': len(self.df_consolidado),
            'archivos_procesados': len(self.archivos_procesados),
            'errores': len(self.errores),
            'facturas_unicas': self.df_consolidado['Número de factura'].nunique(),
            'codigos_homologados': (self.df_consolidado.get('Codigo homologado DGH', '') != '').sum()
        }
