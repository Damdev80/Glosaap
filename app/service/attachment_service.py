"""
Servicio de gestión de adjuntos
Maneja la descarga, almacenamiento y filtrado de archivos adjuntos
"""
import os
import tempfile


class AttachmentService:
    """Servicio para manejar adjuntos de correos"""
    
    def __init__(self, base_dir=None):
        """
        Args:
            base_dir: Directorio base para guardar adjuntos. 
                     Si es None, usa temporal del sistema
        """
        # Inicializar la lista PRIMERO
        self.downloaded_files = []
        
        if base_dir is None:
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
        print(f"DEBUG: AttachmentService base_dir = {self.base_dir}")
        
        # Cargar archivos existentes en el directorio
        self._scan_directory()
    
    def _scan_directory(self):
        """Escanea el directorio y carga todos los archivos existentes"""
        if not os.path.exists(self.base_dir):
            return
        
        for root, dirs, files in os.walk(self.base_dir):
            for file in files:
                file_path = os.path.join(root, file)
                if file_path not in self.downloaded_files:
                    self.downloaded_files.append(file_path)
        
        print(f"DEBUG: Archivos cargados del directorio: {len(self.downloaded_files)}")
        excel_count = len([f for f in self.downloaded_files if f.endswith(('.xlsx', '.xls', '.xlsm', '.xlsb', '.csv'))])
        print(f"DEBUG: De los cuales {excel_count} son Excel")
    
    def add_files(self, file_paths):
        """Agrega archivos a la lista de descargados"""
        for path in file_paths:
            if os.path.exists(path) and path not in self.downloaded_files:
                self.downloaded_files.append(path)
    
    def get_all_files(self):
        """Retorna todos los archivos descargados"""
        return self.downloaded_files
    
    def get_excel_files(self):
        """Filtra y retorna archivos Excel y CSV"""
        return [
            f for f in self.downloaded_files 
            if f.endswith(('.xlsx', '.xls', '.xlsm', '.xlsb', '.csv'))
        ]
    
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
