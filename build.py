"""
Script de construcción para Glosaap

Este script compila la aplicación principal y el updater,
y prepara la distribución final.

Uso:
    python build.py
    
    o con argumentos:
    python build.py --clean      # Limpia directorios antes de compilar
    python build.py --app-only   # Solo compila la app principal
    python build.py --updater-only  # Solo compila el updater
"""
import os
import sys
import shutil
import subprocess
import argparse
from pathlib import Path

# Directorio raíz del proyecto
ROOT_DIR = Path(__file__).parent


def clean_build():
    """Limpia los directorios de build"""
    print("🧹 Limpiando directorios de build...")
    
    dirs_to_clean = ['build', 'dist']
    for dir_name in dirs_to_clean:
        dir_path = ROOT_DIR / dir_name
        if dir_path.exists():
            print(f"   Eliminando {dir_name}/")
            shutil.rmtree(dir_path)
    
    # Limpiar archivos .spec generados automáticamente (mantener los manuales)
    # Solo limpiar si existen archivos temporales de PyInstaller
    
    print("   ✅ Limpieza completada")


def build_app():
    """Compila la aplicación principal"""
    print("\n📦 Compilando Glosaap...")
    
    spec_file = ROOT_DIR / "glosaap.spec"
    if not spec_file.exists():
        print("   ❌ Error: glosaap.spec no encontrado")
        return False
    
    result = subprocess.run(
        [sys.executable, "-m", "PyInstaller", str(spec_file)],
        cwd=str(ROOT_DIR),
        capture_output=True,
        text=True
    )
    
    if result.returncode != 0:
        print("   ❌ Error compilando Glosaap:")
        print(result.stderr)
        return False
    
    # Verificar que se creó el ejecutable
    exe_path = ROOT_DIR / "dist" / "Glosaap" / "Glosaap.exe"
    if exe_path.exists():
        print(f"   ✅ Glosaap.exe creado exitosamente")
        return True
    else:
        print("   ❌ Error: Glosaap.exe no fue creado")
        return False


def build_updater():
    """Compila el updater"""
    print("\n🔄 Compilando Updater...")
    
    spec_file = ROOT_DIR / "updater.spec"
    if not spec_file.exists():
        print("   ❌ Error: updater.spec no encontrado")
        return False
    
    result = subprocess.run(
        [sys.executable, "-m", "PyInstaller", str(spec_file)],
        cwd=str(ROOT_DIR),
        capture_output=True,
        text=True
    )
    
    if result.returncode != 0:
        print("   ❌ Error compilando updater:")
        print(result.stderr)
        return False
    
    # Verificar que se creó el ejecutable
    exe_path = ROOT_DIR / "dist" / "updater.exe"
    if exe_path.exists():
        print(f"   ✅ updater.exe creado exitosamente")
        return True
    else:
        print("   ❌ Error: updater.exe no fue creado")
        return False


def copy_updater_to_dist():
    """Copia updater.exe al directorio de distribución de Glosaap"""
    print("\n📋 Copiando updater a distribución...")
    
    src = ROOT_DIR / "dist" / "updater.exe"
    dst = ROOT_DIR / "dist" / "Glosaap" / "updater.exe"
    
    if not src.exists():
        print(f"   ❌ Error: {src} no existe")
        return False
    
    if not dst.parent.exists():
        print(f"   ❌ Error: directorio {dst.parent} no existe")
        return False
    
    shutil.copy2(src, dst)
    print(f"   ✅ updater.exe copiado a dist/Glosaap/")
    return True


def create_release_zip():
    """Crea el archivo zip para la release de GitHub"""
    print("\n📦 Creando archivo de release...")
    
    dist_dir = ROOT_DIR / "dist" / "Glosaap"
    if not dist_dir.exists():
        print("   ❌ Error: directorio de distribución no existe")
        return False
    
    # Leer versión desde settings
    try:
        sys.path.insert(0, str(ROOT_DIR))
        from app.config.settings import APP_VERSION
    except ImportError:
        APP_VERSION = "1.0.0"
    
    zip_name = f"Glosaap_v{APP_VERSION}"
    zip_path = ROOT_DIR / "dist" / zip_name
    
    # Crear zip
    shutil.make_archive(str(zip_path), 'zip', str(dist_dir.parent), "Glosaap")
    
    final_zip = zip_path.with_suffix('.zip')
    if final_zip.exists():
        size_mb = final_zip.stat().st_size / (1024 * 1024)
        print(f"   ✅ {final_zip.name} creado ({size_mb:.1f} MB)")
        return True
    else:
        print("   ❌ Error creando archivo zip")
        return False


def main():
    parser = argparse.ArgumentParser(description="Script de construcción de Glosaap")
    parser.add_argument("--clean", action="store_true", help="Limpiar antes de compilar")
    parser.add_argument("--app-only", action="store_true", help="Solo compilar app principal")
    parser.add_argument("--updater-only", action="store_true", help="Solo compilar updater")
    parser.add_argument("--no-zip", action="store_true", help="No crear archivo zip")
    
    args = parser.parse_args()
    
    print("=" * 50)
    print("🚀 Glosaap Build Script")
    print("=" * 50)
    
    # Limpiar si se solicita
    if args.clean:
        clean_build()
    
    success = True
    
    # Compilar según argumentos
    if args.updater_only:
        success = build_updater()
    elif args.app_only:
        success = build_app()
    else:
        # Compilar todo
        success = build_app()
        if success:
            success = build_updater()
        if success:
            success = copy_updater_to_dist()
        if success and not args.no_zip:
            success = create_release_zip()
    
    print("\n" + "=" * 50)
    if success:
        print("✅ Build completado exitosamente!")
        print("\nArchivos generados:")
        print("  - dist/Glosaap/Glosaap.exe")
        print("  - dist/Glosaap/updater.exe")
        if not args.no_zip:
            print("  - dist/Glosaap_v*.zip (listo para GitHub Release)")
    else:
        print("❌ Build falló. Revisa los errores arriba.")
    print("=" * 50)
    
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
