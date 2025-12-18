"""
Servicio de gestión de adjuntos
Maneja la descarga, almacenamiento y filtrado de archivos adjuntos
"""
import os
import sys
import tempfile


class AttachmentService:
    """Servicio para manejar adjuntos de correos"""
    
    def __init__(self, base_dir=None):
        """
        Args:
            base_dir: Directorio base para guardar adjuntos. 
                     Si es None, usa carpeta temporal del sistema (mismo que imap_client)
        """
        # Inicializar las listas PRIMERO
        self.downloaded_files = []  # Todos los archivos en el directorio
        self.session_files = []     # Solo archivos descargados en esta búsqueda
        
        if base_dir is None:
            # IMPORTANTE: Usar MISMO directorio que imap_client (tempfile.gettempdir())
            # para que los archivos descargados se detecten correctamente
            self.base_dir = os.path.join(
                tempfile.gettempdir(), 
                "glosaap_attachments"
            )
        else:
            # Convertir a ruta absoluta si es relativa
            if not os.path.isabs(base_dir):
                # Obtener el directorio raíz del proyecto (2 niveles arriba de service/)
                project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
                self.base_dir = os.path.join(project_root, base_dir)
            else:
                self.base_dir = base_dir
        
        self._ensure_directory()
    
    def _ensure_directory(self):
        """Crea el directorio si no existe y carga archivos existentes"""
        os.makedirs(self.base_dir, exist_ok=True)
        print(f"[ATTACH] Directorio de trabajo: {self.base_dir}")
        
        # Cargar archivos existentes en el directorio
        self._scan_directory()
    
    def _scan_directory(self):
        """Escanea el directorio y carga todos los archivos existentes"""
        if not os.path.exists(self.base_dir):
            print(f"[ATTACH] Directorio no existe todavía: {self.base_dir}")
            return
        
        # Limpiar lista antes de escanear
        self.downloaded_files = []
        
        # Listar TODOS los archivos en el directorio
        all_files_in_dir = []
        for root, dirs, files in os.walk(self.base_dir):
            for file in files:
                file_path = os.path.join(root, file)
                all_files_in_dir.append(file_path)
                if file_path not in self.downloaded_files:
                    self.downloaded_files.append(file_path)
        
        print(f"[ATTACH] Total archivos en directorio: {len(all_files_in_dir)}")
        print(f"[ATTACH] Archivos cargados en lista: {len(self.downloaded_files)}")
        
        excel_count = len([f for f in self.downloaded_files if f.endswith(('.xlsx', '.xls', '.xlsm', '.xlsb', '.csv'))])
        print(f"[ATTACH] Archivos Excel detectados: {excel_count}")
        
        # Mostrar primeros 5 archivos para debug
        if self.downloaded_files:
            print(f"[ATTACH] Primeros archivos:")
            for i, f in enumerate(self.downloaded_files[:5]):
                print(f"  {i+1}. {os.path.basename(f)}")
        else:
            print(f"[ATTACH] ⚠️ No se encontraron archivos en: {self.base_dir}")
    
    def add_files(self, file_paths):
        """Agrega archivos a la lista de descargados Y de sesión"""
        for path in file_paths:
            if os.path.exists(path):
                if path not in self.downloaded_files:
                    self.downloaded_files.append(path)
                # Siempre agregar a session_files (archivos de esta búsqueda)
                if path not in self.session_files:
                    self.session_files.append(path)
        print(f"[ATTACH] Archivos sesión: {len(self.session_files)} | Total dir: {len(self.downloaded_files)}")
    
    def rescan(self):
        """Re-escanea el directorio para actualizar la lista de archivos"""
        print(f"[ATTACH] Re-escaneando directorio...")
        self._scan_directory()
        return len(self.downloaded_files)
    
    def clear_all(self):
        """Elimina todos los archivos del directorio temporal"""
        import shutil
        
        print(f"[CLEANUP] clear_all() llamado - base_dir: {self.base_dir}")
        
        if os.path.exists(self.base_dir):
            files_in_dir = [f for f in os.listdir(self.base_dir) if os.path.isfile(os.path.join(self.base_dir, f))]
            file_count = len(files_in_dir)
            print(f"[CLEANUP] Eliminando {file_count} archivo(s) del directorio...")
            
            deleted = 0
            errors = 0
            # Eliminar todos los archivos
            for filename in files_in_dir:
                file_path = os.path.join(self.base_dir, filename)
                try:
                    os.unlink(file_path)
                    deleted += 1
                except Exception as e:
                    errors += 1
                    print(f"[CLEANUP] Error al eliminar {filename}: {e}")
            
            print(f"[CLEANUP] ✅ Eliminados: {deleted}, Errores: {errors}")
        else:
            print(f"[CLEANUP] Directorio no existe: {self.base_dir}")
        
        # Limpiar listas en memoria
        self.downloaded_files = []
        self.session_files = []
        print(f"[CLEANUP] Listas en memoria limpiadas")
    
    def clear_session(self):
        """Limpia solo la lista de archivos de sesión (no elimina archivos físicos)"""
        print(f"[CLEANUP] Limpiando archivos de sesión: {len(self.session_files)} archivos")
        self.session_files = []
    
    def get_session_files(self):
        """Retorna solo los archivos descargados en esta sesión de búsqueda"""
        return self.session_files
    
    def get_session_excel_files(self, exclude_devoluciones=True):
        """
        Filtra y retorna archivos Excel/CSV SOLO de la sesión actual
        
        Args:
            exclude_devoluciones: Si es True, excluye archivos de devolución
        """
        excel_files = [
            f for f in self.session_files 
            if f.endswith(('.xlsx', '.xls', '.xlsm', '.xlsb', '.csv'))
        ]
        
        print(f"[SESSION] Archivos Excel en sesión: {len(excel_files)}")
        
        if not exclude_devoluciones:
            return excel_files
        
        # Filtrar devoluciones
        filtered = []
        archivos_devolucion = 0
        
        for f in excel_files:
            filename = os.path.basename(f).lower()
            if 'devolucion' in filename or 'devolución' in filename:
                archivos_devolucion += 1
                continue
            filtered.append(f)
        
        if archivos_devolucion > 0:
            print(f"[SESSION] Devoluciones excluidas: {archivos_devolucion}")
        print(f"[SESSION] Archivos a procesar: {len(filtered)}")
        
        return filtered
    
    def get_all_files(self):
        """Retorna todos los archivos descargados"""
        return self.downloaded_files
    
    def get_excel_files(self, exclude_devoluciones=True):
        """
        Filtra y retorna archivos Excel y CSV
        
        Args:
            exclude_devoluciones: Si es True, excluye archivos de devolución
        """
        # Re-escanear directorio para asegurar lista actualizada
        self.rescan()
        
        excel_files = [
            f for f in self.downloaded_files 
            if f.endswith(('.xlsx', '.xls', '.xlsm', '.xlsb', '.csv'))
        ]
        
        total_inicial = len(excel_files)
        
        # Filtrar archivos de devolución si se solicita
        if exclude_devoluciones:
            filtered = []
            archivos_devolucion = 0
            archivos_fc_asociados = 0
            
            for f in excel_files:
                filename = os.path.basename(f).lower()
                
                # Excluir archivos con "devolucion" en el nombre
                if 'devolucion' in filename or 'devolución' in filename:
                    archivos_devolucion += 1
                    continue
                
                # Excluir archivos FC{numero}.xlsx si existe un DEVOLUCION correspondiente
                # Solo formato FC seguido de numeros
                if filename.startswith('fc') and filename.replace('fc', '').replace('.xlsx', '').replace('.xls', '').isdigit():
                    # Buscar si existe un archivo DEVOLUCION con el mismo numero
                    tiene_devolucion = any(
                        filename in os.path.basename(other).lower() 
                        for other in excel_files 
                        if 'devolucion' in os.path.basename(other).lower()
                    )
                    if tiene_devolucion:
                        archivos_fc_asociados += 1
                        continue
                
                filtered.append(f)
            
            print(f"[FILTER] Total archivos Excel: {total_inicial}")
            print(f"[FILTER] Archivos DEVOLUCION excluidos: {archivos_devolucion}")
            print(f"[FILTER] Archivos FC asociados excluidos: {archivos_fc_asociados}")
            print(f"[FILTER] Archivos a procesar: {len(filtered)}")
            
            return filtered
            
        return excel_files
    
    def get_word_files(self):
        """Filtra y retorna archivos Word"""
        return [
            f for f in self.downloaded_files 
            if f.endswith(('.doc', '.docx', '.docm'))
        ]
    
    def get_pdf_files(self):
        """Filtra y retorna archivos PDF"""
        return [
            f for f in self.downloaded_files 
            if f.endswith('.pdf')
        ]
    
    def get_document_files(self):
        """Retorna todos los archivos de documentos (Excel, Word, PDF)"""
        return [
            f for f in self.downloaded_files 
            if f.endswith(('.xlsx', '.xls', '.xlsm', '.xlsb', '.csv', 
                          '.doc', '.docx', '.docm', '.pdf'))
        ]
    
    def get_file_info(self, file_path):
        """Obtiene información de un archivo"""
        if not os.path.exists(file_path):
            return None
            
        return {
            "name": os.path.basename(file_path),
            "path": file_path,
            "size": os.path.getsize(file_path),
            "extension": os.path.splitext(file_path)[1],
            "is_excel": file_path.endswith(('.xlsx', '.xls', '.csv'))
        }
    
    def clear_all(self):
        """Limpia la lista de archivos descargados (no borra archivos físicos)"""
        self.downloaded_files = []
    
    def clear_directory(self):
        """Elimina todos los archivos del directorio físicamente"""
        import shutil
        if os.path.exists(self.base_dir):
            for root, dirs, files in os.walk(self.base_dir):
                for file in files:
                    try:
                        os.remove(os.path.join(root, file))
                    except Exception as e:
                        print(f"Error eliminando {file}: {e}")
        self.downloaded_files = []
        print(f"DEBUG: Directorio limpiado: {self.base_dir}")
    
    def get_summary(self):
        """Retorna un resumen de archivos descargados"""
        excel_files = self.get_excel_files()
        word_files = self.get_word_files()
        pdf_files = self.get_pdf_files()
        total_size = sum(
            os.path.getsize(f) for f in self.downloaded_files 
            if os.path.exists(f)
        )
        
        return {
            "total_files": len(self.downloaded_files),
            "excel_files": len(excel_files),
            "word_files": len(word_files),
            "pdf_files": len(pdf_files),
            "total_size": total_size,
            "base_dir": self.base_dir
        }
