import unittest
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from app.core.imap_client import ImapClient
from datetime import datetime, timedelta

class TestImapFetchRecent(unittest.TestCase):
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

    def test_fetch_recent(self):
        # Busca los 10 correos más recientes sin filtros
        results = self.client.fetch_recent(limit=10)
        print(f"Correos recientes encontrados: {len(results)}")
        for msg in results:
            print(f"Asunto: {msg.get('subject')}, De: {msg.get('from')}, Fecha: {msg.get('date')}")
        self.assertIsInstance(results, list)

if __name__ == '__main__':
    unittest.main()
