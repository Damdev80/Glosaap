"""
Servicio de gestión de emails
Orquesta las operaciones entre IMAP y adjuntos
"""
import os
from app.core.imap_client import ImapClient
from app.service.attachment_service import AttachmentService
from app.core.mutualser_processor import MutualserProcessor


class EmailService:
    """Servicio principal para gestionar correos electrónicos"""
    
    # Rutas de red para salida de archivos
    MUTUALSER_OUTPUT_RED = r"\\MINERVA\Cartera\GLOSAAP\REPOSITORIO DE RESULTADOS\MUTUALSER"
    
    def __init__(self):
        self.imap_client = None
        # AttachmentService usa directorio temporal del sistema (donde ya tienes archivos)
        self.attachment_service = AttachmentService()  # Sin base_dir = usa temporal
        self.messages = []
        
        # Procesadores por EPS - usar ruta de red MINERVA
        mutualser_output = self._get_output_path(self.MUTUALSER_OUTPUT_RED, "outputs/mutualser")
        self.mutualser_processor = MutualserProcessor(output_dir=mutualser_output)
        print(f"📁 MUTUALSER guardará en: {mutualser_output}")
    
    def _get_output_path(self, network_path, fallback_path):
        """
        Intenta usar ruta de red, si no está disponible usa fallback local
        """
        try:
            # Verificar si la ruta de red existe o se puede crear
            if os.path.exists(network_path):
                return network_path
            
            # Intentar crear la ruta de red
            os.makedirs(network_path, exist_ok=True)
            if os.path.exists(network_path):
                print(f"✅ Ruta de red accesible: {network_path}")
                return network_path
        except Exception as e:
            print(f"⚠️ Red no accesible ({e}), usando local: {fallback_path}")
        
        # Fallback a ruta local
        os.makedirs(fallback_path, exist_ok=True)
        return fallback_path
    
    def connect(self, email, password, server="imap.gmail.com", port=993):
        """Conecta al servidor IMAP"""
        self.imap_client = ImapClient()
        self.imap_client.connect(email, password, server, port)
        return True
    

    def search_messages(self, keyword, limit=1000, timeout=30, on_found=None, date_from=None, date_to=None):
        """
        Busca mensajes por palabra clave en el asunto
        
        Args:
            keyword: Palabra a buscar
            limit: Límite de mensajes
            timeout: Tiempo máximo de búsqueda
            on_found: Callback cuando se encuentra un mensaje
            date_from: Fecha inicio del rango (datetime o string 'YYYY-MM-DD')
            date_to: Fecha fin del rango (datetime o string 'YYYY-MM-DD')
            
        Returns:
            Lista de mensajes encontrados
        """
        if not self.imap_client:
            raise Exception("No hay conexión IMAP establecida")
        
        print(f"[SEARCH] Buscando: keyword='{keyword}', limit={limit}, timeout={timeout}")
        print(f"[SEARCH] Rango: {date_from} hasta {date_to}")
        
        self.messages = self.imap_client.search_by_subject(
            keyword, 
            limit=limit, 
            timeout=timeout, 
            on_found=on_found,
            date_from=date_from,
            date_to=date_to
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
    
    def get_excel_files(self, exclude_devoluciones=True, session_only=True):
        """
        Obtiene archivos Excel/CSV descargados
        
        Args:
            exclude_devoluciones: Excluir archivos de devolución
            session_only: Si True, solo retorna archivos de la sesión actual
        """
        if session_only:
            return self.attachment_service.get_session_excel_files(exclude_devoluciones=exclude_devoluciones)
        return self.attachment_service.get_excel_files(exclude_devoluciones=exclude_devoluciones)
    
    def clear_session(self):
        """Limpia los archivos de la sesión actual (para nueva búsqueda)"""
        return self.attachment_service.clear_session()
    
    def clear_attachments(self):
        """Limpia todos los archivos descargados del directorio temporal"""
        return self.attachment_service.clear_all()
    
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
        if archivos is None:
            archivos = self.get_excel_files()

        if not archivos:
            return {
                'success': False,
                'message': 'No hay archivos para procesar'
            }
        # Procesar archivos
        #     
    


# Procesar adjunto de acuerdo a la EPS