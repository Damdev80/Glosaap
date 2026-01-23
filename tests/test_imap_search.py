import unittest
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from app.core.imap_client import ImapClient
from datetime import datetime, timedelta

class TestImapSearch(unittest.TestCase):
    def setUp(self):
        self.email_addr = 'visado@laconcepcion.org'
        self.password = 'S3rembeque25*'
        self.server = 'mail.laconcepcion.org'
        self.port = 993
        self.use_ssl = True
        self.client = ImapClient()
        self.client.connect(self.email_addr, self.password, server=self.server, port=self.port, use_ssl=self.use_ssl)

    def tearDown(self):
        self.client.logout()

    def test_search_coosalud_report_on_specific_day(self):
        """
        Buscar correos SOLO el 22/01/2026:
        - Asunto: 'Reporte Glosas y Devoluciones'
        - Remitente: 'vco.glosas1@coosalud.com'
        - Con 3 archivos adjuntos
        """
        from datetime import datetime
        date_from = datetime.strptime('22-01-2026', '%d-%m-%Y')
        date_to = datetime.strptime('22-01-2026', '%d-%m-%Y')
        results = self.client.search_by_subject(
            keyword='Reporte Glosas y Devoluciones',
            date_from=date_from,
            date_to=date_to
        )
        filtered = []
        for msg in results:
            # Filtrar por remitente exacto
            if msg.get('from', '').lower().find('vco.glosas1@coosalud.com') == -1:
                continue
            # Contar adjuntos
            msg_id = msg['id']
            attachments = self.client.download_attachments(msg_id)
            if len(attachments) == 3:
                msg['attachments'] = attachments
                filtered.append(msg)
        print(f"Correos encontrados con asunto y remitente correctos, 3 adjuntos, el 22-Jan-2026: {len(filtered)}")
        for msg in filtered:
            subject = msg['subject']
            sender = msg['from']
            date = msg['date']
            print(f"Asunto: {subject}, De: {sender}, Fecha: {date}, Adjuntos: {len(msg.get('attachments', []))}")
        self.assertTrue(len(filtered) > 0)

    def test_search_by_subsanacion(self):
        # Busca por palabra 'subsanación' en el asunto
        since = datetime.now() - timedelta(days=30)
        before = datetime.now() + timedelta(days=1)
        results = self.client.search_by_subject(
            keyword='subsanación',
            date_from=since,
            date_to=before
        )
        print(f"Correos encontrados por 'subsanación': {len(results)}")
        for msg in results:
            print(f"Asunto: {msg.get('subject')}, De: {msg.get('from')}, Fecha: {msg.get('date')}")
        self.assertIsInstance(results, list)

    def test_search_by_subject(self):
        # Busca por asunto exacto (usa search_by_subject)
        since = datetime.now() - timedelta(days=30)
        before = datetime.now() + timedelta(days=1)
        results = self.client.search_by_subject(
            keyword='Reporte Glosas y Devoluciones',
            date_from=since,
            date_to=before
        )
        print(f"Correos encontrados: {len(results)}")
        for msg in results:
            print(f"Asunto: {msg.get('subject')}, De: {msg.get('from')}, Fecha: {msg.get('date')}")
        self.assertIsInstance(results, list)

    def test_search_by_keyword(self):
        # Busca por palabra clave en el asunto
        since = datetime.now() - timedelta(days=30)
        before = datetime.now() + timedelta(days=1)
        results = self.client.search_by_subject(
            keyword='glosas',
            date_from=since,
            date_to=before
        )
        print(f"Correos encontrados por keyword: {len(results)}")
        for msg in results:
            print(f"Asunto: {msg.get('subject')}, De: {msg.get('from')}, Fecha: {msg.get('date')}")
        self.assertIsInstance(results, list)

    def test_search_no_results(self):
        # Busca con un asunto que no existe
        since = datetime.now() - timedelta(days=30)
        before = datetime.now() + timedelta(days=1)
        results = self.client.search_by_subject(
            keyword='AsuntoInexistente',
            date_from=since,
            date_to=before
        )
        print(f"Correos encontrados inexistente: {len(results)}")
        self.assertEqual(len(results), 0)

if __name__ == '__main__':
    unittest.main()
