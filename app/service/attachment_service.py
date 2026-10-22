"""
Servicio de gestión de adjuntos
Maneja la descarga, almacenamiento y filtrado de archivos adjuntos
"""
import os
import sys
import tempfile

from app.config.settings import logger


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
        self.file_metadata = {}     # Metadatos de archivos: {ruta_archivo: {"email_date": fecha, "message_id": id, ...}}
        
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
        logger.debug("[ATTACH] Directorio de trabajo: %s", self.base_dir)
        
        # Cargar archivos existentes en el directorio
        self._scan_directory()
    
    def _scan_directory(self):
        """Escanea el directorio y carga todos los archivos existentes"""
        if not os.path.exists(self.base_dir):
            logger.debug("[ATTACH] Directorio no existe todavia: %s", self.base_dir)
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
        
        logger.debug("[ATTACH] Total archivos en directorio: %s", len(all_files_in_dir))
        logger.debug("[ATTACH] Archivos cargados en lista: %s", len(self.downloaded_files))
        
        excel_count = len([f for f in self.downloaded_files if f.endswith(('.xlsx', '.xls', '.xlsm', '.xlsb', '.csv'))])
        logger.debug("[ATTACH] Archivos Excel detectados: %s", excel_count)

        # Mostrar primeros 5 archivos para debug
        if self.downloaded_files:
            logger.debug("[ATTACH] Primeros archivos:")
            for i, f in enumerate(self.downloaded_files[:5]):
                logger.debug("  %s. %s", i + 1, os.path.basename(f))
        else:
            logger.debug("[ATTACH] No se encontraron archivos en: %s", self.base_dir)
    
    def add_files(self, file_paths, metadata=None):
        """Agrega archivos a la lista de descargados Y de sesión
        
        Args:
            file_paths: Lista de rutas de archivos
            metadata: Dict con metadatos por archivo {path: {"email_date": fecha, ...}}
                     O dict con metadatos para todos los archivos {"email_date": fecha, ...}
        """
        for path in file_paths:
            if os.path.exists(path):
                if path not in self.downloaded_files:
                    self.downloaded_files.append(path)
                # Siempre agregar a session_files (archivos de esta búsqueda)
                if path not in self.session_files:
                    self.session_files.append(path)
                # Almacenar metadatos si se proporcionan
                if metadata:
                    # Si metadata tiene el path como clave, usar esos metadatos específicos
                    if path in metadata:
                        self.file_metadata[path] = metadata[path].copy()
                    # Si no, asumir que metadata es para aplicar a todos
                    else:
                        self.file_metadata[path] = metadata.copy()
        logger.debug(
            "[ATTACH] Archivos sesion: %s | Total dir: %s",
            len(self.session_files),
            len(self.downloaded_files),
        )
    
    def rescan(self):
        """Re-escanea el directorio para actualizar la lista de archivos"""
        logger.debug("[ATTACH] Re-escaneando directorio...")
        self._scan_directory()
        return len(self.downloaded_files)
    
    def clear_all(self, delete_files: bool = False):
        """Limpia el estado en memoria y, opcionalmente, los archivos físicos.

        Semántica explícita:
        - Por defecto (``delete_files=False``) es NO destructiva: solo vacía
          ``downloaded_files``, ``session_files`` y ``file_metadata``.
        - Con ``delete_files=True`` además borra recursivamente todos los
          archivos bajo ``base_dir`` (sin eliminar el propio directorio).

        Args:
            delete_files: Si True, borra archivos físicos del disco.

        Returns:
            dict: ``{"deleted": int, "errors": int, "delete_files": bool}``.
        """
        deleted = 0
        errors = 0

        if delete_files:
            logger.info("[CLEANUP] clear_all(delete_files=True) - base_dir: %s", self.base_dir)
            if os.path.exists(self.base_dir):
                for root, _dirs, files in os.walk(self.base_dir):
                    for filename in files:
                        file_path = os.path.join(root, filename)
                        try:
                            os.remove(file_path)
                            deleted += 1
                        except Exception as e:
                            errors += 1
                            logger.warning("[CLEANUP] Error al eliminar %s: %s", file_path, e)
                logger.info("[CLEANUP] Eliminados: %s, Errores: %s", deleted, errors)
            else:
                logger.info("[CLEANUP] Directorio no existe: %s", self.base_dir)
        else:
            logger.info(
                "[CLEANUP] clear_all(delete_files=False) - solo memoria "
                "(session=%s, total=%s)",
                len(self.session_files),
                len(self.downloaded_files),
            )

        # Limpiar estado en memoria en ambos casos.
        self.downloaded_files = []
        self.session_files = []
        self.file_metadata = {}
        logger.info("[CLEANUP] Listas en memoria limpiadas")

        return {"deleted": deleted, "errors": errors, "delete_files": delete_files}

    def clear_session(self):
        """Limpia solo la lista de archivos de sesión (no elimina archivos físicos)."""
        logger.info("[CLEANUP] Limpiando archivos de sesión: %s archivos", len(self.session_files))
        # Limpiar metadatos de archivos de sesión
        for file_path in self.session_files:
            if file_path in self.file_metadata:
                del self.file_metadata[file_path]
        self.session_files = []
    
    def get_session_files(self):
        """Retorna solo los archivos descargados en esta sesión de búsqueda"""
        return self.session_files
    
    def get_file_metadata(self, file_path):
        """Obtiene metadatos de un archivo específico
        
        Args:
            file_path: Ruta del archivo
            
        Returns:
            dict: Metadatos del archivo o None si no existen
        """
        return self.file_metadata.get(file_path)
    
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
        
        logger.debug("[SESSION] Archivos Excel en sesion: %s", len(excel_files))
        
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
            logger.debug("[SESSION] Devoluciones excluidas: %s", archivos_devolucion)
        logger.debug("[SESSION] Archivos a procesar: %s", len(filtered))
        
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
            
            logger.debug("[FILTER] Total archivos Excel: %s", total_inicial)
            logger.debug("[FILTER] Archivos DEVOLUCION excluidos: %s", archivos_devolucion)
            logger.debug("[FILTER] Archivos FC asociados excluidos: %s", archivos_fc_asociados)
            logger.debug("[FILTER] Archivos a procesar: %s", len(filtered))
            
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
    
    def clear_directory(self):
        """Alias deprecado de :meth:`clear_all` con ``delete_files=True``.

        Se conserva por compatibilidad con callers antiguos. El código nuevo
        debe usar ``clear_all(delete_files=True)`` directamente.
        """
        logger.info("[CLEANUP] clear_directory() deprecado - delega a clear_all(delete_files=True)")
        return self.clear_all(delete_files=True)
    
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
