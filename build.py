#!/usr/bin/env python3
"""
Script de build automático para Glosaap
Crea ejecutable portable usando PyInstaller
"""
import os
import sys
import shutil
import subprocess
import zipfile
from pathlib import Path
from datetime import datetime

# Configuración
APP_NAME = "Glosaap"
BUILD_DIR = "build"
DIST_DIR = "dist"
FINAL_DIR = "release"

def print_step(message):
    """Imprime un paso con formato bonito"""
    print(f"\n🔧 {message}")
    print("=" * 50)

def check_requirements():
    """Verifica que PyInstaller esté disponible"""
    try:
        import PyInstaller
        print("✅ PyInstaller encontrado")
        return True
    except ImportError:
        print("❌ PyInstaller no encontrado")
        print("Instala con: pip install pyinstaller")
        return False

def clean_directories():
    """Limpia directorios de builds anteriores"""
    print_step("Limpiando directorios anteriores")
    
    dirs_to_clean = [BUILD_DIR, DIST_DIR, FINAL_DIR, "__pycache__"]
    
    for dir_name in dirs_to_clean:
        if os.path.exists(dir_name):
            shutil.rmtree(dir_name)
            print(f"🗑️  Eliminado: {dir_name}")
    
    # Limpiar archivos spec
    for spec_file in Path(".").glob("*.spec"):
        spec_file.unlink()
        print(f"🗑️  Eliminado: {spec_file}")

def get_version():
    """Obtiene la versión actual de settings.py"""
    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location("settings", "app/config/settings.py")
        settings = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(settings)
        return settings.APP_VERSION
    except Exception as e:
        print(f"⚠️  Error obteniendo versión: {e}")
        return "unknown"

def build_executable():
    """Construye el ejecutable con PyInstaller"""
    print_step("Construyendo ejecutable")
    
    version = get_version()
    print(f"📋 Versión detectada: {version}")
    
    # Comando PyInstaller
    cmd = [
        "pyinstaller",
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
        print("✅ Build exitoso")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Error en build:")
        print(f"STDOUT: {e.stdout}")
        print(f"STDERR: {e.stderr}")
        return False

def create_portable_package():
    """Crea un paquete portable con todos los recursos"""
    print_step("Creando paquete portable")
    
    version = get_version()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    package_name = f"{APP_NAME}_v{version}_{timestamp}"
    package_dir = os.path.join(FINAL_DIR, package_name)
    
    # Crear directorio de release
    os.makedirs(package_dir, exist_ok=True)
    
    # Copiar ejecutable
    exe_source = os.path.join(DIST_DIR, f"{APP_NAME}.exe")
    exe_dest = os.path.join(package_dir, f"{APP_NAME}.exe")
    
    if os.path.exists(exe_source):
        shutil.copy2(exe_source, exe_dest)
        print(f"📦 Ejecutable copiado: {APP_NAME}.exe")
    else:
        print(f"❌ No se encontró ejecutable: {exe_source}")
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
    
    # Mostrar información final
    zip_size = os.path.getsize(zip_path) / (1024 * 1024)
    print(f"📊 Tamaño final: {zip_size:.1f} MB")
    
    return zip_path

def main():
    """Función principal del build"""
    print("🚀 GLOSAAP BUILD AUTOMÁTICO")
    print("=" * 60)
    
    # Verificar requisitos
    if not check_requirements():
        return False
    
    try:
        # 1. Limpiar
        clean_directories()
        
        # 2. Build
        if not build_executable():
            return False
        
        # 3. Empaquetar
        zip_path = create_portable_package()
        if not zip_path:
            return False
        
        # 4. Éxito
        print_step("BUILD COMPLETADO")
        print(f"✅ Ejecutable listo: {zip_path}")
        print(f"📁 Abre la carpeta: {os.path.abspath(FINAL_DIR)}")
        
        # Abrir carpeta en explorer
        if sys.platform == 'win32':
            subprocess.run(f'explorer "{os.path.abspath(FINAL_DIR)}"', shell=True)
        
        return True
        
    except Exception as e:
        print(f"\n❌ ERROR INESPERADO: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()
    if success:
        print(f"\n🎉 ¡Build exitoso! Archivo listo para distribuir.")
    else:
        print(f"\n💥 Build falló. Revisa los errores arriba.")
    
    input("\nPresiona Enter para salir...")
