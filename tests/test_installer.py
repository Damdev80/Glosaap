"""Tests de Fase B: instalador Inno Setup + preflights anti-bugs.

Todo offline (sin ISCC, sin GUI): valida el script .iss por texto/AST,
la consistencia del mutex con main.py y el preflight de disco del updater.
"""
import ast
import re
import shutil
from pathlib import Path

import build
import updater

ROOT = Path(__file__).resolve().parent.parent
ISS = ROOT / "installer" / "glosaap.iss"

# AppId estable: cambiarlo huérfana instalaciones previas (no tocar).
APP_ID_ESPERADO = "{B4E7A1C3-8F2D-4A6B-9E5C-1D3F7A9B2C4E}"
MUTEX_ESPERADO = r"Local\GlosaapAppMutex"


def _iss() -> str:
    assert ISS.exists(), "Falta installer/glosaap.iss"
    return ISS.read_text(encoding="utf-8")


class TestIssScript:
    def test_appid_estable(self):
        match = re.search(r"AppId=\{\{([^}]+)\}", _iss())
        assert match, "ISS sin AppId"
        assert "{" + match.group(1) + "}" == APP_ID_ESPERADO

    def test_instalacion_por_usuario_sin_admin(self):
        texto = _iss()
        assert "PrivilegesRequired=lowest" in texto
        assert r"DefaultDirName={localappdata}\Glosaap" in texto

    def test_mutex_coincide_con_main(self):
        assert MUTEX_ESPERADO in _iss().replace("AppMutex=", "")
        arbol = ast.parse((ROOT / "main.py").read_text(encoding="utf-8"))
        valores = [
            n.value.value
            for n in ast.walk(arbol)
            if isinstance(n, ast.Assign)
            and any(isinstance(t, ast.Name) and t.id == "APP_MUTEX_NAME" for t in n.targets)
            and isinstance(n.value, ast.Constant)
        ]
        assert valores == [MUTEX_ESPERADO]

    def test_single_instance_en_main(self):
        arbol = ast.parse((ROOT / "main.py").read_text(encoding="utf-8"))
        mains = [
            n for n in ast.walk(arbol)
            if isinstance(n, ast.If)
            and isinstance(n.test, ast.Compare)
            and isinstance(n.test.left, ast.Name)
            and n.test.left.id == "__name__"
        ]
        assert mains, "main.py sin bloque __main__"
        llamados = []
        for n in ast.walk(mains[0]):
            if not isinstance(n, ast.Call):
                continue
            if isinstance(n.func, ast.Name):
                llamados.append(n.func.id)
            elif isinstance(n.func, ast.Attribute):
                llamados.append(n.func.attr)
        assert "_ensure_single_instance" in llamados

    def test_archivos_requeridos(self):
        texto = _iss()
        assert "dist\\Glosaap.exe" in texto or "dist/Glosaap.exe" in texto.replace("\\\\", "/")
        assert "updater.exe" in texto

    def test_version_parametrizada(self):
        texto = _iss()
        assert "/DMyAppVersion" in texto or "MyAppVersion" in texto
        assert "Glosaap_Setup_v{#MyAppVersion}" in texto


class TestFindIscc:
    def test_none_sin_iscc(self, monkeypatch):
        monkeypatch.setattr(shutil, "which", lambda *a, **k: None)
        monkeypatch.setattr("os.path.exists", lambda p: False)
        assert build.find_iscc() is None

    def test_encuentra_en_path(self, tmp_path, monkeypatch):
        fake = tmp_path / "ISCC.exe"
        fake.write_bytes(b"MZ")
        monkeypatch.setattr(shutil, "which", lambda *a, **k: str(fake))
        assert build.find_iscc() == str(fake)


class TestDiskSpace:
    def test_suficiente(self, tmp_path, monkeypatch):
        class Uso:
            free = 10 * 1024**3
        monkeypatch.setattr(shutil, "disk_usage", lambda p: Uso())
        assert updater.check_disk_space(tmp_path, 1024) is True

    def test_insuficiente(self, tmp_path, monkeypatch):
        class Uso:
            free = 1
        monkeypatch.setattr(shutil, "disk_usage", lambda p: Uso())
        assert updater.check_disk_space(tmp_path, 10**9) is False

    def test_no_medible_no_bloquea(self, tmp_path, monkeypatch):
        def _raise(p):
            raise OSError("sin disco")
        monkeypatch.setattr(shutil, "disk_usage", _raise)
        assert updater.check_disk_space(tmp_path, 10**9) is True
