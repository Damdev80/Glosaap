"""Consistencia de release: la versión debe decir lo mismo en todas partes.

Espejo automatizado de lo que sincroniza `bump.py`:
- APP_VERSION en app/config/settings.py == version en pyproject.toml.
- La versión aparece en README.md, docs/MANUAL_USUARIO.md y
  docs/AUTO_UPDATE.md (bump.py reemplaza todas las ocurrencias).
- CHANGELOG.md trae entrada `## [<version>]` (bump.py la exige;
  este test además impide dejar bullets `(completar)`).
- Toda EPS habilitada con homologador_file apunta a una clave real de
  HOMOLOGADOR_FILES (evita el "homologador no encontrado" por typo).

Si este test falla, no taguear: corre `python bump.py X.Y.Z` y completa
el CHANGELOG antes de publicar.
"""
import re
from pathlib import Path

from app.config import settings
from app.config.eps_config import EPS_CONFIG

ROOT = Path(__file__).resolve().parent.parent


def _app_version() -> str:
    text = (ROOT / "app" / "config" / "settings.py").read_text(encoding="utf-8")
    match = re.search(r'^APP_VERSION\s*=\s*"([^"]+)"', text, re.MULTILINE)
    assert match, "APP_VERSION no encontrada en settings.py"
    return match.group(1)


class TestReleaseConsistency:
    def test_settings_y_pyproject_coinciden(self):
        pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
        match = re.search(r'^version\s*=\s*"([^"]+)"', pyproject, re.MULTILINE)
        assert match, "version no encontrada en pyproject.toml"
        assert match.group(1) == _app_version()

    def test_version_mencionada_en_docs(self):
        version = _app_version()
        for rel in ("README.md", "docs/MANUAL_USUARIO.md", "docs/AUTO_UPDATE.md"):
            text = (ROOT / rel).read_text(encoding="utf-8")
            assert version in text, f"{rel} no menciona la versión {version}"

    def test_changelog_con_entrada_y_completa(self):
        version = _app_version()
        changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
        assert f"## [{version}]" in changelog, (
            f"CHANGELOG.md sin entrada ## [{version}]"
        )
        start = changelog.index(f"## [{version}]")
        resto = changelog[start:]
        fin = resto.find("## [", 1)
        seccion = resto[:fin] if fin != -1 else resto
        assert "(completar)" not in seccion, (
            f"CHANGELOG ## [{version}] con bullets sin completar"
        )

    def test_eps_habilitadas_con_homologador_valido(self):
        """Toda EPS habilitada resuelve su homologador desde HOMOLOGADOR_FILES.

        Evita el "homologador no encontrado" por typos entre eps_config y
        settings (fuente única). Las deshabilitadas no aplican.
        """
        conocidas = set(settings.HOMOLOGADOR_FILES.values())
        revisadas = 0
        for eps in EPS_CONFIG:
            if not getattr(eps, "enabled", False):
                continue
            ruta = getattr(eps, "homologador_path", None)
            if ruta is None:
                continue
            revisadas += 1
            assert ruta in conocidas, (
                f"EPS {eps.name}: homologador_path no viene de HOMOLOGADOR_FILES"
            )
        assert revisadas, "Ninguna EPS habilitada resolvió homologador"
