"""Bump de versión en un solo comando.

Uso:
    python bump.py 0.11.18 [--date YYYY-MM-DD] [--dry-run]

Hace el paso 1 de la rutina de releases:
  - APP_VERSION en app/config/settings.py
  - version en pyproject.toml
  - Nueva entrada ## [X.Y.Z] - fecha en CHANGELOG.md
  - Sincroniza README.md, docs/MANUAL_USUARIO.md, docs/AUTO_UPDATE.md
No commitea: revisa el diff y sigue con pytest + commit + build.
"""
import argparse
import re
import sys
from datetime import date
from pathlib import Path

# La consola Windows usa cp1252 y los prints con emojis revientan
# (UnicodeEncodeError). Fuerza UTF-8 con reemplazo seguro.
try:
    if sys.stdout is not None:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if sys.stderr is not None:
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

ROOT = Path(__file__).resolve().parent
SEMVER = re.compile(r"^\d+\.\d+\.\d+$")


def read_version() -> str:
    text = (ROOT / "app" / "config" / "settings.py").read_text(encoding="utf-8")
    match = re.search(r'^APP_VERSION\s*=\s*"([^"]+)"', text, re.MULTILINE)
    if not match:
        raise SystemExit("No se encontró APP_VERSION en settings.py")
    return match.group(1)


def replace(path: Path, old: str, new: str, dry_run: bool) -> int:
    text = path.read_text(encoding="utf-8")
    count = text.count(old)
    if count and not dry_run:
        path.write_text(text.replace(old, new), encoding="utf-8")
    print(f"  {path.relative_to(ROOT)}: {count} reemplazo(s)")
    return count


def insert_changelog(version: str, when: str, old_version: str, dry_run: bool) -> None:
    path = ROOT / "CHANGELOG.md"
    text = path.read_text(encoding="utf-8")
    if f"## [{version}]" in text:
        raise SystemExit(f"CHANGELOG.md ya tiene entrada ## [{version}]")
    entry = (
        f"## [{version}] - {when}\n\n"
        "### ✨ Nuevas Características\n"
        "- (completar)\n\n"
        "### 🐛 Correcciones\n"
        "- (completar)\n\n"
    )
    anchor = "---\n"
    idx = text.index(anchor) + len(anchor)
    new_text = text[:idx] + "\n" + entry + text[idx:]
    if not dry_run:
        path.write_text(new_text, encoding="utf-8")
    print(f"  CHANGELOG.md: entrada ## [{version}] agregada (completa los bullets)")


def main() -> int:
    parser = argparse.ArgumentParser(description="Bump de versión Glosaap")
    parser.add_argument("version", help="Nueva versión semver (ej. 0.11.18)")
    parser.add_argument("--date", default=str(date.today()), help="Fecha (default: hoy)")
    parser.add_argument("--dry-run", action="store_true", help="Muestra cambios sin aplicar")
    args = parser.parse_args()

    if not SEMVER.match(args.version):
        raise SystemExit("Versión inválida, usa semver X.Y.Z")
    current = read_version()
    if args.version == current:
        raise SystemExit(f"Ya estás en {current}")

    print(f"Bump {current} -> {args.version} (dry_run={args.dry_run})")
    replace(ROOT / "app" / "config" / "settings.py", f'APP_VERSION = "{current}"', f'APP_VERSION = "{args.version}"', args.dry_run)
    replace(ROOT / "pyproject.toml", f'version = "{current}"', f'version = "{args.version}"', args.dry_run)
    replace(ROOT / "README.md", current, args.version, args.dry_run)
    replace(ROOT / "docs" / "MANUAL_USUARIO.md", current, args.version, args.dry_run)
    replace(ROOT / "docs" / "AUTO_UPDATE.md", current, args.version, args.dry_run)
    insert_changelog(args.version, args.date, current, args.dry_run)

    if args.dry_run:
        print("Dry-run OK, nada modificado.")
    else:
        print("Listo. Sigue con: pytest, git add/commit/push, python build.py, python release.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())
