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
    

    def search_messages(self, keyword, limit=None, timeout=120, on_found=None, date_from=None, date_to=None):
        """
        Busca mensajes por palabra clave en el asunto con filtros opcionales.
        
        Args:
            keyword (str): Palabra clave a buscar en el asunto. Ej: "MUTUALSER", "Glosa"
            limit (int, optional): Límite máximo de mensajes a retornar. None = sin límite
            timeout (int): Tiempo máximo de búsqueda en segundos (default: 120)
            on_found (callable, optional): Función callback(message) ejecutada al encontrar cada mensaje
            date_from (datetime|str, optional): Fecha inicio del rango. Formato: datetime o 'YYYY-MM-DD'
            date_to (datetime|str, optional): Fecha fin del rango. Formato: datetime o 'YYYY-MM-DD'
            
        Returns:
            list: Lista de diccionarios con información de mensajes encontrados.
                  Cada mensaje contiene: {'id', 'subject', 'from', 'date', 'has_attachments'}
        
        Raises:
            Exception: Si no hay conexión IMAP establecida
            
        Examples:
            >>> # Búsqueda básica
            >>> messages = email_service.search_messages("MUTUALSER")
            >>> 
            >>> # Búsqueda con límite y callback
            >>> def on_message(msg):
            ...     print(f"Encontrado: {msg['subject']}")
            >>> messages = email_service.search_messages("Glosa", limit=10, on_found=on_message)
            >>> 
            >>> # Búsqueda con rango de fechas
            >>> from datetime import datetime, timedelta
            >>> yesterday = datetime.now() - timedelta(days=1)
            >>> messages = email_service.search_messages(
            ...     "MUTUALSER", 
            ...     date_from=yesterday,
            ...     date_to=datetime.now()
            ... )
            >>> 
            >>> # Búsqueda con fechas como strings
            >>> messages = email_service.search_messages(
            ...     "Respuesta Glosa",
            ...     date_from="2024-01-01",
            ...     date_to="2024-01-31"
            ... )
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
    
    def download_message_attachments(self, message_id, email_date=None):
        """
        Descarga todos los adjuntos de un mensaje específico al directorio temporal.
        
        Args:
            message_id (str): ID único del mensaje en el servidor IMAP
            email_date (str, optional): Fecha del correo en formato '%Y-%m-%d %H:%M:%S'
            
        Returns:
            list: Lista de rutas absolutas de archivos descargados exitosamente.
                  Retorna lista vacía si no hay adjuntos o fallan todas las descargas.
                  
        Raises:
            Exception: Si no hay conexión IMAP establecida
            
        Examples:
            >>> # Descargar adjuntos de un mensaje específico con fecha
            >>> message_id = "12345"
            >>> email_date = "2026-02-05 10:30:00"
            >>> files = email_service.download_message_attachments(message_id, email_date=email_date)
            >>> print(f"Descargados {len(files)} archivos:")
            >>> for file_path in files:
            ...     print(f"  - {os.path.basename(file_path)}")
            >>> 
            >>> # Verificar si se descargaron archivos
            >>> if files:
            ...     print(f"Primer archivo: {files[0]}")
            ...     print(f"Tamaño: {os.path.getsize(files[0])} bytes")
            ... else:
            ...     print("No se descargaron adjuntos")
        
        Note:
            - Los archivos se descargan al directorio temporal del AttachmentService
            - Los nombres de archivo duplicados se renombran automáticamente
            - Los archivos se agregan automáticamente al registro de la sesión actual
            - Si se proporciona email_date, se guarda en los metadatos de cada archivo
        """
        if not self.imap_client:
            raise Exception("No hay conexión IMAP establecida")
        
        saved_files = self.imap_client.download_attachments(
            message_id,
            dest_dir=self.attachment_service.base_dir
        )
        
        if saved_files:
            # Crear metadata con fecha del correo si está disponible
            metadata = {}
            if email_date:
                for file_path in saved_files:
                    metadata[file_path] = {
                        "email_date": email_date,
                        "message_id": message_id
                    }
            
            self.attachment_service.add_files(saved_files, metadata=metadata)
        
        return saved_files
    
    def download_all_attachments(self, messages=None, on_progress=None):
        """
        Descarga adjuntos de múltiples mensajes con seguimiento de progreso detallado.
        
        Args:
            messages (list, optional): Lista de mensajes a procesar. Si None, usa self.messages
                                     de la última búsqueda realizada
            on_progress (callable, optional): Función callback(idx, total, message, files)
                                            ejecutada después de procesar cada mensaje
                                            
        Returns:
            dict: Estadísticas detalladas de la descarga con las siguientes claves:
                - total_messages (int): Número total de mensajes procesados
                - messages_with_attachments (int): Mensajes que tenían adjuntos
                - total_files (int): Número total de archivos descargados
                - errors (int): Número de errores encontrados
                
        Raises:
            Exception: Si no hay conexión IMAP establecida
            
        Examples:
            >>> # Descarga básica sin callback
            >>> stats = email_service.download_all_attachments()
            >>> print(f"Procesados {stats['total_messages']} mensajes")
            >>> print(f"Descargados {stats['total_files']} archivos")
            >>> 
            >>> # Descarga con seguimiento de progreso
            >>> def show_progress(idx, total, message, files):
            ...     progress = (idx + 1) / total * 100
            ...     print(f"[{progress:.1f}%] {message['subject']}: {len(files)} archivos")
            >>> 
            >>> stats = email_service.download_all_attachments(on_progress=show_progress)
            >>> 
            >>> # Descarga de mensajes específicos con análisis detallado
            >>> messages = email_service.search_messages("MUTUALSER", limit=5)
            >>> 
            >>> def detailed_progress(idx, total, msg, files):
            ...     print(f"Mensaje {idx+1}/{total}: {msg['from']}")
            ...     print(f"  Asunto: {msg['subject'][:50]}...")
            ...     print(f"  Adjuntos: {len(files)}")
            ...     for file_path in files:
            ...         size_mb = os.path.getsize(file_path) / (1024*1024)
            ...         print(f"    - {os.path.basename(file_path)} ({size_mb:.2f} MB)")
            >>> 
            >>> stats = email_service.download_all_attachments(
            ...     messages=messages, 
            ...     on_progress=detailed_progress
            ... )
            >>> 
            >>> # Verificar resultados
            >>> if stats['errors'] > 0:
            ...     print(f"⚠️ {stats['errors']} errores durante la descarga")
            >>> print(f"✅ Descarga completada: {stats['total_files']} archivos")
        
        Note:
            - El proceso continúa aunque algunos mensajes fallen
            - Los errores se registran en la consola y en stats['errors']
            - Los archivos se descargan al directorio temporal del AttachmentService
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
                # Extraer fecha del correo si está disponible
                email_date = None
                if "date" in msg and msg["date"]:
                    from datetime import datetime
                    msg_date = msg["date"]
                    try:
                        # Intentar convertir a formato estándar
                        if isinstance(msg_date, str):
                            for fmt in ['%a, %d %b %Y %H:%M:%S %z', '%a, %d %b %Y %H:%M:%S', '%Y-%m-%d %H:%M:%S']:
                                try:
                                    parsed = datetime.strptime(msg_date.strip(), fmt)
                                    email_date = parsed.strftime('%Y-%m-%d %H:%M:%S')
                                    break
                                except ValueError:
                                    continue
                        elif hasattr(msg_date, 'strftime'):
                            email_date = msg_date.strftime('%Y-%m-%d %H:%M:%S')
                    except Exception:
                        pass
                
                files = self.download_message_attachments(msg["id"], email_date=email_date)
                
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
        Procesa archivos de respuesta de glosas de MUTUALSER y genera Excel consolidado
        con objeciones separadas por tipo.
        
        Args:
            archivos (list, optional): Lista de rutas de archivos Excel a procesar.
                                     Si None, usa archivos Excel descargados en la sesión actual.
                                     
        Returns:
            dict: Resultado del procesamiento con las siguientes claves:
                - success (bool): True si el procesamiento fue exitoso
                - message (str): Mensaje descriptivo (solo si success=False)
                - output_file (str): Ruta del archivo consolidado generado
                - objeciones_file (str): Ruta del archivo de objeciones generado
                - resumen (dict): Estadísticas del procesamiento
                
        Examples:
            >>> # Procesamiento automático de archivos descargados
            >>> # (después de search_messages y download_all_attachments)
            >>> resultado = email_service.procesar_mutualser()
            >>> if resultado['success']:
            ...     print(f"Consolidado: {resultado['output_file']}")
            ...     print(f"Objeciones: {resultado['objeciones_file']}")
            ...     print(f"Procesados: {resultado['resumen']['total_registros']} registros")
            >>> 
            >>> # Procesamiento de archivos específicos
            >>> archivos_mutualser = [
            ...     "C:/temp/respuesta_glosa_001.xlsx",
            ...     "C:/temp/respuesta_glosa_002.xlsx"
            ... ]
            >>> resultado = email_service.procesar_mutualser(archivos_mutualser)
            >>> 
            >>> # Análisis del resultado
            >>> if resultado['success']:
            ...     resumen = resultado['resumen']
            ...     print(f"📊 Resumen del procesamiento:")
            ...     print(f"   Total registros: {resumen['total_registros']}")
            ...     print(f"   Glosas aprobadas: {resumen.get('aprobadas', 0)}")
            ...     print(f"   Glosas objetadas: {resumen.get('objetadas', 0)}")
            ...     print(f"   Archivos procesados: {len(archivos_mutualser)}")
            ... else:
            ...     print(f"❌ Error: {resultado['message']}")
            >>> 
            >>> # Verificar archivos generados
            >>> import os
            >>> if resultado['success']:
            ...     output_path = resultado['output_file']
            ...     if os.path.exists(output_path):
            ...         size_mb = os.path.getsize(output_path) / (1024*1024)
            ...         print(f"Archivo consolidado: {size_mb:.2f} MB")
        
        Note:
            - Los archivos se procesan y consolidan según la estructura de MUTUALSER
            - Se genera automáticamente un archivo separado para objeciones
            - Los archivos resultantes se guardan en la ruta de red MINERVA si está disponible
            - Si no se especifican archivos, usa solo archivos Excel de la sesión actual
            - Excluye automáticamente archivos de devolución
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