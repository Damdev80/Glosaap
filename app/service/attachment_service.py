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
        self.base_dir = base_dir or os.path.join(
            tempfile.gettempdir(), 
            "glosaap_attachments"
        )
        self._ensure_directory()
        self.downloaded_files = []
    
    def _ensure_directory(self):
        """Crea el directorio si no existe"""
        os.makedirs(self.base_dir, exist_ok=True)
    
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
        """Limpia la lista de archivos descargados"""
        self.downloaded_files = []
    
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
