import imaplib
import email
from email.header import decode_header
import os
import tempfile
import logging
import re
import time
from datetime import datetime
from typing import Optional, List, Dict, Any, Callable, Union

# Logger del módulo
logger = logging.getLogger(__name__)


def _decode_header(value) -> str:
    if value is None:
        return ""
    parts = decode_header(value)
    out = []
    for text, enc in parts:
        if isinstance(text, bytes):
            try:
                out.append(text.decode(enc or "utf-8", errors="ignore"))
            except Exception:
                out.append(text.decode("utf-8", errors="ignore"))
        else:
            out.append(text)
    return "".join(out)


class ImapClient:
    """Minimal IMAP helper to connect, list recent messages and download attachments."""

    def __init__(self):
        self.conn: Optional[Union[imaplib.IMAP4_SSL, imaplib.IMAP4]] = None
        self.tempdir: Optional[str] = None
        self.imap_server: str = ""

    def _detect_imap_server(self, email_addr: str) -> str:
        """Detecta el servidor IMAP basado en el dominio del correo"""
        domain = email_addr.split('@')[-1].lower()
        
        # Servidores conocidos
        known_servers = {
            'gmail.com': 'imap.gmail.com',
            'googlemail.com': 'imap.gmail.com',
            'outlook.com': 'outlook.office365.com',
            'hotmail.com': 'outlook.office365.com',
            'live.com': 'outlook.office365.com',
            'yahoo.com': 'imap.mail.yahoo.com',
            'yahoo.es': 'imap.mail.yahoo.com',
        }
        
        if domain in known_servers:
            return known_servers[domain]
        
        # Para dominios personalizados (cPanel, hosting propio):
        # Intentar con mail.dominio primero (más común en cPanel)
        return f"mail.{domain}"

    def connect(self, email_addr, password, server=None, port=993, use_ssl=True):
        # Auto-detectar servidor si no se especifica
        if server is None:
            server = self._detect_imap_server(email_addr)
            logger.info(f"Servidor IMAP detectado: {server}")
        
        if use_ssl:
            conn = imaplib.IMAP4_SSL(server, port)
        else:
            conn = imaplib.IMAP4(server, port)
        conn.login(email_addr, password)
        self.conn = conn
        self.imap_server = server
        return True

    def list_mailboxes(self) -> List[str]:
        if self.conn is None:
            return []
        typ, data = self.conn.list()
        if typ != "OK":
            return []
        boxes = []
        for line in data:
            if line is None:
                continue
            if isinstance(line, bytes):
                boxes.append(line.decode(errors="ignore"))
            else:
                boxes.append(str(line))
        return boxes

    def select_folder(self, folder: str = "INBOX") -> int:
        if self.conn is None:
            raise RuntimeError("Not connected")
        typ, data = self.conn.select(folder)
        if typ != "OK":
            raise RuntimeError(f"Unable to select folder {folder}")
        if data[0] is None:
            return 0
        return int(data[0])

    def fetch_recent(self, folder: str = "INBOX", limit: int = 10) -> List[Dict[str, Any]]:
        if self.conn is None:
            return []
        self.select_folder(folder)
        typ, data = self.conn.search(None, "ALL")
        if typ != "OK" or data[0] is None:
            return []
        ids = data[0].split()
        ids = ids[-limit:]
        msgs: List[Dict[str, Any]] = []
        for msg_id in reversed(ids):
            typ, msg_data = self.conn.fetch(msg_id, "(RFC822)")
            if typ != "OK" or not msg_data or msg_data[0] is None:
                continue
            raw = msg_data[0][1]
            if not isinstance(raw, bytes):
                continue
            msg = email.message_from_bytes(raw)
            subject = _decode_header(msg.get("Subject"))
            from_ = _decode_header(msg.get("From"))
            date = _decode_header(msg.get("Date"))
            has_attachments = False
            for part in msg.walk():
                content_disposition = part.get_content_disposition()
                if content_disposition == "attachment" or part.get_filename():
                    has_attachments = True
                    break
            msgs.append({
                "id": msg_id.decode() if isinstance(msg_id, bytes) else str(msg_id),
                "subject": subject,
                "from": from_,
                "date": date,
                "has_attachments": has_attachments,
            })
        return msgs

    # ==================== MÉTODOS AUXILIARES PARA BÚSQUEDA ====================
    
    def _format_imap_date(self, date_obj: Any, add_days: int = 0) -> Optional[str]:
        """
        Formatea una fecha al formato IMAP (DD-Mon-YYYY).
        
        Args:
            date_obj: Fecha como datetime o string
            add_days: Días a agregar (útil para BEFORE que es exclusivo)
            
        Returns:
            String formateado o None si no se puede parsear
        """
        from datetime import timedelta
        
        if date_obj is None:
            return None
            
        if isinstance(date_obj, str):
            # Si ya es string, intentar parsearlo
            for fmt in ['%Y-%m-%d', '%d/%m/%Y']:
                try:
                    date_obj = datetime.strptime(date_obj, fmt)
                    break
                except Exception:
                    continue
            else:
                return None
                
        # Agregar días si es necesario
        if add_days:
            date_obj = date_obj + timedelta(days=add_days)
            
        # Formato IMAP: DD-Mon-YYYY
        months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 
                  'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
        return f"{date_obj.day:02d}-{months[date_obj.month-1]}-{date_obj.year}"
    
    def _build_search_criteria(
        self, 
        keyword: Optional[str] = None, 
        date_from: Optional[datetime] = None, 
        date_to: Optional[datetime] = None
    ) -> str:
        """
        Construye el criterio de búsqueda IMAP.
        
        Args:
            keyword: Palabra clave para buscar en SUBJECT
            date_from: Fecha inicio (SINCE)
            date_to: Fecha fin (BEFORE)
            
        Returns:
            String con criterio IMAP formateado
        """
        criteria_parts: List[str] = []
        
        # Búsqueda por SUBJECT
        if keyword:
            safe_keyword = keyword.replace('"', '\\"')
            criteria_parts.append(f'SUBJECT "{safe_keyword}"')
            logger.info(f"Buscando por asunto: {keyword}")
        
        # Rango de fechas
        if date_from:
            imap_date = self._format_imap_date(date_from)
            if imap_date:
                criteria_parts.append(f'SINCE {imap_date}')
                logger.info(f"Buscando desde: {imap_date}")
        
        if date_to:
            # BEFORE es exclusivo, sumamos 1 día
            imap_date = self._format_imap_date(date_to, add_days=1)
            if imap_date:
                criteria_parts.append(f'BEFORE {imap_date}')
                logger.info(f"Buscando hasta: {imap_date}")
        
        if criteria_parts:
            return '(' + ' '.join(criteria_parts) + ')'
        return "ALL"
    
    def _execute_search(self, criteria: str) -> List[bytes]:
        """
        Ejecuta la búsqueda IMAP y retorna los IDs.
        
        Args:
            criteria: Criterio de búsqueda IMAP
            
        Returns:
            Lista de IDs de mensajes encontrados
        """
        logger.info(f"Criterio de búsqueda IMAP: {criteria}")
        
        typ, data = self.conn.search(None, criteria)
        
        if typ != "OK" or data[0] is None:
            logger.info("Búsqueda IMAP no retornó resultados")
            return []
        
        ids = data[0].split()
        if not ids or ids == [b'']:
            logger.info("No se encontraron IDs de correos")
            return []
        
        logger.info(f"Correos encontrados por IMAP: {len(ids)}")
        return ids
    
    def _detect_attachments(self, msg: email.message.Message) -> bool:
        """
        Detecta si un mensaje tiene adjuntos.
        
        Args:
            msg: Mensaje de email parseado
            
        Returns:
            True si tiene adjuntos
        """
        for part in msg.walk():
            # Método 1: Content-Disposition
            content_disposition = part.get("Content-Disposition", "")
            if "attachment" in content_disposition.lower():
                return True
                
            # Método 2: Filename presente
            if part.get_filename():
                return True
                
            # Método 3: Content-Type no es texto
            content_type = part.get_content_type()
            if content_type not in ["text/plain", "text/html", "multipart/alternative", 
                                     "multipart/mixed", "multipart/related"]:
                if part.get_payload(decode=True):
                    return True
        return False
    
    def _parse_message(self, msg_id: bytes, keyword: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Parsea un mensaje individual y extrae su información.
        
        Args:
            msg_id: ID del mensaje en IMAP
            keyword: Palabra clave para filtrar (opcional)
            
        Returns:
            Diccionario con info del mensaje o None si debe descartarse
        """
        try:
            typ, msg_data = self.conn.fetch(msg_id, "(RFC822)")
            if typ != "OK" or not msg_data or msg_data[0] is None:
                return None
            
            raw = msg_data[0][1]
            if not isinstance(raw, bytes):
                return None
                
            msg = email.message_from_bytes(raw)
            subject = _decode_header(msg.get("Subject")) or ""
            
            # Filtrar por keyword (respaldo si IMAP no filtró bien)
            if keyword and keyword.lower() not in subject.lower():
                logger.debug(f"Correo descartado: {subject[:50]}")
                return None
            
            logger.info(f"Correo encontrado: {subject[:60]}...")
            
            return {
                "id": msg_id.decode() if isinstance(msg_id, bytes) else str(msg_id),
                "subject": subject,
                "from": _decode_header(msg.get("From")),
                "date": _decode_header(msg.get("Date")),
                "has_attachments": self._detect_attachments(msg),
            }
            
        except Exception as e:
            logger.debug(f"Error procesando correo {msg_id}: {e}")
            return None
    
    def _process_message_ids(
        self, 
        ids: List[bytes], 
        keyword: Optional[str],
        limit: Optional[int],
        timeout: int,
        on_found: Optional[Callable[[Dict[str, Any]], None]]
    ) -> List[Dict[str, Any]]:
        """
        Procesa una lista de IDs de mensajes.
        
        Args:
            ids: Lista de IDs de mensajes
            keyword: Palabra clave para filtrar
            limit: Máximo de mensajes a retornar
            timeout: Timeout en segundos sin encontrar nuevos
            on_found: Callback por cada mensaje encontrado
            
        Returns:
            Lista de mensajes procesados
        """
        msgs: List[Dict[str, Any]] = []
        last_found_time = time.time()
        processed_count = 0
        
        # Procesar más recientes primero
        for msg_id in reversed(ids):
            processed_count += 1
            
            # Verificar timeout
            time_since_last = time.time() - last_found_time
            effective_timeout = timeout if msgs else timeout * 2
            
            if time_since_last > effective_timeout and processed_count > 10:
                logger.info(f"Timeout: {effective_timeout}s sin nuevos. "
                           f"Procesados: {processed_count}, Encontrados: {len(msgs)}")
                break
            
            # Verificar límite
            if limit is not None and len(msgs) >= limit:
                break
            
            # Parsear mensaje
            msg_info = self._parse_message(msg_id, keyword)
            if msg_info:
                last_found_time = time.time()
                msgs.append(msg_info)
                
                if on_found:
                    on_found(msg_info)
        
        return msgs
    
    # ==================== MÉTODO PRINCIPAL DE BÚSQUEDA ====================
    
    def search_by_subject(
        self, 
        keyword: str, 
        folder: str = "INBOX", 
        limit: Optional[int] = None, 
        timeout: int = 120, 
        on_found: Optional[Callable[[Dict[str, Any]], None]] = None, 
        date_from: Optional[datetime] = None, 
        date_to: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """
        Busca correos que contengan una palabra clave en el asunto.
        
        Args:
            keyword: Palabra clave a buscar en el asunto
            folder: Carpeta IMAP (default: INBOX)
            limit: Máximo de correos a retornar (None = sin límite)
            timeout: Segundos sin encontrar nuevo correo antes de parar
            on_found: Callback por cada mensaje encontrado
            date_from: Fecha inicio del rango
            date_to: Fecha fin del rango
            
        Returns:
            Lista de diccionarios con información de los mensajes
        """
        if self.conn is None:
            return []
        
        try:
            self.select_folder(folder)
            
            # 1. Construir criterio de búsqueda
            criteria = self._build_search_criteria(keyword, date_from, date_to)
            
            # 2. Ejecutar búsqueda
            ids = self._execute_search(criteria)
            if not ids:
                return []
            
            # 3. Procesar mensajes encontrados
            return self._process_message_ids(ids, keyword, limit, timeout, on_found)
            
        except Exception as e:
            logger.error(f"Error en búsqueda: {e}")
            return []

    def download_attachments(self, msg_id: Union[str, bytes], folder: str = "INBOX", dest_dir: Optional[str] = None) -> List[str]:
        """
        Descarga solo adjuntos de tipo Excel, Word o PDF
        """
        if self.conn is None:
            return []
            
        self.select_folder(folder)
        msg_id_bytes = msg_id.encode() if isinstance(msg_id, str) else msg_id
        typ, msg_data = self.conn.fetch(msg_id_bytes.decode() if isinstance(msg_id_bytes, bytes) else str(msg_id_bytes), "(RFC822)")
        if typ != "OK" or not msg_data or msg_data[0] is None:
            return []
        raw = msg_data[0][1]
        if not isinstance(raw, bytes):
            return []
        msg = email.message_from_bytes(raw)
        out_dir = dest_dir or os.path.join(tempfile.gettempdir(), "glosaap_attachments")
        if os.path.exists(out_dir) is False:
            os.makedirs(out_dir, exist_ok=True)
        
        # Extensiones permitidas
        ALLOWED_EXTENSIONS = (
            '.xlsx', '.xls', '.xlsm', '.xlsb',  # Excel
            '.doc', '.docx', '.docm',            # Word
            '.pdf'                                # PDF
        )
        
        saved: List[str] = []
        skipped: List[str] = []
        
        for part in msg.walk():
            # Múltiples métodos para detectar adjuntos
            filename = part.get_filename()
            
            # Si no tiene filename, revisar Content-Disposition y Content-Type
            if not filename:
                content_disposition = part.get("Content-Disposition", "")
                if "attachment" in content_disposition.lower():
                    # Intentar extraer filename del Content-Disposition
                    match = re.search(r'filename[\s]*=[\s]*"?([^"]+)"?', content_disposition)
                    if match:
                        filename = match.group(1)
            
            if filename:
                filename = _decode_header(filename)
                
                # Filtrar: solo guardar archivos permitidos
                file_ext = os.path.splitext(filename.lower())[1]
                
                if file_ext not in ALLOWED_EXTENSIONS:
                    skipped.append(filename)
                    continue
                
                payload = part.get_payload(decode=True)
                if not payload or not isinstance(payload, bytes):
                    continue
                    
                safe_name = filename.replace(os.path.sep, "_")
                path = os.path.join(out_dir, safe_name)
                
                with open(path, "wb") as f:
                    f.write(payload)
                    
                saved.append(path)
                logger.debug(f"Adjunto guardado: {safe_name}")
        
        if skipped:
            logger.debug(f"{len(skipped)} archivo(s) omitido(s) (imágenes, etc.)")
        
        if not saved:
            logger.debug("No se encontraron adjuntos Excel/Word/PDF en el mensaje")
            
        return saved

    def logout(self):
        """Cierra la conexión IMAP"""
        try:
            if self.conn:
                self.conn.logout()
                logger.debug("Sesión IMAP cerrada")
        except Exception:
            pass
