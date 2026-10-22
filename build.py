#!/usr/bin/env python3
"""
Script de build automático para Glosaap
Crea ejecutable portable usando PyInstaller
"""
import argparse
import hashlib
import os
import sys
import shutil
import subprocess
import zipfile
from pathlib import Path
from datetime import datetime

# La consola Windows usa cp1252 y los prints con emojis revientan
# (UnicodeEncodeError), incluido en runners de CI. Fuerza UTF-8 seguro.
try:
    if sys.stdout is not None:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if sys.stderr is not None:
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

# Si no está en el venv, redirigir al venv
if not hasattr(sys, 'real_prefix') and not (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix):
    # No estamos en un venv, redirigir
    venv_python = Path(__file__).parent / ".venv" / "Scripts" / "python.exe"
    if venv_python.exists():
        print(f"🔄 Ejecutando desde venv: {venv_python}")
        result = subprocess.run([str(venv_python), __file__] + sys.argv[1:])
        sys.exit(result.returncode)

# Configuración
APP_NAME = "Glosaap"
BUILD_DIR = "build"
DIST_DIR = "dist"
FINAL_DIR = "release"

# Specs trackeados en git: clean_directories() NUNCA debe borrarlos.
# Solo se eliminan .spec generados (no trackeados) de corridas de PyInstaller.
TRACKED_SPECS = frozenset({"glosaap.spec", "updater.spec"})

# RIESGO CONOCIDO (supply-chain, documentado aquí porque docs/** está fuera
# del alcance de este script): el updater hoy solo descarga por HTTPS y no
# verifica firma. Como mitigación, este build publica <zip>.sha256 junto al
# ZIP para que el updater verifique el hash (contrato update-system Fase 1).

def compute_sha256(file_path):
    """Calcula el hash SHA-256 hex de un archivo (lectura por bloques de 1 MB)."""
    digest = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_sha256_file(zip_path):
    """Genera al lado del ZIP su checksum.

    Crea `<nombre-zip>.sha256` con formato estilo sha256sum:
    `"<sha256>  <nombre-zip>"`. Devuelve la ruta del .sha256.
    """
    zip_path = Path(zip_path)
    sha256_hash = compute_sha256(zip_path)
    sha_path = zip_path.with_name(zip_path.name + ".sha256")
    sha_path.write_text(f"{sha256_hash}  {zip_path.name}\n", encoding="utf-8")
    print(f"🔐 SHA-256: {sha256_hash}")
    print(f"📄 Checksum escrito: {sha_path}")
    return str(sha_path)


def parse_args(argv=None):
    """Argumentos CLI (con --help; sin input() bloqueante para CI)."""
    parser = argparse.ArgumentParser(
        description="Build de Glosaap: genera release/Glosaap_vX.Y.Z_<ts>.zip + .sha256"
    )
    parser.add_argument(
        "-y", "--yes", "--non-interactive",
        dest="non_interactive",
        action="store_true",
        help="Modo no interactivo: no pide Enter al final ni abre el explorer (para CI).",
    )
    parser.add_argument(
        "--skip-clean",
        action="store_true",
        help="No limpiar directorios de builds anteriores.",
    )
    parser.add_argument(
        "--skip-open",
        action="store_true",
        help="No abrir la carpeta release/ en el explorer al finalizar.",
    )
    return parser.parse_args(argv)

def print_step(message):
    """Imprime un paso con formato bonito"""
    print(f"\n🔧 {message}")
    print("=" * 50)

def check_requirements():
    """Verifica que PyInstaller esté disponible"""
    try:
        import PyInstaller
        print(f"✅ PyInstaller encontrado ({PyInstaller.__version__})")
    except ImportError:
        print("❌ PyInstaller no encontrado")
        print("Instala con: pip install pyinstaller")
        return False

    # Precondición del empaquetado: el viewer Flet debe estar instalado en
    # el entorno de build, o `--collect-all flet_desktop` no recolecta nada
    # (silencioso) y el exe muere en el preflight. Falla rápido y claro.
    try:
        import flet.version as _fv
        import flet_desktop.version as _fdv

        print(f"✅ flet {_fv.version} + flet_desktop {_fdv.version}")
        if _fdv.version and _fdv.version != _fv.version:
            print(
                f"❌ Versiones flet/flet_desktop no coinciden "
                f"({_fv.version} vs {_fdv.version}): el exe caería al "
                f"fallback de pip. Fija ambas a la misma versión."
            )
            return False
    except ImportError as e:
        print(f"❌ flet_desktop no instalado en el entorno de build: {e}")
        print("   Instala con: pip install -r requirements.txt")
        return False
    return True

def clean_directories():
    """Limpia directorios de builds anteriores"""
    print_step("Limpiando directorios anteriores")
    
    dirs_to_clean = [BUILD_DIR, f"{BUILD_DIR}_updater", DIST_DIR, "__pycache__"]
    
    for dir_name in dirs_to_clean:
        if os.path.exists(dir_name):
            shutil.rmtree(dir_name)
            print(f"🗑️  Eliminado: {dir_name}")
    
    # Limpiar archivos spec GENERADOS (nunca los trackeados en git).
    # Bug conocido: antes se borraba todo *.spec, incluyendo glosaap.spec
    # y updater.spec que sí están versionados (ver git ls-files "*.spec").
    for spec_file in Path(".").glob("*.spec"):
        if spec_file.name in TRACKED_SPECS:
            print(f"⏭️  Conservado (trackeado en git): {spec_file}")
            continue
        spec_file.unlink()
        print(f"🗑️  Eliminado: {spec_file}")

def get_version():
    """Obtiene la versión actual de settings.py"""
    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location("settings", "app/config/settings.py")
        if spec and spec.loader:
            settings = importlib.util.module_from_spec(spec)
        if spec and spec.loader:
            spec.loader.exec_module(settings)
        return settings.APP_VERSION
    except Exception as e:
        print(f"⚠️  Error obteniendo versión: {e}")
        return "unknown"

def build_main_executable():
    """Construye el ejecutable principal con PyInstaller"""
    print_step("Construyendo ejecutable principal")
    
    version = get_version()
    print(f"📋 Versión detectada: {version}")
    
    # Comando PyInstaller para ejecutable principal
    # (via python -m para no depender del PATH)
    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--onefile",                    # Un solo archivo ejecutable
        "--windowed",                   # Sin ventana de consola
        "--name", APP_NAME,             # Nombre del ejecutable
        "--distpath", DIST_DIR,         # Directorio de salida
        "--workpath", BUILD_DIR,        # Directorio de trabajo
        "--clean",                      # Limpiar cache
        "--noconfirm",                  # No pedir confirmación
        
        # Incluir directorios necesarios
        "--add-data", "app;app",
        "--add-data", "assets;assets",

        # Flet busca el viewer en el paquete flet_desktop (import dinámico
        # que PyInstaller no detecta). Sin esto, flet intenta instalarlo
        # con `sys.executable -m pip install`, que en el exe congelado
        # RE-EJECUTA Glosaap.exe en bucle infinito (fork bomb).
        "--collect-all", "flet_desktop",
        
        # Archivo principal
        "main.py"
    ]
    
    # Agregar icono si existe
    icon_path = "assets/icons/app_logo.ico"
    if os.path.exists(icon_path):
        cmd.extend(["--icon", icon_path])
        print(f"📦 Icono incluido: {icon_path}")
    
    print(f"▶️  Ejecutando: {' '.join(cmd)}")
    
    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        print("✅ Build del ejecutable principal exitoso")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Error en build del ejecutable principal:")
        print(f"STDOUT: {e.stdout}")
        print(f"STDERR: {e.stderr}")
        return False

def build_updater():
    """Construye el updater.exe por separado"""
    print_step("Construyendo updater")
    
    # Comando PyInstaller para updater
    # (via python -m para no depender del PATH)
    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--onefile",                    # Un solo archivo ejecutable
        "--console",                    # Con ventana de consola para debugging
        "--name", "updater",            # Nombre del ejecutable
        "--distpath", DIST_DIR,         # Directorio de salida
        "--workpath", f"{BUILD_DIR}_updater",  # Directorio de trabajo separado
        "--clean",                      # Limpiar cache
        "--noconfirm",                  # No pedir confirmación
        
        # Archivo del updater
        "updater.py"
    ]
    
    print(f"▶️  Ejecutando: {' '.join(cmd)}")
    
    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        print("✅ Build del updater exitoso")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Error en build del updater:")
        print(f"STDOUT: {e.stdout}")
        print(f"STDERR: {e.stderr}")
        return False

def build_executables():
    """Construye ambos ejecutables"""
    if not build_main_executable():
        return False
    
    if not build_updater():
        return False
    
    return True

def create_portable_package():
    """Crea un paquete portable con todos los recursos"""
    print_step("Creando paquete portable")
    
    version = get_version()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    package_name = f"{APP_NAME}_v{version}_{timestamp}"
    package_dir = os.path.join(FINAL_DIR, package_name)
    
    # Crear directorio de release
    os.makedirs(package_dir, exist_ok=True)
    
    # Copiar ejecutable principal
    exe_source = os.path.join(DIST_DIR, f"{APP_NAME}.exe")
    exe_dest = os.path.join(package_dir, f"{APP_NAME}.exe")
    
    if os.path.exists(exe_source):
        shutil.copy2(exe_source, exe_dest)
        print(f"📦 Ejecutable principal copiado: {APP_NAME}.exe")
    else:
        print(f"❌ No se encontró ejecutable principal: {exe_source}")
        return None
    
    # Copiar updater
    updater_source = os.path.join(DIST_DIR, "updater.exe")
    updater_dest = os.path.join(package_dir, "updater.exe")
    
    if os.path.exists(updater_source):
        shutil.copy2(updater_source, updater_dest)
        print(f"📦 Updater copiado: updater.exe")
    else:
        print(f"❌ No se encontró updater: {updater_source}")
        return None
    
    # Crear archivo README
    readme_content = f"""🚀 Glosaap v{version}
================================

📥 INSTALACIÓN:
1. Extrae todos los archivos a una carpeta
2. Ejecuta Glosaapp.exe
3. ¡Listo!

📋 REQUISITOS:
- Windows 10/11
- Conexión a internet (para actualizaciones)
- Acceso a \\\\MINERVA\\Cartera\\GLOSAAP (red corporativa)

🔄 ACTUALIZACIONES:
La aplicación verifica automáticamente las actualizaciones desde GitHub.

📞 SOPORTE:
- Repositorio: https://github.com/Damdev80/Glosaap
- Versión: {version}
- Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

💡 NOTAS:
- Primera ejecución puede tardar unos segundos
- Los archivos se procesan en \\\\MINERVA\\Cartera\\GLOSAAP\\REPOSITORIO DE RESULTADOS
"""
    
    with open(os.path.join(package_dir, "README.txt"), "w", encoding="utf-8") as f:
        f.write(readme_content)
    
    print(f"📄 README creado")
    
    # Crear ZIP
    zip_path = f"{package_dir}.zip"
    
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(package_dir):
            for file in files:
                file_path = os.path.join(root, file)
                arc_name = os.path.relpath(file_path, FINAL_DIR)
                zipf.write(file_path, arc_name)
    
    print(f"🗜️  ZIP creado: {zip_path}")

    # Checksum SHA-256 del ZIP (contrato update-system Fase 1, lado publicación):
    # genera release/Glosaap_vX.Y.Z_<ts>.zip.sha256 al lado del ZIP y loguea el hash.
    # release.py lo sube junto al ZIP e incluye "SHA256: <hash>" en el body.
    write_sha256_file(zip_path)

    # Mostrar información final
    zip_size = os.path.getsize(zip_path) / (1024 * 1024)
    print(f"📊 Tamaño final: {zip_size:.1f} MB")
    
    return zip_path

def main(args=None):
    """Función principal del build"""
    if args is None:
        args = parse_args([])
    print("🚀 GLOSAAP BUILD AUTOMÁTICO")
    print("=" * 60)

    # Verificar requisitos
    if not check_requirements():
        return False

    try:
        # 1. Limpiar (salvo --skip-clean)
        if not args.skip_clean:
            clean_directories()
        else:
            print_step("Limpieza omitida (--skip-clean)")

        # 2. Build
        if not build_executables():
            return False

        # 3. Empaquetar
        zip_path = create_portable_package()
        if not zip_path:
            return False

        # 4. Éxito
        print_step("BUILD COMPLETADO")
        print(f"✅ Ejecutable listo: {zip_path}")
        print(f"📁 Abre la carpeta: {os.path.abspath(FINAL_DIR)}")

        # Abrir carpeta en explorer (solo local interactivo, nunca en CI)
        if sys.platform == 'win32' and not args.non_interactive and not args.skip_open:
            subprocess.run(f'explorer "{os.path.abspath(FINAL_DIR)}"', shell=True)

        return True
        
    except Exception as e:
        print(f"\n❌ ERROR INESPERADO: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    args = parse_args()
    success = main(args)
    if success:
        print(f"\n🎉 ¡Build exitoso! Archivo listo para distribuir.")
    else:
        print(f"\n💥 Build falló. Revisa los errores arriba.")

    # Bug conocido: input() bloqueaba CI. Solo pausar en terminal interactiva
    # y fuera de modo no-interactivo.
    if not args.non_interactive and sys.stdin.isatty():
        input("\nPresiona Enter para salir...")

    # Fail-closed en CI: salir != 0 si el build falló (antes el workflow
    # marcaba el paso como exitoso aunque no hubiera ZIP).
    sys.exit(0 if success else 1)
