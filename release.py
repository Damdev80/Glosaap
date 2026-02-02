import os
import sys
import requests
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

# Cargar variables de entorno ...
load_dotenv()

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
REPO = "Damdev80/Glosaap"

if not GITHUB_TOKEN:
    print("❌ Error: GITHUB_TOKEN no configurado en .env")
    sys.exit(1)

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

def create_release():
    """Crear release en GitHub usando API REST"""
    version = get_version()
    
    print(f"\n{'='*60}")
    print(f"🚀 CREANDO RELEASE v{version}")
    print(f"{'='*60}\n")
    
    # Headers con autenticación
    headers = {
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28"
    }
    
    # Generar notas de release
    release_notes = generate_release_notes(version)
    
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
        
        # Subir archivo ZIP
        upload_asset(release['upload_url'], version, headers)
        
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

def upload_asset(upload_url, version, headers):
    """Subir archivo ZIP al release"""
    zip_pattern = f"release/Glosaap_v{version}_*.zip"
    zip_files = list(Path(".").glob(zip_pattern))
    
    if not zip_files:
        print(f"⚠️  No se encontró {zip_pattern}")
        print(f"   Ejecuta primero: python build.py")
        return
    
    zip_file = zip_files[0]
    file_size_mb = zip_file.stat().st_size / (1024 * 1024)
    
    print(f"\n📤 Subiendo asset...")
    print(f"   Archivo: {zip_file.name}")
    print(f"   Tamaño: {file_size_mb:.2f} MB")
    
    # Preparar headers para upload
    upload_headers = headers.copy()
    upload_headers["Content-Type"] = "application/zip"
    
    # URL limpia (sin {?name,label})
    upload_url_clean = upload_url.split("{")[0]
    
    with open(zip_file, "rb") as f:
        response = requests.post(
            f"{upload_url_clean}?name={zip_file.name}",
            data=f,
            headers=upload_headers
        )
    
    if response.status_code in [200, 201]:
        print(f"✅ Asset subido correctamente")
    else:
        print(f"⚠️  Error al subir: {response.json()}")

if __name__ == "__main__":
    create_release()
