#!/usr/bin/env python3
"""
Test del sistema de actualizaciones de Glosaap
"""
import sys
import os

# Agregar el directorio raíz del proyecto al path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from app.service.update_service import UpdateService
from app.config.settings import APP_VERSION, GITHUB_REPO

def test_updates():
    """Prueba el sistema de actualizaciones"""
    print(f"🔍 Probando actualizaciones...")
    print(f"📋 Versión actual: {APP_VERSION}")
    print(f"🔗 Repositorio: {GITHUB_REPO}")
    print(f"=" * 50)
    
    try:
        # Crear servicio de actualización
        update_service = UpdateService(
            current_version=APP_VERSION,
            github_repo=GITHUB_REPO
        )
        
        print("🌐 Verificando conexión con GitHub...")
        
        # Verificar actualizaciones
        release = update_service.check_for_updates()
        
        if release:
            print(f"✅ ¡Actualización disponible!")
            print(f"   📦 Versión: {release.version}")
            print(f"   📝 Nombre: {release.name}")
            print(f"   📁 Archivo: {release.asset_name}")
            print(f"   📊 Tamaño: {release.size_mb:.1f} MB")
            print(f"   🔗 URL: {release.download_url}")
            print(f"\n📄 Changelog:")
            print(f"{release.changelog[:300]}...")
        else:
            print("✅ No hay actualizaciones disponibles")
            print("📱 La aplicación está actualizada")
        
    except Exception as e:
        print(f"❌ Error en verificación:")
        print(f"   🔍 Tipo: {type(e).__name__}")
        print(f"   💬 Mensaje: {str(e)}")
        import traceback
        print(f"\n🔧 Traceback:")
        traceback.print_exc()

if __name__ == "__main__":
    test_updates()