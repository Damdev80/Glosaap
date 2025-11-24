import imaplib
import email
from email.header import decode_header
import os
import tempfile


def _decode_header(value):
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
        self.conn = None
        self.tempdir = None

    def connect(self, email_addr, password, server="imap.gmail.com", port=993, use_ssl=True):
        if use_ssl:
            conn = imaplib.IMAP4_SSL(server, port)
        else:
            conn = imaplib.IMAP4(server, port)
        conn.login(email_addr, password)
        self.conn = conn
        return True

    def list_mailboxes(self):
        typ, data = self.conn.list()
        if typ != "OK":
            return []
        boxes = []
        for line in data:
            if isinstance(line, bytes):
                line = line.decode(errors="ignore")
            boxes.append(line)
        return boxes

    def select_folder(self, folder="INBOX"):
        typ, data = self.conn.select(folder)
        if typ != "OK":
            raise RuntimeError(f"Unable to select folder {folder}")
        return int(data[0])

    def fetch_recent(self, folder="INBOX", limit=10):
        self.select_folder(folder)
        typ, data = self.conn.search(None, "ALL")
        if typ != "OK":
            return []
        ids = data[0].split()
        ids = ids[-limit:]
        msgs = []
        for msg_id in reversed(ids):
            typ, msg_data = self.conn.fetch(msg_id, "(RFC822)")
            if typ != "OK":
                continue
            raw = msg_data[0][1]
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

    def search_by_subject(self, keyword, folder="INBOX", limit=100, timeout=15, on_found=None):
        """
        Busca correos que contengan una palabra clave en el asunto.
        Busca tanto correos leídos como no leídos.
        timeout: tiempo máximo en segundos para buscar
        on_found: callback que se llama cada vez que se encuentra un mensaje
        """
        import time
        start_time = time.time()
        
        try:
            self.select_folder(folder)
            
            # Buscar TODOS los correos (leídos y no leídos)
            typ, data = self.conn.search(None, "ALL")
            if typ != "OK":
                return []
            
            ids = data[0].split()
            if not ids or ids == [b'']:
                return []
            
            msgs = []
            
            # Procesar en orden inverso (más recientes primero)
            for msg_id in reversed(ids):
                # Verificar timeout
                if time.time() - start_time > timeout:
                    print(f"⏱️ Timeout alcanzado: {len(msgs)} correos encontrados en {timeout}s")
                    break
                    
                if len(msgs) >= limit:
                    break
                    
                try:
                    typ, msg_data = self.conn.fetch(msg_id, "(RFC822)")
                    if typ != "OK" or not msg_data or not msg_data[0]:
                        continue
                        
                    raw = msg_data[0][1]
                    msg = email.message_from_bytes(raw)
                    subject = _decode_header(msg.get("Subject")) or ""
                    
                    # Filtrar por palabra clave (case-insensitive)
                    if keyword.lower() not in subject.lower():
                        continue
                    
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

    def download_attachments(self, msg_id, folder="INBOX", dest_dir=None):
        """
        Descarga solo adjuntos de tipo Excel, Word o PDF
        """
        self.select_folder(folder)
        typ, msg_data = self.conn.fetch(msg_id.encode() if isinstance(msg_id, str) else msg_id, "(RFC822)")
        if typ != "OK":
            return []
        raw = msg_data[0][1]
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
        
        saved = []
        skipped = []
        
        for part in msg.walk():
            # Múltiples métodos para detectar adjuntos
            filename = part.get_filename()
            
            # Si no tiene filename, revisar Content-Disposition y Content-Type
            if not filename:
                content_disposition = part.get("Content-Disposition", "")
                if "attachment" in content_disposition.lower():
                    # Intentar extraer filename del Content-Disposition
                    import re
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
                if not payload:
                    continue
                    
                safe_name = filename.replace(os.path.sep, "_")
                path = os.path.join(out_dir, safe_name)
                
                with open(path, "wb") as f:
                    f.write(payload)
                    
                saved.append(path)
                print(f"✅ Adjunto guardado: {safe_name}")
        
        if skipped:
            print(f"ℹ️  {len(skipped)} archivo(s) omitido(s) (imágenes, etc.)") 
        
        if not saved:
            print("⚠️ No se encontraron adjuntos Excel/Word/PDF en el mensaje")
            
        return saved

    def logout(self):
        try:
            if self.conn:
                self.conn.logout()
        except Exception:
            pass
