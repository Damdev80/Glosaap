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

    def search_by_subject(self, keyword: str, folder: str = "INBOX", limit: Optional[int] = None, timeout: int = 30, on_found: Optional[Callable[[Dict[str, Any]], None]] = None, date_from: Optional[datetime] = None, date_to: Optional[datetime] = None) -> List[Dict[str, Any]]:
        """
        Busca correos que contengan una palabra clave en el asunto.
        Busca tanto correos leídos como no leídos.
        
        Args:
            keyword: Palabra clave a buscar en el asunto
            folder: Carpeta IMAP (default: INBOX)
            limit: Máximo de correos a retornar (None = sin límite)
            timeout: Tiempo máximo en segundos SIN ENCONTRAR un nuevo correo
            on_found: Callback que se llama cada vez que se encuentra un mensaje
            date_from: Fecha inicio del rango (datetime o string)
            date_to: Fecha fin del rango (datetime o string)
            
        Returns:
            Lista de diccionarios con información de los mensajes
        """
        if self.conn is None:
            return []
            
        last_found_time = time.time()
        
        try:
            self.select_folder(folder)
            
            # Construir criterio de búsqueda con fechas
            search_criteria = "ALL"
            
            if date_from or date_to:
                # Formatear fechas para IMAP (formato: DD-Mon-YYYY)
                from datetime import timedelta
                
                def format_imap_date(date_obj: Any, add_days: int = 0) -> Optional[str]:
                    if date_obj is None:
                        return None
                    if isinstance(date_obj, str):
                        # Si ya es string, intentar parsearlo
                        try:
                            date_obj = datetime.strptime(date_obj, '%Y-%m-%d')
                        except Exception:
                            try:
                                date_obj = datetime.strptime(date_obj, '%d/%m/%Y')
                            except Exception:
                                return None
                    # Agregar días si es necesario (para BEFORE que es exclusivo)
                    if add_days:
                        date_obj = date_obj + timedelta(days=add_days)
                    # Formato IMAP: DD-Mon-YYYY (ej: 01-Nov-2025)
                    months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 
                              'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
                    return f"{date_obj.day:02d}-{months[date_obj.month-1]}-{date_obj.year}"
                
                criteria_parts: List[str] = []
                
                if date_from:
                    imap_date_from = format_imap_date(date_from)
                    if imap_date_from:
                        criteria_parts.append(f'SINCE {imap_date_from}')
                        logger.info(f"Buscando desde: {imap_date_from}")
                
                if date_to:
                    # BEFORE es exclusivo, así que sumamos 1 día para incluir el día seleccionado
                    imap_date_to = format_imap_date(date_to, add_days=1)
                    if imap_date_to:
                        criteria_parts.append(f'BEFORE {imap_date_to}')
                        logger.info(f"Buscando hasta: {imap_date_to} (exclusivo)")
                
                if criteria_parts:
                    search_criteria = '(' + ' '.join(criteria_parts) + ')'
                    logger.info(f"Criterio de búsqueda IMAP: {search_criteria}")
            
            # Buscar correos según criterio
            logger.info(f"Ejecutando búsqueda IMAP con criterio: {search_criteria}")
            typ, data = self.conn.search(None, search_criteria)
            if typ != "OK" or data[0] is None:
                return []
            
            ids = data[0].split()
            if not ids or ids == [b'']:
                return []
            
            msgs: List[Dict[str, Any]] = []
            
            # Procesar en orden inverso (más recientes primero)
            for msg_id in reversed(ids):
                # Verificar timeout: tiempo desde el ÚLTIMO correo encontrado
                time_since_last = time.time() - last_found_time
                if time_since_last > timeout:
                    logger.info(f"Timeout: {timeout}s sin encontrar nuevos correos. Total: {len(msgs)}")
                    break
                    
                if limit is not None and len(msgs) >= limit:
                    break
                    
                try:
                    typ, msg_data = self.conn.fetch(msg_id, "(RFC822)")
                    if typ != "OK" or not msg_data or msg_data[0] is None:
                        continue
                        
                    raw = msg_data[0][1]
                    if not isinstance(raw, bytes):
                        continue
                    msg = email.message_from_bytes(raw)
                    subject = _decode_header(msg.get("Subject")) or ""
                    
                    # Filtrar por palabra clave (case-insensitive)
                    if keyword.lower() not in subject.lower():
                        continue
                    
                    # ¡Encontramos un correo! Reiniciar el contador
                    last_found_time = time.time()
                    
                    from_ = _decode_header(msg.get("From"))
                    date = _decode_header(msg.get("Date"))
                    
                    # Detectar adjuntos - múltiples métodos
                    has_attachments = False
                    for part in msg.walk():
                        # Método 1: Content-Disposition
                        content_disposition = part.get("Content-Disposition", "")
                        if "attachment" in content_disposition.lower():
                            has_attachments = True
                            break
                        # Método 2: Filename presente
                        if part.get_filename():
                            has_attachments = True
                            break
                        # Método 3: Content-Type con name
                        content_type = part.get_content_type()
                        if content_type not in ["text/plain", "text/html", "multipart/alternative", "multipart/mixed", "multipart/related"]:
                            if part.get_payload(decode=True):  # Tiene contenido
                                has_attachments = True
                                break
                    
                    msg_data = {
                        "id": msg_id.decode() if isinstance(msg_id, bytes) else str(msg_id),
                        "subject": subject,
                        "from": from_,
                        "date": date,
                        "has_attachments": has_attachments,
                    }
                    
                    msgs.append(msg_data)
                    
                    # Llamar callback si existe
                    if on_found:
                        on_found(msg_data)
                        
                except Exception as e:
                    continue
            
            return msgs
            
        except Exception as e:
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
