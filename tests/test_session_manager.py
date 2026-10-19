"""
Tests para el gestor de sesiones (session_manager.py).

Formato v1 sin secretos en disco: keyring primario, fallback Fernet.
Compat lectura legacy v0 (base64) por una version.
"""
import base64
import json
import os

from app.core import session_manager


class TestSessionManagerImport:
    """Tests para importación del módulo."""

    def test_module_import(self):
        """Puede importar el módulo"""
        assert session_manager is not None

    def test_save_session_function(self):
        """Tiene función save_session"""
        from app.core.session_manager import save_session
        assert callable(save_session)

    def test_load_session_function(self):
        """Tiene función load_session"""
        from app.core.session_manager import load_session
        assert callable(load_session)

    def test_clear_session_function(self):
        """Tiene función clear_session"""
        from app.core.session_manager import clear_session
        assert callable(clear_session)


class TestSaveSession:
    """Tests para guardar sesión."""

    def test_save_session_creates_file(self, tmp_path):
        """save_session crea archivo de sesión"""
        session_file = tmp_path / ".session.json"
        original_session_file = session_manager.SESSION_FILE
        session_manager.SESSION_FILE = str(session_file)

        try:
            session_manager.save_session(
                "test@email.com",
                "password123",
                "imap.gmail.com"
            )

            assert session_file.exists()
        finally:
            session_manager.SESSION_FILE = original_session_file

    def test_secret_not_readable_on_disk(self, tmp_path):
        """Secreto no legible en disco (ni plano ni base64)."""
        session_file = tmp_path / ".session.json"
        original_session_file = session_manager.SESSION_FILE
        session_manager.SESSION_FILE = str(session_file)

        try:
            secret = "secret123-unico"
            session_manager.save_session(
                "test@email.com",
                secret,
                "imap.gmail.com"
            )

            raw = session_file.read_text(encoding="utf-8")
            # Ni el secreto ni su codificacion legacy deben aparecer.
            assert secret not in raw
            assert base64.b64encode(secret.encode()).decode() not in raw

            data = json.loads(raw)
            # Formato v1: sin campo password en claro.
            assert data.get("version") == 1
            assert "saved_at" in data
            assert "backend" in data
            # Si hay token, no debe decodificar al secreto sin clave.
            if "token" in data:
                assert secret not in data["token"]
        finally:
            session_manager.SESSION_FILE = original_session_file


class TestLoadSession:
    """Tests para cargar sesión."""

    def test_load_session_no_file_returns_none(self, tmp_path):
        """Sin archivo de sesión retorna None"""
        session_file = tmp_path / ".session.json"
        original_session_file = session_manager.SESSION_FILE
        session_manager.SESSION_FILE = str(session_file)

        try:
            result = session_manager.load_session()
            assert result is None
        finally:
            session_manager.SESSION_FILE = original_session_file

    def test_load_session_returns_data(self, tmp_path):
        """load_session retorna datos guardados (roundtrip)."""
        session_file = tmp_path / ".session.json"
        original_session_file = session_manager.SESSION_FILE
        session_manager.SESSION_FILE = str(session_file)

        try:
            # Guardar primero
            session_manager.save_session(
                "user@test.com",
                "mypass",
                "mail.server.com"
            )

            # Cargar
            result = session_manager.load_session()

            assert result is not None
            assert result["email"] == "user@test.com"
            assert result["password"] == "mypass"
            assert result["server"] == "mail.server.com"
        finally:
            session_manager.SESSION_FILE = original_session_file

    def test_load_session_legacy_v0_compat(self, tmp_path):
        """Compat lectura formato viejo base64 (v0) una version."""
        session_file = tmp_path / ".session.json"
        original_session_file = session_manager.SESSION_FILE
        session_manager.SESSION_FILE = str(session_file)

        try:
            legacy = {
                "email": "legacy@test.com",
                "password": base64.b64encode("legacypass".encode()).decode(),
                "server": "mail.legacy.com",
            }
            session_file.write_text(json.dumps(legacy), encoding="utf-8")

            result = session_manager.load_session()

            assert result is not None
            assert result["email"] == "legacy@test.com"
            assert result["password"] == "legacypass"
            assert result["server"] == "mail.legacy.com"
        finally:
            session_manager.SESSION_FILE = original_session_file

    def test_load_session_corrupt_returns_none(self, tmp_path):
        """Archivo corrupto retorna None sin lanzar."""
        session_file = tmp_path / ".session.json"
        original_session_file = session_manager.SESSION_FILE
        session_manager.SESSION_FILE = str(session_file)

        try:
            session_file.write_text("{no-json", encoding="utf-8")
            assert session_manager.load_session() is None
        finally:
            session_manager.SESSION_FILE = original_session_file


class TestClearSession:
    """Tests para limpiar sesión."""

    def test_clear_session_removes_file(self, tmp_path):
        """clear_session elimina archivo"""
        session_file = tmp_path / ".session.json"
        original_session_file = session_manager.SESSION_FILE
        session_manager.SESSION_FILE = str(session_file)

        try:
            # Crear archivo
            session_manager.save_session("a@b.com", "pass", "server")
            assert session_file.exists()

            # Limpiar
            session_manager.clear_session()
            assert not session_file.exists()
        finally:
            session_manager.SESSION_FILE = original_session_file

    def test_clear_session_no_file_no_error(self, tmp_path):
        """clear_session sin archivo no da error"""
        session_file = tmp_path / ".session.json"
        original_session_file = session_manager.SESSION_FILE
        session_manager.SESSION_FILE = str(session_file)

        try:
            # No debería lanzar excepción
            session_manager.clear_session()
        finally:
            session_manager.SESSION_FILE = original_session_file


class TestSessionManagerConstants:
    """Tests para constantes del módulo."""

    def test_session_file_defined(self):
        """SESSION_FILE está definido"""
        from app.core.session_manager import SESSION_FILE
        assert SESSION_FILE is not None

    def test_session_file_is_json(self):
        """SESSION_FILE es archivo JSON"""
        from app.core.session_manager import SESSION_FILE
        assert SESSION_FILE.endswith('.json')

    def test_project_root_defined(self):
        """PROJECT_ROOT está definido"""
        from app.core.session_manager import PROJECT_ROOT
        assert PROJECT_ROOT is not None


class TestSessionDataIntegrity:
    """Tests para integridad de datos de sesión."""

    def test_roundtrip_special_characters(self, tmp_path):
        """Guarda y carga contraseñas con caracteres especiales"""
        session_file = tmp_path / ".session.json"
        original_session_file = session_manager.SESSION_FILE
        session_manager.SESSION_FILE = str(session_file)

        try:
            special_pass = "p@ss!word#123$%^"
            session_manager.save_session("test@mail.com", special_pass, "server")

            result = session_manager.load_session()

            assert result["password"] == special_pass
        finally:
            session_manager.SESSION_FILE = original_session_file


class TestSessionModule:
    """Tests para el módulo en general."""

    def test_module_has_docstring(self):
        """El módulo tiene docstring"""
        assert session_manager.__doc__ is not None
