"""
Servicio CRUD para gestionar archivos de homologación de múltiples EPS
Permite agregar, editar, eliminar y consultar códigos de homologación
con sistema de caché optimizado para mejorar rendimiento
"""
import pandas as pd
import os
from datetime import datetime
import shutil
from typing import Optional, Dict, Any
from functools import lru_cache
import hashlib


class HomologacionService:
    """
    Servicio para gestionar archivos de homologación de múltiples EPS
    con sistema de caché optimizado para mejorar rendimiento de búsquedas
    """
    
    # Ruta base del directorio de homologación en red
    HOMOLOGACION_DIR = r"\\MINERVA\Cartera\GLOSAAP\HOMOLOGADOR"
    
    # Archivos de homologación por EPS
    EPS_FILES = {
        "mutualser": "mutualser_homologacion.xlsx",
        "coosalud": "coosalud_homologacion.xlsx"
    }
    
    # Columnas requeridas por EPS (Coosalud solo tiene 2 columnas)
    EPS_COLUMNAS = {
        "mutualser": ['Código Servicio de la ERP', 'Código producto en DGH', 'COD_SERV_FACT'],
        "coosalud": ['Código Servicio de la ERP', 'Código producto en DGH']
    }
    
    # Columnas por defecto (para compatibilidad)
    COLUMNAS = ['Código Servicio de la ERP', 'Código producto en DGH', 'COD_SERV_FACT']
    
    # Cache class-level para compartir entre instancias
    _file_cache: Dict[str, Dict[str, Any]] = {}
    _search_cache: Dict[str, Dict[str, pd.DataFrame]] = {}
    
    def __init__(self, eps: Optional[str] = None):
        """
        Inicializa el servicio de homologación con sistema de caché
        
        Args:
            eps: Nombre de la EPS (mutualser, coosalud, etc.)
        """
        self.eps = eps
        self.homologacion_path: Optional[str] = None
        self.df: Optional[pd.DataFrame] = None
        self.columnas_actuales: list = self.COLUMNAS  # Columnas según EPS
        self._file_hash: Optional[str] = None  # Hash para detectar cambios
        
        if eps:
            self._set_eps(eps)
    
    def _get_file_hash(self, file_path: str) -> str:
        """Calcula hash MD5 de un archivo para detectar cambios"""
        if not os.path.exists(file_path):
            return ""
        
        with open(file_path, 'rb') as f:
            file_hash = hashlib.md5()
            for chunk in iter(lambda: f.read(4096), b""):
                file_hash.update(chunk)
        return file_hash.hexdigest()
    
    def _is_cache_valid(self, cache_key: str) -> bool:
        """Verifica si el caché es válido comparando hash del archivo"""
        if cache_key not in self._file_cache:
            return False
            
        cache_entry = self._file_cache[cache_key]
        current_hash = self._get_file_hash(cache_entry.get('file_path', ''))
        
        return current_hash == cache_entry.get('file_hash', '')
    
    def _update_file_cache(self, cache_key: str, df: pd.DataFrame, file_path: str):
        """Actualiza el caché de archivo con nuevo DataFrame y hash"""
        file_hash = self._get_file_hash(file_path)
        
        self._file_cache[cache_key] = {
            'df': df.copy(),
            'file_path': file_path,
            'file_hash': file_hash,
            'timestamp': datetime.now()
        }
        
        # Limpiar caché de búsqueda relacionado
        search_cache_key = f"{cache_key}_search"
        if search_cache_key in self._search_cache:
            del self._search_cache[search_cache_key]
    
    def _clear_search_cache(self, cache_key: str):
        """Limpia el caché de búsqueda para una EPS específica"""
        search_cache_key = f"{cache_key}_search"
        if search_cache_key in self._search_cache:
            del self._search_cache[search_cache_key]
    
    @classmethod
    def clear_all_cache(cls):
        """Limpia todos los cachés (útil para testing o reinicios)"""
        cls._file_cache.clear()
        cls._search_cache.clear()
        print("🗑️ Cache de homologación limpiado")
    
    @classmethod
    def get_eps_disponibles(cls):
        """
        Obtiene lista de EPS disponibles basado en archivos existentes
        
        Returns:
            Lista de diccionarios con info de cada EPS
        """
        eps_list = []
        try:
            if os.path.exists(cls.HOMOLOGACION_DIR):
                for eps_key, filename in cls.EPS_FILES.items():
                    filepath = os.path.join(cls.HOMOLOGACION_DIR, filename)
                    if os.path.exists(filepath):
                        # Obtener cantidad de registros
                        try:
                            df = pd.read_excel(filepath, nrows=0)
                            df_full = pd.read_excel(filepath)
                            count = len(df_full)
                        except:
                            count = 0
                        
                        eps_list.append({
                            "key": eps_key,
                            "name": eps_key.upper(),
                            "file": filename,
                            "path": filepath,
                            "count": count
                        })
        except Exception as e:
            print(f"Error listando EPS: {e}")
        
        return eps_list
    
    def _set_eps(self, eps: str):
        """Configura la EPS y carga el archivo correspondiente"""
        eps_lower = eps.lower()
        if eps_lower not in self.EPS_FILES:
            raise ValueError(f"EPS '{eps}' no soportada. Opciones: {list(self.EPS_FILES.keys())}")
        
        self.eps = eps_lower
        self.homologacion_path = os.path.join(self.HOMOLOGACION_DIR, self.EPS_FILES[eps_lower])
        # Configurar columnas según la EPS
        self.columnas_actuales = self.EPS_COLUMNAS.get(eps_lower, self.COLUMNAS)
        self._cargar()
    
    def cambiar_eps(self, eps: str):
        """
        Cambia a otra EPS
        
        Args:
            eps: Nombre de la EPS
        """
        self._set_eps(eps)
    
    def _cargar(self):
        """Carga el archivo de homologación usando caché para mejor rendimiento"""
        if not self.homologacion_path:
            self.df = pd.DataFrame(columns=self.columnas_actuales)
            return True
            
        cache_key = f"{self.eps}_homologacion"
        
        try:
            # Verificar si tenemos caché válido
            if self._is_cache_valid(cache_key):
                self.df = self._file_cache[cache_key]['df'].copy()
                self._file_hash = self._file_cache[cache_key]['file_hash']
                eps_name = self.eps.upper() if self.eps else "DESCONOCIDA"
                print(f"⚡ Homologación {eps_name} cargada desde caché: {len(self.df)} registros") # type: ignore
                return True
            
            # Cargar desde archivo si no hay caché válido
            if os.path.exists(self.homologacion_path):
                print(f"📁 Cargando homologación {self.eps} desde archivo...")
                self.df = pd.read_excel(self.homologacion_path)
                
                # Limpiar columnas
                self.df.columns = self.df.columns.str.strip()
                
                # Mantener solo columnas relevantes para esta EPS
                cols_existentes = [c for c in self.columnas_actuales if c in self.df.columns]
                if cols_existentes:
                    self.df = self.df[cols_existentes].copy()
                
                # Actualizar caché
                self._update_file_cache(cache_key, self.df, self.homologacion_path)
                self._file_hash = self._file_cache[cache_key]['file_hash']
                
                eps_name = self.eps.upper() if self.eps else "DESCONOCIDA"
                print(f"✅ Homologación {eps_name} cargada: {len(self.df)} registros (guardado en caché)")
            else:
                # Crear DataFrame vacío con las columnas de esta EPS
                self.df = pd.DataFrame(columns=self.columnas_actuales)
                print(f"⚠️ Archivo de homologación {self.eps or 'desconocida'} no encontrado, creando nuevo")
                
            return True
            
        except Exception as e:
            print(f"❌ Error cargando homologación: {e}")
            self.df = pd.DataFrame(columns=self.columnas_actuales)
            return False
    
    def _guardar(self):
        """Guarda los cambios en el archivo e invalida caché"""
        if not self.homologacion_path:
            print("❌ No hay EPS seleccionada")
            return False
            
        try:
            # Crear backup antes de guardar
            if os.path.exists(self.homologacion_path):
                backup_dir = os.path.join(self.HOMOLOGACION_DIR, "backups")
                os.makedirs(backup_dir, exist_ok=True)
                backup_filename = f"{self.eps}_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
                backup_path = os.path.join(backup_dir, backup_filename)
                shutil.copy2(self.homologacion_path, backup_path)
                print(f"📋 Backup creado: {backup_filename}")
            
            # Guardar archivo
            if self.df is None:
                print("❌ No hay datos para guardar")
                return False
                
            self.df.to_excel(self.homologacion_path, index=False)
            
            # Actualizar caché con nueva versión
            cache_key = f"{self.eps}_homologacion"
            self._update_file_cache(cache_key, self.df, self.homologacion_path)
            self._file_hash = self._file_cache[cache_key]['file_hash']
            
            eps_name = self.eps.upper() if self.eps else "DESCONOCIDA"
            print(f"✅ Archivo {eps_name} guardado (caché actualizado)")
            return True
            
        except Exception as e:
            print(f"❌ Error guardando: {e}")
            return False
    
    # ==================== CRUD ====================
    
    def listar(self, filtro=None, limite=100):
        """
        Lista códigos de homologación
        
        Args:
            filtro: Texto para filtrar (busca en todas las columnas)
            limite: Máximo de registros a retornar
            
        Returns:
            DataFrame con los registros
        """
        if self.df is None or self.df.empty:
            return pd.DataFrame(columns=self.columnas_actuales)
        
        df_resultado = self.df.copy()
        
        if filtro:
            filtro = str(filtro).lower()
            mask = df_resultado.apply(
                lambda row: any(filtro in str(v).lower() for v in row), axis=1
            )
            df_resultado = df_resultado[mask]
        
        return df_resultado.head(limite)
    
    def buscar_por_codigo_erp(self, codigo_erp):
        """
        Busca un código por el Código Servicio de la ERP (con caché optimizado)
        
        Args:
            codigo_erp: Código a buscar
            
        Returns:
            Serie con el registro encontrado o None
        """
        if self.df is None or self.df.empty:
            return None
        
        cache_key = f"{self.eps}_search"
        codigo_str = str(codigo_erp).strip()
        
        # Verificar caché de búsqueda
        if cache_key in self._search_cache:
            search_cache = self._search_cache[cache_key]
            if codigo_str in search_cache:
                cached_result = search_cache[codigo_str]
                if not cached_result.empty:
                    return cached_result.iloc[0]
                return None
        else:
            # Inicializar caché de búsqueda para esta EPS
            self._search_cache[cache_key] = {}
        
        # Búsqueda en DataFrame
        mask = self.df['Código Servicio de la ERP'].astype(str).str.strip() == codigo_str
        resultado = self.df[mask]
        
        # Guardar en caché de búsqueda
        self._search_cache[cache_key][codigo_str] = resultado.copy()
        
        return resultado.iloc[0] if not resultado.empty else None
    
    def buscar_por_codigo_erp_lote(self, codigos_erp: list) -> Dict[str, Any]:
        """
        Busca múltiples códigos ERP de forma optimizada usando caché
        
        Args:
            codigos_erp: Lista de códigos a buscar
            
        Returns:
            Diccionario con códigos como claves y resultados como valores
        """
        if self.df is None or self.df.empty:
            return {}
        
        cache_key = f"{self.eps}_search"
        resultados = {}
        codigos_a_buscar = []
        
        # Verificar caché primero
        if cache_key in self._search_cache:
            search_cache = self._search_cache[cache_key]
            for codigo in codigos_erp:
                codigo_str = str(codigo).strip()
                if codigo_str in search_cache:
                    cached_result = search_cache[codigo_str]
                    resultados[codigo_str] = cached_result.iloc[0] if not cached_result.empty else None
                else:
                    codigos_a_buscar.append(codigo_str)
        else:
            # Inicializar caché
            self._search_cache[cache_key] = {}
            codigos_a_buscar = [str(c).strip() for c in codigos_erp]
        
        # Buscar códigos no cacheados
        if codigos_a_buscar:
            df_codigos = self.df['Código Servicio de la ERP'].astype(str).str.strip()
            for codigo_str in codigos_a_buscar:
                mask = df_codigos == codigo_str
                resultado = self.df[mask]
                
                # Guardar en caché
                self._search_cache[cache_key][codigo_str] = resultado.copy()
                resultados[codigo_str] = resultado.iloc[0] if not resultado.empty else None
        
        return resultados
        
        if not resultado.empty:
            return resultado.iloc[0]
        return None
    
    def agregar(self, codigo_erp, codigo_dgh, cod_serv_fact=None):
        """
        Agrega un nuevo código de homologación
        
        Args:
            codigo_erp: Código Servicio de la ERP (del archivo de glosa)
            codigo_dgh: Código producto en DGH (código homologado)
            cod_serv_fact: COD_SERV_FACT (opcional, solo para Mutualser)
            
        Returns:
            True si se agregó correctamente
        """
        try:
            # Validar que no exista
            if self.buscar_por_codigo_erp(codigo_erp) is not None:
                print(f"⚠️ El código {codigo_erp} ya existe")
                return False
            
            # Crear registro según columnas de la EPS
            nuevo_registro = {
                'Código Servicio de la ERP': str(codigo_erp).strip(),
                'Código producto en DGH': str(codigo_dgh).strip()
            }
            
            # Solo agregar COD_SERV_FACT si la EPS lo requiere (Mutualser)
            if 'COD_SERV_FACT' in self.columnas_actuales:
                if cod_serv_fact is None:
                    cod_serv_fact = codigo_dgh
                nuevo_registro['COD_SERV_FACT'] = str(cod_serv_fact).strip()
            
            nuevo = pd.DataFrame([nuevo_registro])
            
            self.df = pd.concat([self.df, nuevo], ignore_index=True)
            
            # Limpiar caché de búsqueda después de modificar datos
            self._clear_search_cache(f"{self.eps}_homologacion")
            
            if self._guardar():
                print(f"✅ Código agregado: {codigo_erp} → {codigo_dgh}")
                return True
            return False
            
        except Exception as e:
            print(f"❌ Error agregando código: {e}")
            return False
    
    def actualizar(self, codigo_erp, codigo_dgh=None, cod_serv_fact=None):
        """
        Actualiza un código existente
        
        Args:
            codigo_erp: Código a actualizar
            codigo_dgh: Nuevo código DGH (opcional)
            cod_serv_fact: Nuevo COD_SERV_FACT (opcional, solo para Mutualser)
            
        Returns:
            True si se actualizó correctamente
        """
        try:
            if self.df is None:
                print("❌ No hay datos cargados")
                return False
            
            codigo_str = str(codigo_erp).strip()
            mask = self.df['Código Servicio de la ERP'].astype(str).str.strip() == codigo_str
            
            if not mask.any():
                print(f"⚠️ Código {codigo_erp} no encontrado")
                return False
            
            if codigo_dgh:
                self.df.loc[mask, 'Código producto en DGH'] = str(codigo_dgh).strip()
            # Solo actualizar COD_SERV_FACT si la EPS lo tiene (Mutualser)
            if cod_serv_fact and 'COD_SERV_FACT' in self.columnas_actuales:
                self.df.loc[mask, 'COD_SERV_FACT'] = str(cod_serv_fact).strip()
            
            # Limpiar caché de búsqueda después de actualizar
            self._clear_search_cache(f"{self.eps}_homologacion")
            
            if self._guardar():
                print(f"✅ Código actualizado: {codigo_erp}")
                return True
            return False
            
        except Exception as e:
            print(f"❌ Error actualizando código: {e}")
            return False
    
    def eliminar(self, codigo_erp):
        """
        Elimina un código
        
        Args:
            codigo_erp: Código a eliminar
            
        Returns:
            True si se eliminó correctamente
        """
        try:
            if self.df is None:
                print("❌ No hay datos cargados")
                return False
            
            codigo_str = str(codigo_erp).strip()
            mask = self.df['Código Servicio de la ERP'].astype(str).str.strip() == codigo_str
            
            if not mask.any():
                print(f"⚠️ Código {codigo_erp} no encontrado")
                return False
            
            self.df = self.df[~mask].copy()
            
            # Limpiar caché de búsqueda después de eliminar
            self._clear_search_cache(f"{self.eps}_homologacion")
            
            if self._guardar():
                print(f"✅ Código eliminado: {codigo_erp}")
                return True
            return False
            
        except Exception as e:
            print(f"❌ Error eliminando código: {e}")
            return False
    
    def agregar_multiples(self, codigos):
        """
        Agrega múltiples códigos de una vez
        
        Args:
            codigos: Lista de tuplas (codigo_erp, codigo_dgh) o (codigo_erp, codigo_dgh, cod_serv_fact)
            
        Returns:
            Cantidad de códigos agregados exitosamente
        """
        agregados = 0
        for codigo in codigos:
            if len(codigo) == 2:
                codigo_erp, codigo_dgh = codigo
                cod_serv_fact = codigo_dgh
            else:
                codigo_erp, codigo_dgh, cod_serv_fact = codigo
            
            # Validar que no exista
            if self.buscar_por_codigo_erp(codigo_erp) is None:
                # Crear registro según columnas de la EPS
                nuevo_registro = {
                    'Código Servicio de la ERP': str(codigo_erp).strip(),
                    'Código producto en DGH': str(codigo_dgh).strip()
                }
                # Solo agregar COD_SERV_FACT si la EPS lo requiere
                if 'COD_SERV_FACT' in self.columnas_actuales:
                    nuevo_registro['COD_SERV_FACT'] = str(cod_serv_fact).strip()
                
                nuevo = pd.DataFrame([nuevo_registro])
                self.df = pd.concat([self.df, nuevo], ignore_index=True)
                agregados += 1
        
        if agregados > 0 and self._guardar():
            print(f"✅ {agregados} códigos agregados")
        
        return agregados
    
    def obtener_no_homologados(self, codigos_tecnologia):
        """
        Obtiene los códigos que no están en el archivo de homologación
        
        Args:
            codigos_tecnologia: Lista de códigos de tecnología
            
        Returns:
            Lista de códigos no homologados
        """
        if self.df is None or self.df.empty:
            return codigos_tecnologia
        
        codigos_existentes = set(
            self.df['Código Servicio de la ERP']
            .dropna().astype(str).str.strip().tolist()
        )
        
        no_homologados = []
        for codigo in codigos_tecnologia:
            codigo_str = str(codigo).strip()
            if codigo_str and codigo_str not in codigos_existentes:
                no_homologados.append(codigo_str)
        
        return list(set(no_homologados))  # Únicos
    
    def get_estadisticas(self):
        """
        Obtiene estadísticas del archivo de homologación
        
        Returns:
            Dict con estadísticas
        """
        if self.df is None or self.df.empty:
            return {'total': 0, 'con_dgh': 0, 'con_serv_fact': 0}
        
        stats = {
            'total': len(self.df),
            'con_dgh': self.df['Código producto en DGH'].notna().sum() if 'Código producto en DGH' in self.df.columns else 0
        }
        
        # Solo incluir con_serv_fact si la columna existe (Mutualser)
        if 'COD_SERV_FACT' in self.columnas_actuales and 'COD_SERV_FACT' in self.df.columns:
            stats['con_serv_fact'] = self.df['COD_SERV_FACT'].notna().sum()
        else:
            stats['con_serv_fact'] = 0
        
        return stats
    
    def exportar_no_homologados(self, codigos, output_path=None):
        """
        Exporta códigos no homologados a un Excel para revisión
        
        Args:
            codigos: Lista de códigos no homologados
            output_path: Ruta de salida (opcional)
            
        Returns:
            Ruta del archivo generado
        """
        if not codigos:
            print("No hay códigos para exportar")
            return None
        
        if output_path is None:
            eps_name = self.eps or "general"
            output_path = f"codigos_pendientes_homologar_{eps_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        
        # Crear DataFrame según columnas de la EPS
        export_data = {
            'Código Servicio de la ERP': codigos,
            'Código producto en DGH': ''
        }
        # Solo agregar COD_SERV_FACT si la EPS lo requiere
        if 'COD_SERV_FACT' in self.columnas_actuales:
            export_data['COD_SERV_FACT'] = ''
        
        df_export = pd.DataFrame(export_data)
        
        df_export.to_excel(output_path, index=False)
        print(f"✅ Exportado: {output_path} ({len(codigos)} códigos pendientes)")
        return output_path

    def verificar_carga_masiva(self, df_carga):
        """
        Verifica los códigos de una carga masiva antes de agregarlos
        
        Args:
            df_carga: DataFrame con columnas 'codigo_eps' y 'codigo_homologo'
            
        Returns:
            Dict con:
                - validos: Lista de tuplas (codigo_eps, codigo_homologo) válidas para agregar
                - duplicados_archivo: Lista de códigos que ya existen en el archivo
                - duplicados_carga: Lista de códigos duplicados dentro del archivo de carga
                - errores: Lista de errores encontrados
        """
        resultado = {
            'validos': [],
            'duplicados_archivo': [],
            'duplicados_carga': [],
            'errores': []
        }
        
        try:
            # Verificar columnas requeridas
            cols_lower = [c.lower().strip() for c in df_carga.columns]
            
            # Buscar columna de código EPS
            col_eps = None
            for i, col in enumerate(cols_lower):
                if 'codigo' in col and ('eps' in col or 'erp' in col or 'servicio' in col):
                    col_eps = df_carga.columns[i]
                    break
            if col_eps is None and len(df_carga.columns) >= 1:
                col_eps = df_carga.columns[0]
            
            # Buscar columna de código homólogo
            col_homologo = None
            for i, col in enumerate(cols_lower):
                if 'homologo' in col or 'dgh' in col or 'producto' in col:
                    col_homologo = df_carga.columns[i]
                    break
            if col_homologo is None and len(df_carga.columns) >= 2:
                col_homologo = df_carga.columns[1]
            
            if col_eps is None or col_homologo is None:
                resultado['errores'].append("No se encontraron las columnas requeridas (código EPS y código homólogo)")
                return resultado
            
            # Obtener códigos existentes en el archivo de homologación
            codigos_existentes = set()
            if self.df is not None and not self.df.empty:
                codigos_existentes = set(
                    self.df['Código Servicio de la ERP']
                    .dropna().astype(str).str.strip().tolist()
                )
            
            # Rastrear códigos en la carga para detectar duplicados internos
            codigos_en_carga = {}
            
            for idx, row in df_carga.iterrows():
                codigo_eps = str(row[col_eps]).strip() if pd.notna(row[col_eps]) else ''
                codigo_homologo = str(row[col_homologo]).strip() if pd.notna(row[col_homologo]) else ''
                
                # Validar que no estén vacíos
                if not codigo_eps or codigo_eps.lower() == 'nan':
                    resultado['errores'].append(f"Fila {idx + 2}: Código EPS vacío")
                    continue
                if not codigo_homologo or codigo_homologo.lower() == 'nan':
                    resultado['errores'].append(f"Fila {idx + 2}: Código homólogo vacío para {codigo_eps}")
                    continue
                
                # Verificar si ya existe en el archivo
                if codigo_eps in codigos_existentes:
                    resultado['duplicados_archivo'].append({
                        'codigo': codigo_eps,
                        'homologo_nuevo': codigo_homologo,
                        'fila': idx + 2
                    })
                    continue
                
                # Verificar si está duplicado en la misma carga
                if codigo_eps in codigos_en_carga:
                    resultado['duplicados_carga'].append({
                        'codigo': codigo_eps,
                        'homologo': codigo_homologo,
                        'fila_original': codigos_en_carga[codigo_eps]['fila'],
                        'fila_duplicada': idx + 2
                    })
                    continue
                
                # Es válido
                codigos_en_carga[codigo_eps] = {'homologo': codigo_homologo, 'fila': idx + 2}
                resultado['validos'].append((codigo_eps, codigo_homologo))
            
        except Exception as e:
            resultado['errores'].append(f"Error procesando archivo: {str(e)}")
        
        return resultado
    
    def agregar_masivo(self, codigos_validos):
        """
        Agrega múltiples códigos validados de forma masiva
        
        Args:
            codigos_validos: Lista de tuplas (codigo_eps, codigo_homologo)
            
        Returns:
            Dict con cantidad agregada y errores
        """
        agregados = 0
        errores = []
        
        try:
            nuevos_registros = []
            for codigo_eps, codigo_homologo in codigos_validos:
                # Crear registro según columnas de la EPS
                nuevo_registro = {
                    'Código Servicio de la ERP': str(codigo_eps).strip(),
                    'Código producto en DGH': str(codigo_homologo).strip()
                }
                # Solo agregar COD_SERV_FACT si la EPS lo requiere (Mutualser)
                if 'COD_SERV_FACT' in self.columnas_actuales:
                    nuevo_registro['COD_SERV_FACT'] = str(codigo_homologo).strip()  # Mismo valor por defecto
                
                nuevos_registros.append(nuevo_registro)
            
            if nuevos_registros:
                df_nuevos = pd.DataFrame(nuevos_registros)
                self.df = pd.concat([self.df, df_nuevos], ignore_index=True)
                
                if self._guardar():
                    agregados = len(nuevos_registros)
                    print(f"✅ {agregados} códigos agregados masivamente")
                else:
                    errores.append("Error al guardar el archivo")
        
        except Exception as e:
            errores.append(f"Error en carga masiva: {str(e)}")
        
        return {'agregados': agregados, 'errores': errores}
