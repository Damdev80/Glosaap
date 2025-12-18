"""
Lógica de negocio de la aplicación Glosaap

Contiene las funciones de procesamiento, filtrado y carga de datos.
"""
import os
import threading
import logging
from typing import List, Dict, Any, Callable, Optional

from app.ui.styles import COLORS

logger = logging.getLogger(__name__)


class MessageFilter:
    """Filtrador de mensajes por EPS"""
    
    @staticmethod
    def filter_by_eps(messages: List[Dict], eps: Optional[Dict]) -> List[Dict]:
        """
        Filtra mensajes según la configuración de EPS.
        
        Args:
            messages: Lista de mensajes a filtrar
            eps: Configuración de la EPS seleccionada
            
        Returns:
            Lista de mensajes que coinciden con el filtro
        """
        if not eps:
            return messages
        
        filtered = []
        filter_type = eps.get("filter_type", "keyword")
        filter_value = (eps.get("filter") or "").lower()
        subject_pattern = (eps.get("subject_pattern") or "").lower()
        sender_filter = (eps.get("sender_filter") or "").lower()
        
        for msg in messages:
            subject = (msg.get("subject") or "").lower()
            from_addr = (msg.get("from") or "").lower()
            
            if filter_type == "keyword":
                if filter_value and (filter_value in subject or filter_value in from_addr):
                    filtered.append(msg)
                    
            elif filter_type == "subject_exact_pattern":
                has_subject = subject_pattern and subject_pattern in subject
                
                if has_subject:
                    if sender_filter:
                        if sender_filter in from_addr:
                            filtered.append(msg)
                    else:
                        # Excluir Sanitas para Mutualser
                        if "sanitas" not in subject and "sanitas" not in from_addr:
                            filtered.append(msg)
                            
            elif filter_type == "email":
                if filter_value and filter_value in from_addr:
                    filtered.append(msg)
        
        return filtered
    
    @staticmethod
    def get_search_keyword(eps: Optional[Dict]) -> str:
        """
        Obtiene la palabra clave de búsqueda según la EPS.
        
        Args:
            eps: Configuración de la EPS
            
        Returns:
            Palabra clave para búsqueda IMAP
        """
        if not eps:
            return "glosa"
        
        subject_pattern = eps.get("subject_pattern", "")
        if not subject_pattern:
            return "glosa"
        
        # Palabras a ignorar (preposiciones, artículos)
        ignore_words = ['de', 'del', 'la', 'el', 'y', 'en', 'a', 'con']
        words = subject_pattern.split()
        
        # Buscar primera palabra significativa
        for word in words:
            if word.lower() not in ignore_words and len(word) > 2:
                return word
        
        return "glosa"


class EmailLoader:
    """Cargador de correos electrónicos"""
    
    def __init__(self, email_service, app_state, messages_view, page, alert_dialog):
        self.email_service = email_service
        self.app_state = app_state
        self.messages_view = messages_view
        self.page = page
        self.alert_dialog = alert_dialog
    
    def load_messages(self, search_info: str = ""):
        """
        Carga mensajes del servidor en un thread separado.
        
        Args:
            search_info: Información de búsqueda para mostrar
        """
        def worker():
            try:
                self._load_messages_sync(search_info)
            except Exception as ex:
                logger.error(f"Error cargando mensajes: {ex}")
                self.messages_view.set_loading(False, f"❌ Error: {str(ex)}")
                self.alert_dialog.show_error(
                    page=self.page,
                    title="Error en la búsqueda",
                    message=f"Ocurrió un error al buscar correos:\n\n{str(ex)}"
                )
        
        threading.Thread(target=worker, daemon=True).start()
    
    def _load_messages_sync(self, search_info: str):
        """Carga mensajes de forma síncrona"""
        self.messages_view.set_loading(True, "🔍 Buscando correos...")
        
        all_msgs = []
        downloaded_count = 0
        eps = self.app_state.selected_eps
        
        def on_found(msg):
            nonlocal downloaded_count
            all_msgs.append(msg)
            
            # Filtrar en tiempo real
            filtered = MessageFilter.filter_by_eps(all_msgs, eps)
            self.messages_view.show_messages(filtered, search_info)
            self.messages_view.set_loading(
                True, 
                f"🔍 Encontrados {len(all_msgs)} correo(s), mostrando {len(filtered)} filtrados..."
            )
            
            # Descargar adjuntos automáticamente
            if msg in filtered:
                msg_id = msg.get("id")
                if msg_id:
                    self._download_attachment(msg_id)
                    downloaded_count += 1
        
        # Obtener palabra clave de búsqueda
        search_keyword = MessageFilter.get_search_keyword(eps)
        logger.info(f"Buscando con palabra clave: '{search_keyword}'")
        
        # Buscar mensajes
        self.email_service.search_messages(
            search_keyword,
            limit=500,
            timeout=30,
            on_found=on_found,
            date_from=self.app_state.date_from,
            date_to=self.app_state.date_to
        )
        
        # Filtrar resultados finales
        msgs = MessageFilter.filter_by_eps(all_msgs, eps)
        self.app_state.found_messages = msgs
        
        # Mostrar resultados
        self._show_results(msgs, all_msgs, search_info)
    
    def _download_attachment(self, msg_id: str):
        """Descarga adjuntos de un mensaje"""
        self.messages_view.update_message_status(msg_id, "📥 Descargando...")
        try:
            files = self.email_service.download_message_attachments(msg_id)
            if files:
                self.messages_view.update_message_status(msg_id, f"✅ {len(files)} archivo(s)")
            else:
                self.messages_view.update_message_status(msg_id, "Sin adjuntos Excel")
        except Exception as e:
            logger.error(f"Error descargando adjuntos: {e}")
            self.messages_view.update_message_status(msg_id, "❌ Error", is_error=True)
    
    def _show_results(self, msgs: List[Dict], all_msgs: List[Dict], search_info: str):
        """Muestra los resultados de la búsqueda"""
        self.messages_view.show_messages(msgs, search_info)
        self.messages_view.show_download_controls(False)
        
        excel_count = len(self.email_service.get_excel_files())
        
        if msgs:
            self.messages_view.set_loading(
                False, 
                f"✅ {len(msgs)} correo(s) | 📁 {excel_count} Excel listos para procesar"
            )
            
            # Mostrar diálogo de completado
            eps_name = self.app_state.selected_eps.get("name", "") if self.app_state.selected_eps else ""
            date_range = ""
            if self.app_state.date_from and self.app_state.date_to:
                date_range = f"{self.app_state.date_from.strftime('%d/%m/%Y')} - {self.app_state.date_to.strftime('%d/%m/%Y')}"
            
            self.alert_dialog.show_search_complete(
                page=self.page,
                total_found=len(all_msgs),
                filtered_count=len(msgs),
                excel_count=excel_count,
                eps_name=eps_name,
                date_range=date_range
            )
        else:
            self.messages_view.set_loading(False, "No hay resultados")
            eps_name = self.app_state.selected_eps.get("name", "la EPS seleccionada") if self.app_state.selected_eps else ""
            self.alert_dialog.show_info(
                page=self.page,
                title="Sin resultados",
                message=f"No se encontraron correos de {eps_name} en el rango de fechas especificado."
            )


class EPSProcessor:
    """Procesador de archivos de EPS"""
    
    def __init__(self, email_service, messages_view, page, alert_dialog):
        self.email_service = email_service
        self.messages_view = messages_view
        self.page = page
        self.alert_dialog = alert_dialog
    
    def process(self, eps_type: str):
        """
        Procesa archivos de una EPS en un thread separado.
        
        Args:
            eps_type: Tipo de EPS ('mutualser' o 'coosalud')
        """
        def worker():
            try:
                if eps_type == "mutualser":
                    self._process_mutualser()
                elif eps_type == "coosalud":
                    self._process_coosalud()
            except Exception as ex:
                logger.error(f"Error procesando {eps_type}: {ex}")
                self.messages_view.set_processing(False, f"❌ Error: {str(ex)}")
                self.messages_view.processing_status.color = COLORS["error"]
                self.messages_view.process_eps_btn.disabled = False
                
                self.alert_dialog.show_error(
                    page=self.page,
                    title="Error en el procesamiento",
                    message=f"Ocurrió un error inesperado:\n\n{str(ex)}"
                )
        
        threading.Thread(target=worker, daemon=True).start()
    
    def _process_mutualser(self):
        """Procesa archivos de MUTUALSER"""
        self.messages_view.set_processing(True, "🔄 Procesando MUTUALSER...")
        self.messages_view.process_eps_btn.disabled = True
        
        excel_files = self.email_service.get_excel_files()
        
        if not excel_files:
            self._show_no_files_error()
            return
        
        logger.info(f"Procesando {len(excel_files)} archivos Excel de MUTUALSER")
        self.messages_view.set_processing(True, f"📊 Procesando {len(excel_files)} archivo(s) Excel...")
        
        resultado = self.email_service.procesar_mutualser()
        
        if resultado['success']:
            self._show_mutualser_success(resultado)
        else:
            self._show_processing_error(resultado['message'])
        
        self.messages_view.process_eps_btn.disabled = False
    
    def _process_coosalud(self):
        """Procesa archivos de COOSALUD"""
        from app.service.processors import CoosaludProcessor
        
        self.messages_view.set_processing(True, "🔄 Procesando COOSALUD...")
        self.messages_view.process_eps_btn.disabled = True
        
        excel_files = self.email_service.get_excel_files(exclude_devoluciones=True)
        
        if not excel_files:
            self.messages_view.set_processing(False, "❌ No hay archivos Excel para procesar")
            self.messages_view.process_eps_btn.disabled = False
            self.alert_dialog.show_warning(
                page=self.page,
                title="Sin archivos para procesar",
                message="No se encontraron archivos Excel de GLOSAS.\n\nLos archivos de DEVOLUCIÓN fueron excluidos automáticamente."
            )
            return
        
        logger.info(f"Procesando {len(excel_files)} archivos Excel de COOSALUD")
        self.messages_view.set_processing(True, f"📊 Procesando {len(excel_files)} archivo(s) Excel...")
        
        # Configurar procesador
        homologador_path = r"\\MINERVA\Cartera\GLOSAAP\HOMOLOGADOR\mutualser_homologacion.xlsx"
        output_dir = r"\\MINERVA\Cartera\GLOSAAP\REPOSITORIO DE RESULTADOS\COOSALUD"
        
        if not os.path.exists(output_dir):
            try:
                os.makedirs(output_dir, exist_ok=True)
            except Exception as e:
                logger.warning(f"No se pudo crear directorio: {e}")
        
        processor = CoosaludProcessor(homologador_path=homologador_path)
        result_data, message = processor.process_glosas(excel_files, output_dir=output_dir)
        
        if result_data:
            self.messages_view.set_processing(False, f"✅ {message}")
            self.messages_view.processing_status.color = COLORS["success"]
            self.alert_dialog.show_success(
                page=self.page,
                title="Procesamiento completado",
                message=message
            )
        else:
            self.messages_view.set_processing(False, f"❌ {message}")
            self.messages_view.processing_status.color = COLORS["error"]
            self.alert_dialog.show_error(
                page=self.page,
                title="Error al procesar",
                message=message
            )
        
        self.messages_view.process_eps_btn.disabled = False
    
    def _show_no_files_error(self):
        """Muestra error cuando no hay archivos"""
        self.messages_view.set_processing(False, "❌ No hay archivos Excel para procesar")
        self.messages_view.process_eps_btn.disabled = False
        self.alert_dialog.show_warning(
            page=self.page,
            title="Sin archivos para procesar",
            message="No se encontraron archivos Excel en el directorio temporal.\n\nLos archivos se almacenan automáticamente cuando descargas adjuntos."
        )
    
    def _show_mutualser_success(self, resultado: Dict):
        """Muestra éxito de procesamiento MUTUALSER"""
        resumen = resultado['resumen']
        msg = f"✅ ¡Archivos generados!\n"
        msg += f"📄 {resultado['output_file']}\n"
        if resultado.get('objeciones_file'):
            msg += f"📋 {resultado['objeciones_file']}\n"
        msg += f"📊 {resumen['total_registros']} registros | {resumen['codigos_homologados']} homologados"
        
        self.messages_view.set_processing(False, msg)
        self.messages_view.processing_status.color = COLORS["success"]
        
        output_files = [resultado['output_file']]
        if resultado.get('objeciones_file'):
            output_files.append(resultado['objeciones_file'])
        
        def open_output_folder():
            import subprocess
            output_dir = os.path.dirname(resultado['output_file'])
            subprocess.Popen(f'explorer "{output_dir}"')
        
        self.alert_dialog.show_processing_complete(
            page=self.page,
            eps_name="MUTUALSER",
            stats=resumen,
            output_files=output_files,
            on_open_folder=open_output_folder
        )
    
    def _show_processing_error(self, message: str):
        """Muestra error de procesamiento"""
        self.messages_view.set_processing(False, f"❌ Error: {message}")
        self.messages_view.processing_status.color = COLORS["error"]
        self.alert_dialog.show_error(
            page=self.page,
            title="Error al procesar",
            message=f"No se pudo procesar los archivos:\n\n{message}"
        )
