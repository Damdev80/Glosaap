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
        Busca el código homologado según las reglas de negocio:
        
        FLUJO CORRECTO:
        1. Tomar código de la factura (Tecnología)
        2. Buscar ese código en 'Código Servicio de la ERP'
        3. De esa fila, tomar el valor de 'Código producto en DGH'
        4. Buscar ese valor en TODA la columna 'COD_SERV_FACT'
        5. Si existe en COD_SERV_FACT → devolverlo
        6. Si no existe → dejar en blanco
        
        Args:
            codigo_tecnologia: Código a buscar (de la columna Tecnología)
            
        Returns:
            Código homologado que exista en COD_SERV_FACT, o cadena vacía
        """
        if self.df_homologacion is None or pd.isna(codigo_tecnologia):
            return ''
        
        try:
            # Convertir código a string y limpiar
            codigo_str = str(codigo_tecnologia).strip()
            
            # Si está vacío, retornar vacío
            if not codigo_str or codigo_str == 'nan':
                return ''
            
            # Nombres de columnas
            columna_erp = 'Código Servicio de la ERP'
            columna_codigo_producto = 'Código producto en DGH'
            columna_cod_serv_fact = 'COD_SERV_FACT'
            
            # Verificar que las columnas existen
            if columna_erp not in self.df_homologacion.columns:
                print(f"❌ Columna '{columna_erp}' no encontrada")
                return ''
            if columna_codigo_producto not in self.df_homologacion.columns:
                print(f"❌ Columna '{columna_codigo_producto}' no encontrada")
                return ''
            if columna_cod_serv_fact not in self.df_homologacion.columns:
                print(f"❌ Columna '{columna_cod_serv_fact}' no encontrada")
                return ''
            
            # Crear conjunto de todos los valores válidos en COD_SERV_FACT para búsqueda rápida
            todos_cod_serv_fact = set(
                self.df_homologacion[columna_cod_serv_fact]
                .dropna()
                .astype(str)
                .str.strip()
                .tolist()
            )
            todos_cod_serv_fact.discard('0')
            todos_cod_serv_fact.discard('')
            
            # Extraer solo dígitos del código para comparación flexible
            codigo_numerico = ''.join(filter(str.isdigit, codigo_str))
            
            # PASO 1: Buscar en 'Código Servicio de la ERP'
            mask = self.df_homologacion[columna_erp].astype(str).str.strip() == codigo_str
            resultado = self.df_homologacion[mask]
            
            # Búsqueda flexible si no encuentra exacto (solo por parte numérica)
            if resultado.empty and codigo_numerico:
                mask = self.df_homologacion[columna_erp].astype(str).str.replace(r'\D', '', regex=True) == codigo_numerico
                resultado = self.df_homologacion[mask]
            
            if not resultado.empty:
                # PASO 2: De esa fila, tomar el valor de 'Código producto en DGH'
                codigo_producto_dgh = resultado.iloc[0][columna_codigo_producto]
                
                if pd.notna(codigo_producto_dgh):
                    codigo_producto_str = str(codigo_producto_dgh).strip()
                    
                    if codigo_producto_str and codigo_producto_str != '0' and codigo_producto_str != 'nan':
                        # PASO 3: Buscar ese valor en TODA la columna COD_SERV_FACT
                        if codigo_producto_str in todos_cod_serv_fact:
                            # ✅ El código existe en COD_SERV_FACT
                            return codigo_producto_str
                        
                        # Búsqueda flexible por parte numérica
                        codigo_producto_numerico = ''.join(filter(str.isdigit, codigo_producto_str))
                        if codigo_producto_numerico:
                            for cod in todos_cod_serv_fact:
                                cod_numerico = ''.join(filter(str.isdigit, cod))
                                if cod_numerico == codigo_producto_numerico:
                                    return cod
            
            # No se encontró
            return ''
            
        except Exception as e:
            print(f"   ⚠️ Error buscando código {codigo_tecnologia}: {e}")
            import traceback
            traceback.print_exc()
            return ''
    
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
                print(f"     {idx+1}. '{codigo_str}' -> {len(codigo_num)} dígitos -> Buscar en: Código producto en DGH -> COD_SERV_FACT")
        
        # Crear nueva columna con códigos homologados
        codigos_homologados = []
        total = len(self.df_consolidado)
        encontrados = 0
        errores_busqueda = []
        
        for idx, row in self.df_consolidado.iterrows():
            codigo_tecnologia = row.get('Tecnología')
            codigo_homologado = self._buscar_codigo_homologado(codigo_tecnologia)
            codigos_homologados.append(codigo_homologado)
            
            # Ahora codigo_homologado retorna '' si no encuentra, no None
            if codigo_homologado and codigo_homologado != '':
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
        
        # Agregar columna de tecnologías NO homologadas
        def marcar_no_homologado(row):
            codigo_hom = row.get('Codigo homologado DGH')
            tecnologia = row.get('Tecnología')
            if pd.isna(codigo_hom) or codigo_hom == '' or codigo_hom is None:
                return tecnologia if pd.notna(tecnologia) else ''
            return ''
        
        self.df_consolidado['Tecnologia NO homologada'] = self.df_consolidado.apply(marcar_no_homologado, axis=1)
        
        print(f"\n✅ Homologación completada:")
        print(f"   • Total de registros: {total}")
        print(f"   • Códigos homologados encontrados: {encontrados}")
        print(f"   • Sin homologar: {total - encontrados}")
        
        if errores_busqueda:
            print(f"\n   ⚠️ Ejemplos de códigos NO encontrados:")
            for codigo in errores_busqueda:
                print(f"     - {codigo}")
            #hay que agregar un mensaje de error en esa columna si no se encuentra el código homologado
            self.df_consolidado['Codigo homologado DGH'] = self.df_consolidado['Codigo homologado DGH'].fillna('')        
        
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
            
            # Función para formatear fecha a DD/MM/YYYY
            def formatear_fecha_ddmmyyyy(fecha):
                if pd.isna(fecha) or fecha == '' or fecha is None:
                    return ''
                
                try:
                    # Si ya es un objeto datetime o Timestamp
                    if isinstance(fecha, (pd.Timestamp, datetime)):
                        return fecha.strftime('%d/%m/%Y')
                    
                    # Si es un string, intentar parsearlo
                    if isinstance(fecha, str):
                        fecha_str = fecha.strip()
                        if not fecha_str:
                            return ''
                        
                        # Intentar varios formatos
                        for fmt in ['%Y-%m-%d', '%d/%m/%Y', '%d-%m-%Y', '%m/%d/%Y']:
                            try:
                                fecha_dt = datetime.strptime(fecha_str, fmt)
                                return fecha_dt.strftime('%d/%m/%Y')
                            except:
                                continue
                        
                        # Último intento con pandas
                        fecha_dt = pd.to_datetime(fecha_str, errors='coerce')
                        if pd.notna(fecha_dt):
                            return fecha_dt.strftime('%d/%m/%Y')
                    
                    # Si es un número (serial de Excel), convertir
                    if isinstance(fecha, (int, float)):
                        fecha_dt = pd.Timestamp('1899-12-30') + pd.Timedelta(days=int(fecha))
                        return fecha_dt.strftime('%d/%m/%Y')
                        
                except Exception as e:
                    print(f"⚠️ Error formateando fecha '{fecha}': {e}")
                
                return ''
            
            # Función para formatear fecha a M/D/Y (mes/día/año)
            def formatear_fecha_mdy(fecha):
                if pd.isna(fecha) or fecha == '' or fecha is None:
                    return ''
                
                try:
                    # Si ya es un objeto datetime o Timestamp
                    if isinstance(fecha, (pd.Timestamp, datetime)):
                        return fecha.strftime('%-m/%-d/%Y') if os.name != 'nt' else fecha.strftime('%#m/%#d/%Y')
                    
                    # Si es un string, intentar parsearlo
                    if isinstance(fecha, str):
                        fecha_str = fecha.strip()
                        if not fecha_str:
                            return ''
                        
                        # Intentar varios formatos
                        for fmt in ['%Y-%m-%d', '%d/%m/%Y', '%d-%m-%Y', '%m/%d/%Y']:
                            try:
                                fecha_dt = datetime.strptime(fecha_str, fmt)
                                # En Windows usar %#m/%#d, en Linux usar %-m/%-d (sin ceros)
                                return fecha_dt.strftime('%#m/%#d/%Y') if os.name == 'nt' else fecha_dt.strftime('%-m/%-d/%Y')
                            except:
                                continue
                        
                        # Último intento con pandas
                        fecha_dt = pd.to_datetime(fecha_str, errors='coerce')
                        if pd.notna(fecha_dt):
                            return fecha_dt.strftime('%#m/%#d/%Y') if os.name == 'nt' else fecha_dt.strftime('%-m/%-d/%Y')
                    
                    # Si es un número (serial de Excel), convertir
                    if isinstance(fecha, (int, float)):
                        fecha_dt = pd.Timestamp('1899-12-30') + pd.Timedelta(days=int(fecha))
                        return fecha_dt.strftime('%#m/%#d/%Y') if os.name == 'nt' else fecha_dt.strftime('%-m/%-d/%Y')
                        
                except Exception as e:
                    print(f"⚠️ Error formateando fecha '{fecha}': {e}")
                
                return ''
            
            # Mapeo de columnas (consolidado -> objeciones)
            # CDCONSEC: Número consecutivo por factura (mismo consecutivo para misma factura)
            facturas = self.df_consolidado.get('Número de factura', pd.Series())
            facturas_unicas = facturas.unique()
            # Crear diccionario: factura -> número consecutivo
            factura_a_consecutivo = {factura: idx + 1 for idx, factura in enumerate(facturas_unicas)}
            # Asignar consecutivo según la factura
            df_objeciones['CDCONSEC'] = facturas.map(factura_a_consecutivo)
            
            # CDFECDOC: Fecha ACTUAL en formato fecha (M/D/Y)
            fecha_actual = datetime.now()
            fecha_actual_str = fecha_actual.strftime('%#m/%#d/%Y') if os.name == 'nt' else fecha_actual.strftime('%-m/%-d/%Y')
            df_objeciones['CDFECDOC'] = fecha_actual_str
            
            # CRNCXC: Número de factura con 4 ceros después de la C
            # Ej: C123 -> C0000123
            def formatear_crncxc(valor):
                if pd.isna(valor) or valor == '' or valor is None:
                    return ''
                valor_str = str(valor).strip()
                # Si comienza con C o c, agregar 4 ceros después de la C
                if valor_str.upper().startswith('FC'):
                    # Extraer la parte numérica después de la C
                    parte_numerica = valor_str[1:]
                    return f"FC0000{parte_numerica}"
                # Si es solo número, agregar C0000 al inicio
                return f"FC0000{valor_str}"
            
            df_objeciones['CRNCXC'] = self.df_consolidado.get('Número de factura', '').apply(formatear_crncxc)
            
            # CROFECOBJ: Fecha de la FACTURA en formato fecha (D/M/Y)
            fecha_col = self.df_consolidado.get('Fecha')
            if fecha_col is not None:
                df_objeciones['CROFECOBJ'] = fecha_col.apply(formatear_fecha_ddmmyyyy)
            else:
                df_objeciones['CROFECOBJ'] = ''
            
            # CROREFERE: null (vacío)
            df_objeciones['CROREFERE'] = ''
            
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
            
            # CROVALOBJ: Valor glosado (mantener el valor tal cual)
            def obtener_valor_numerico(valor):
                if pd.isna(valor) or valor == '' or valor is None:
                    return 0
                
                try:
                    # Si ya es numérico, retornarlo tal cual
                    if isinstance(valor, (int, float)):
                        return int(valor)
                    
                    # Si es string, limpiar formato
                    valor_str = str(valor).strip()
                    
                    # Remover símbolo $ y espacios
                    valor_str = valor_str.replace('$', '').replace(' ', '').strip()
                    
                    # Si no hay nada, retornar 0
                    if not valor_str:
                        return 0
                    
                    # Detectar formato: si tiene punto como separador de miles (ej: 30.000)
                    # y NO tiene coma, entonces el punto es separador de miles
                    if '.' in valor_str and ',' not in valor_str:
                        # Verificar si parece separador de miles (grupos de 3 dígitos después del punto)
                        partes = valor_str.split('.')
                        # Si todas las partes después de la primera tienen 3 dígitos, es separador de miles
                        es_separador_miles = all(len(p) == 3 for p in partes[1:])
                        if es_separador_miles:
                            # Quitar los puntos (son separadores de miles)
                            valor_str = valor_str.replace('.', '')
                    
                    # Si tiene coma, puede ser decimal (formato español) o separador de miles
                    if ',' in valor_str:
                        # Si tiene punto Y coma, el punto es miles y coma es decimal
                        if '.' in valor_str:
                            valor_str = valor_str.replace('.', '').replace(',', '.')
                        else:
                            # Solo coma: verificar si es decimal o miles
                            partes = valor_str.split(',')
                            if len(partes) == 2 and len(partes[1]) <= 2:
                                # Probablemente es decimal (ej: 30,50)
                                valor_str = valor_str.replace(',', '.')
                            else:
                                # Es separador de miles
                                valor_str = valor_str.replace(',', '')
                    
                    # Convertir a número entero (sin decimales)
                    return int(float(valor_str))
                except:
                    return 0
            
            valor_glosado_col = self.df_consolidado.get('Valor glosado')
            if valor_glosado_col is not None:
                df_objeciones['CROVALOBJ'] = valor_glosado_col.apply(obtener_valor_numerico)
            else:
                df_objeciones['CROVALOBJ'] = 0
            
            # CRDOBSERV: Concepto de glosa + Observacion (limpiar encoding)
            def limpiar_texto(texto):
                if pd.isna(texto) or texto is None:
                    return ''
                texto_str = str(texto).strip()
                # Normalizar caracteres problemáticos
                try:
                    return texto_str.encode('utf-8', errors='replace').decode('utf-8')
                except:
                    return texto_str
            
            def combinar_observaciones(row):
                concepto = row.get('Concepto de glosa', '')
                observacion = row.get('Observacion', '')
                
                partes = []
                if pd.notna(concepto) and str(concepto).strip():
                    partes.append(limpiar_texto(concepto))
                if pd.notna(observacion) and str(observacion).strip():
                    partes.append(limpiar_texto(observacion))
                
                return ' - '.join(partes) if partes else ''
            
            df_objeciones['CRDOBSERV'] = self.df_consolidado.apply(combinar_observaciones, axis=1)
            
            # ==================== PROCESAR FILAS AU/TA ====================
            # Regla: Si hay filas con misma factura + misma tecnología donde una tiene
            # CRNCONOBJ que empieza con "AU" y otra con "TA":
            # 1. Copiar CRDOBSERV de la fila TA
            # 2. Eliminar la fila TA
            # 3. Agregar a CRDOBSERV de AU: "\\ " + texto copiado
            
            print("\n🔄 Procesando filas AU/TA duplicadas...")
            
            filas_a_eliminar = []
            filas_procesadas = 0
            
            # Agrupar por factura + tecnología (SLNSERPRO)
            for (factura, tecnologia), grupo in df_objeciones.groupby(['CRNCXC', 'SLNSERPRO']):
                if len(grupo) < 2:
                    continue
                
                # Buscar filas AU y TA
                filas_au = []
                filas_ta = []
                
                for idx, row in grupo.iterrows():
                    crnconobj = str(row.get('CRNCONOBJ', '')).strip().upper()
                    if crnconobj.startswith('AU'):
                        filas_au.append(idx)
                    elif crnconobj.startswith('TA'):
                        filas_ta.append(idx)
                
                # Si hay al menos una AU y una TA
                if filas_au and filas_ta:
                    # Tomar la primera AU y procesar todas las TA
                    idx_au = filas_au[0]
                    
                    for idx_ta in filas_ta:
                        # Copiar CRDOBSERV de TA
                        crdobserv_ta = str(df_objeciones.at[idx_ta, 'CRDOBSERV']).strip()
                        
                        if crdobserv_ta:
                            # Agregar a CRDOBSERV de AU con "\\ "
                            crdobserv_au = str(df_objeciones.at[idx_au, 'CRDOBSERV']).strip()
                            if crdobserv_au:
                                df_objeciones.at[idx_au, 'CRDOBSERV'] = f"{crdobserv_au} \\\\ {crdobserv_ta}"
                            else:
                                df_objeciones.at[idx_au, 'CRDOBSERV'] = f"\\\\ {crdobserv_ta}"
                        
                        # Marcar fila TA para eliminar
                        filas_a_eliminar.append(idx_ta)
                        filas_procesadas += 1
            
            # Eliminar filas TA
            if filas_a_eliminar:
                df_objeciones = df_objeciones.drop(filas_a_eliminar)
                df_objeciones = df_objeciones.reset_index(drop=True)
                print(f"   ✅ {filas_procesadas} filas TA procesadas y eliminadas")
            else:
                print(f"   ℹ️ No se encontraron filas AU/TA duplicadas para procesar")
            
            # ==================== FIN PROCESAR AU/TA ====================
            
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
