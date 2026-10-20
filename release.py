import argparse
import hashlib
import os
import sys
import requests
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

# RIESGO CONOCIDO (supply-chain, documentado aquí porque docs/** está fuera
# del alcance de este script): el updater hoy solo descarga por HTTPS y no
# verifica firma. Como mitigación (contrato update-system Fase 1, lado
# publicación), este script publica <zip>.sha256 junto al ZIP e incluye la
# línea "SHA256: <hash>" en el body del release para que el updater verifique
# el hash. NUNCA publiques un ZIP sin su checksum (fail-closed).

# Cargar variables de entorno ...
# GITHUB_TOKEN viene de `.env` (requiere python-dotenv). No hay `.env.example`
# en el repo a propósito: nunca commitees el token. Formato del .env local:
#   GITHUB_TOKEN=ghp_...
load_dotenv()

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
REPO = "Damdev80/Glosaap"


def require_token():
    """Exige GITHUB_TOKEN solo al publicar (no al importar ni con --dry-run)."""
    token = os.getenv("GITHUB_TOKEN") or GITHUB_TOKEN
    if not token:
        print("❌ Error: GITHUB_TOKEN no configurado.")
        print("   Crea un archivo `.env` junto a release.py con:")
        print("     GITHUB_TOKEN=ghp_...")
        print("   No commitees ese archivo.")
        sys.exit(1)
    return token


def parse_args(argv=None):
    """Argumentos CLI (con --help; --dry-run no publica ni exige token)."""
    parser = argparse.ArgumentParser(
        description="Publica la release de Glosaap en GitHub (ZIP + .sha256, fail-closed sin checksum)."
    )
    parser.add_argument(
        "--version",
        default=None,
        help="Forzar versión (por defecto: APP_VERSION de app/config/settings.py).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Muestra versión, ZIP, SHA256 y notas sin crear el release.",
    )
    return parser.parse_args(argv)


def compute_sha256(file_path):
    """Calcula el hash SHA-256 hex de un archivo (lectura por bloques de 1 MB)."""
    digest = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def find_zip_for_version(version):
    """Localiza release/Glosaap_v<version>_<ts>.zip.

    Si hay varios ZIP timestamped, usa el más reciente (no zip_files[0]
    a ciegas) y lo informa. Devuelve None si no hay ninguno.
    """
    zip_pattern = f"release/Glosaap_v{version}_*.zip"
    zip_files = sorted(
        Path(".").glob(zip_pattern),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    if not zip_files:
        return None
    if len(zip_files) > 1:
        print(f"⚠️  Hay {len(zip_files)} ZIP candidatos para v{version}; usando el más reciente:")
        for candidate in zip_files:
            print(f"     - {candidate.name}")
    return zip_files[0]


def ensure_sha256_file(zip_file):
    """Garantiza el checksum `<zip>.sha256` (fail-closed).

    Si no existe, lo genera desde el ZIP. Si existe pero no coincide con el
    ZIP actual, lo regenera. Devuelve (ruta_sha256: Path, hash: str).
    Falla con mensaje claro si el ZIP no existe (no publicar sin checksum).
    """
    zip_file = Path(zip_file)
    if not zip_file.exists():
        print(f"❌ No se encontró el ZIP: {zip_file}")
        print("   Ejecuta primero: python build.py")
        sys.exit(1)
    sha_file = zip_file.with_name(zip_file.name + ".sha256")
    actual = compute_sha256(zip_file)
    if sha_file.exists():
        existing = sha_file.read_text(encoding="utf-8").strip().split()
        if existing and existing[0] == actual:
            print(f"🔐 Checksum existente verificado: {sha_file.name}")
            return sha_file, actual
        print(f"⚠️  {sha_file.name} no coincide con el ZIP actual; regenerando...")
    sha_file.write_text(f"{actual}  {zip_file.name}\n", encoding="utf-8")
    print(f"🔐 SHA-256: {actual}")
    print(f"📄 Checksum escrito: {sha_file}")
    return sha_file, actual

def get_version():
    """Obtener versión de settings.py"""
    settings_path = Path(__file__).parent / "app" / "config" / "settings.py"
    with open(settings_path) as f:
        for line in f:
            if 'APP_VERSION = ' in line:
                return line.split('"')[1]
    return "0.0.0"

def get_changelog():
    """Leer CHANGELOG.md si existe"""
    changelog_path = Path(__file__).parent / "CHANGELOG.md"
    if changelog_path.exists():
        with open(changelog_path, encoding='utf-8') as f:
            return f.read()
    return None

def get_git_log():
    """Obtener últimos commits para generar changelog"""
    import subprocess
    try:
        result = subprocess.run(
            ["git", "log", "--oneline", "-10"],
            capture_output=True,
            text=True
        )
        return result.stdout
    except:
        return None

def generate_release_notes(version):
    """Generar notas de release completas"""
    changelog = get_changelog()
    
    if changelog:
        # Extraer solo la sección de la versión actual
        lines = changelog.split('\n')
        start_idx = None
        end_idx = None
        
        for i, line in enumerate(lines):
            if f"## [{version}]" in line:
                start_idx = i
            elif start_idx is not None and line.startswith("## ["):
                end_idx = i
                break
        
        if start_idx is not None:
            end_idx = end_idx or len(lines)
            return '\n'.join(lines[start_idx:end_idx]).strip()
    
    # Si no hay changelog, generar desde git log
    git_log = get_git_log()
    if git_log:
        return f"## Release {version}\n\n### Commits\n{git_log}"
    
    return f"Release v{version}"

def create_release(version=None, dry_run=False):
    """Crear release en GitHub usando API REST"""
    token = None if dry_run else require_token()
    version = version or get_version()

    print(f"\n{'='*60}")
    print(f"🚀 CREANDO RELEASE v{version}" + (" (DRY-RUN, no publica)" if dry_run else ""))
    print(f"{'='*60}\n")

    # Checksum fail-closed: se resuelve ANTES de crear el release para poder
    # incluir "SHA256: <hash>" en el body y subir ambos assets después.
    zip_file = find_zip_for_version(version)
    if not zip_file:
        print(f"❌ No se encontró release/Glosaap_v{version}_*.zip")
        print("   Ejecuta primero: python build.py")
        sys.exit(1)
    sha_file, sha_hash = ensure_sha256_file(zip_file)
    print(f"   ZIP: {zip_file.name}")
    print(f"   SHA: {sha_file.name}")

    # Headers con autenticación
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28"
    }

    # Generar notas de release (+ línea de checksum para verificación)
    release_notes = generate_release_notes(version)
    release_notes += f"\n\nSHA256: {sha_hash}"

    if dry_run:
        print("📝 Notas del release (dry-run):")
        print("-" * 60)
        print(release_notes)
        print("-" * 60)
        print("✅ Dry-run OK: ZIP + .sha256 listos, nada publicado.")
        return {"version": version, "zip": str(zip_file),
                "sha256_file": str(sha_file), "sha256": sha_hash,
                "notes": release_notes}
    
    # Datos del release
    data = {
        "tag_name": f"v{version}",
        "name": f"Glosaap v{version}",
        "body": release_notes,
        "draft": False,
        "prerelease": False
    }
    
    # Crear release
    print(f"📝 Generando notas de release...")
    print(f"📡 Conectando a GitHub...")
    
    url = f"https://api.github.com/repos/{REPO}/releases"
    response = requests.post(url, json=data, headers=headers)
    
    if response.status_code == 201:
        release = response.json()
        print(f"\n✅ Release v{version} creado exitosamente")
        print(f"📎 URL: {release['html_url']}\n")
        
        # Subir archivos ZIP + .sha256
        upload_asset(release['upload_url'], zip_file, sha_file, headers)
        
        print(f"\n{'='*60}")
        print(f"✨ ¡RELEASE COMPLETADO CON ÉXITO!")
        print(f"{'='*60}")
        print(f"📦 Versión: v{version}")
        print(f"🔗 URL: {release['html_url']}")
        print(f"{'='*60}\n")
        
    else:
        print(f"❌ Error: {response.status_code}")
        try:
            error_data = response.json()
            error_msg = error_data.get('message', 'Desconocido')
            print(f"   Mensaje: {error_msg}")
            if 'errors' in error_data:
                print(f"   Errores: {error_data['errors']}")
        except:
            print(f"   Respuesta: {response.text}")
        
        # Si ya existe, ofrecer opciones
        if response.status_code == 422:
            print(f"\n⚠️  Posible conflicto (release ya existe).")
            print(f"   Opciones:")
            print(f"   1. Incrementa la versión en settings.py")
            print(f"   2. Elimina el release desde GitHub")
        
        sys.exit(1)

def upload_file(upload_url, file_path, content_type, headers):
    """Sube un archivo individual al release. Devuelve True si tuvo éxito."""
    file_path = Path(file_path)
    file_size_mb = file_path.stat().st_size / (1024 * 1024)

    print(f"\n📤 Subiendo asset...")
    print(f"   Archivo: {file_path.name}")
    print(f"   Tamaño: {file_size_mb:.2f} MB")

    # Preparar headers para upload
    upload_headers = headers.copy()
    upload_headers["Content-Type"] = content_type

    # URL limpia (sin {?name,label})
    upload_url_clean = upload_url.split("{")[0]

    with open(file_path, "rb") as f:
        response = requests.post(
            f"{upload_url_clean}?name={file_path.name}",
            data=f,
            headers=upload_headers
        )

    if response.status_code in [200, 201]:
        print(f"✅ Asset subido correctamente: {file_path.name}")
        return True
    print(f"⚠️  Error al subir {file_path.name}: {response.json()}")
    return False


def upload_asset(upload_url, zip_file, sha_file, headers):
    """Subir archivos ZIP + .sha256 al release (fail-closed sin checksum)."""
    zip_file = Path(zip_file)
    sha_file = Path(sha_file)

    if not zip_file.exists():
        print(f"❌ No se encontró el ZIP: {zip_file}")
        print("   Ejecuta primero: python build.py")
        sys.exit(1)
    if not sha_file.exists():
        print(f"❌ No se encontró el checksum: {sha_file}")
        print("   Ejecuta primero: python build.py (genera el .sha256)")
        sys.exit(1)

    ok_zip = upload_file(upload_url, zip_file, "application/zip", headers)
    ok_sha = upload_file(upload_url, sha_file, "text/plain", headers)

    if not (ok_zip and ok_sha):
        print("❌ Falló la subida de uno o más assets.")
        sys.exit(1)
    print("✅ ZIP + .sha256 publicados.")


if __name__ == "__main__":
    args = parse_args()
    create_release(version=args.version, dry_run=args.dry_run)
