"""
Servicio de gestión de emails
Orquesta las operaciones entre IMAP y adjuntos
"""
from core.imap_client import ImapClient
from service.attachment_service import AttachmentService
from core.eps_processors import MutualserProcessor, CosaludProcessor


class EmailService:
    """Servicio principal para gestionar correos electrónicos"""
    
    def __init__(self):
        self.imap_client = None
        self.attachment_service = AttachmentService()
        self.messages = []
        # Procesadores por EPS
        self.mutualser_processor = MutualserProcessor()
        self.cosalud_processor = CosaludProcessor()
    
    def connect(self, email, password, server="imap.gmail.com", port=993):
        """Conecta al servidor IMAP"""
        self.imap_client = ImapClient()
        self.imap_client.connect(email, password, server, port)
        return True
    

    def search_messages(self, keyword, limit=100, timeout=15, on_found=None):
        """
        Busca mensajes por palabra clave en el asunto
        
        Args:
            keyword: Palabra a buscar
            limit: Límite de mensajes
            timeout: Tiempo máximo de búsqueda
            on_found: Callback cuando se encuentra un mensaje
            
        Returns:
            Lista de mensajes encontrados
        """
        if not self.imap_client:
            raise Exception("No hay conexión IMAP establecida")
        
        self.messages = self.imap_client.search_by_subject(
            keyword, 
            limit=limit, 
            timeout=timeout, 
            on_found=on_found
        )
        return self.messages
    
    def download_message_attachments(self, message_id):
        """
        Descarga adjuntos de un mensaje específico
        
        Args:
            message_id: ID del mensaje
            
        Returns:
            Lista de rutas de archivos descargados
        """
        if not self.imap_client:
            raise Exception("No hay conexión IMAP establecida")
        
        saved_files = self.imap_client.download_attachments(
            message_id,
            dest_dir=self.attachment_service.base_dir
        )
        
        if saved_files:
            self.attachment_service.add_files(saved_files)
        
        return saved_files
    
    def download_all_attachments(self, messages=None, on_progress=None):
        """
        Descarga adjuntos de múltiples mensajes
        
        Args:
            messages: Lista de mensajes (usa self.messages si es None)
            on_progress: Callback(idx, total, msg, files) llamado después de cada descarga
            
        Returns:
            Dict con estadísticas de descarga
        """
        msgs = messages or self.messages
        stats = {
            "total_messages": len(msgs),
            "messages_with_attachments": 0,
            "total_files": 0,
            "errors": 0
        }
        
        for idx, msg in enumerate(msgs):
            try:
                files = self.download_message_attachments(msg["id"])
                
                if files:
                    stats["messages_with_attachments"] += 1
                    stats["total_files"] += len(files)
                
                if on_progress:
                    on_progress(idx, len(msgs), msg, files)
                    
            except Exception as e:
                stats["errors"] += 1
                print(f"Error descargando adjuntos del mensaje {msg.get('id')}: {e}")
        
        return stats
    
    def get_attachment_summary(self):
        """Obtiene resumen de adjuntos descargados"""
        return self.attachment_service.get_summary()
    
    def get_excel_files(self):
        """Obtiene solo archivos Excel/CSV descargados"""
        return self.attachment_service.get_excel_files()
    
    def disconnect(self):
        """Cierra la conexión IMAP"""
        if self.imap_client:
            self.imap_client.logout()
            self.imap_client = None

    # Métodos específicos para procesamiento de EPS
    
    def procesar_mutualser(self, archivos=None):
        """
        Procesa archivos de MUTUALSER y genera Excel consolidado
        
        Args:
            archivos: Lista de rutas de archivos (usa archivos descargados si es None)
            
        Returns:
            Dict con rutas de archivos generados y resumen
        """
        # Si no se especifican archivos, usar los Excel descargados
        if archivos is None:
            archivos = self.get_excel_files()
        
        if not archivos:
            return {
                'success': False,
                'message': 'No hay archivos para procesar'
            }
        
        # Procesar archivos
        df = self.mutualser_processor.procesar_multiples_archivos(archivos)
        
        if df is None or df.empty:
            return {
                'success': False,
                'message': 'No se pudo procesar ningún archivo'
            }
        
        # Exportar consolidado y generar archivo de objeciones
        resultado = self.mutualser_processor.exportar_consolidado()
        
        if resultado:
            output_path, objeciones_path = resultado
            resumen = self.mutualser_processor.get_resumen()
            return {
                'success': True,
                'output_file': output_path,
                'objeciones_file': objeciones_path,
                'resumen': resumen
            }
        else:
            return {
                'success': False,
                'message': 'Error al exportar archivos'
            }
    
    def procesar_cosalud(self, archivos=None):
        """
        Procesa archivos de COSALUD y genera Excel consolidado
        
        Args:
            archivos: Lista de rutas de archivos (usa archivos descargados si es None)
            
        Returns:
            Dict con ruta del archivo generado y resumen
        """
        # TODO: Implementar cuando se defina estructura de COSALUD
        return {
            'success': False,
            'message': 'Procesador de COSALUD aún no implementado'
        }


# Procesar adjunto de acuerdo a la EPS