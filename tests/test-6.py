
import sys
import os
import email
from email.header import decode_header
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from app.core.imap_client import ImapClient

def main():
	email_addr = "visado@laconcepcion.org"
	password = "S3rembeque25*"
	imap = ImapClient()
	imap.connect(email_addr, password, server="mail.laconcepcion.org", port=993, use_ssl=True)
	from datetime import datetime, timedelta
	imap.conn.select("INBOX")
	# Rango de fechas: último mes
	end_date = datetime.strptime("22-Jan-2026", "%d-%b-%Y")
	start_date = end_date - timedelta(days=30)
	start_str = start_date.strftime("%d-%b-%Y")
	end_str = end_date.strftime("%d-%b-%Y")
	print(f"Buscando correos desde: {start_str} hasta: {end_str}")
	status, data = imap.conn.search(None, f'(SINCE "{start_str}" BEFORE "{end_str}")')
	if status != "OK":
		print("Error en búsqueda IMAP.")
		return
	ids = data[0].split()
	print(f"Correos encontrados: {len(ids)}")
	encontrados_coosalud = 0
	encontrados_mutualser = 0
	for msg_id in ids:
		status, msg_data = imap.conn.fetch(msg_id, "(RFC822)")
		if status == "OK":
			msg = email.message_from_bytes(msg_data[0][1])
			subject_raw = msg.get("Subject")
			if subject_raw is None:
				continue
			subject, encoding = decode_header(subject_raw)[0]
			if isinstance(subject, bytes):
				subject = subject.decode(encoding or "utf-8", errors="ignore")
			from_addr = msg.get("From")
			# Normaliza para comparar
			subject_norm = subject.lower() if subject else ""
			from_norm = from_addr.lower() if from_addr else ""
			# Coosalud
			if "reporte glosas y devoluciones" in subject_norm and "vco.glosas1@coosalud.com" in from_norm:
				print(f"[COOSALUD] Asunto: {subject} | De: {from_addr}")
				encontrados_coosalud += 1
			# Mutualser
			if "objeciones de glosa factura fc" in subject_norm:
				print(f"[MUTUALSER] Asunto: {subject} | De: {from_addr}")
				encontrados_mutualser += 1
		else:
			print(f"Error al obtener correo {msg_id}")
	print(f"Correos Coosalud que cumplen asunto y remitente: {encontrados_coosalud}")
	print(f"Correos Mutualser con patrón de asunto: {encontrados_mutualser}")
	imap.disconnect()

if __name__ == "__main__":
	main()
