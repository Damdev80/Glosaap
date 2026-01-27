#!/usr/bin/env python3
"""
Glosaap Updater - Actualizador independiente

Este script se ejecuta como un proceso separado para actualizar
la aplicación principal sin conflictos de archivos en uso.

Flujo:
1. Recibe argumentos con la ubicación del archivo de actualización
2. Espera a que el proceso principal termine
3. Extrae los archivos del zip
4. Crea backup de la versión anterior (opcional)
5. Reemplaza los archivos de la aplicación
6. Reinicia la aplicación principal

Uso:
    updater.exe --update-file <path> --app-dir <dir> --app-exe <exe> --pid <pid>

Este archivo se compila a updater.exe usando PyInstaller.
"""
import os
import sys
import time
import shutil
import zipfile
import argparse
import subprocess
import logging
import traceback
from pathlib import Path
from datetime import datetime

# ==================== CONFIGURACIÓN DE LOGGING ====================

def setup_logging(app_dir: Path) -> logging.Logger:
    """Configura el sistema de logging del updater"""
    log_dir = app_dir / "logs"
    log_dir.mkdir(exist_ok=True)
    
    log_file = log_dir / f"updater_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8'),
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    return logging.getLogger("GlosaapUpdater")


# ==================== FUNCIONES PRINCIPALES ====================

def wait_for_process(pid: int, timeout: int = 60, logger: logging.Logger | None = None) -> bool:
    """
    Espera a que un proceso termine.
    
    Args:
        pid: ID del proceso a esperar
        timeout: Tiempo máximo de espera en segundos
        logger: Logger para mensajes
        
    Returns:
        True si el proceso terminó, False si timeout
    """
    if logger:
        logger.info(f"Esperando a que termine el proceso {pid}...")
    
    start_time = time.time()
    
    while time.time() - start_time < timeout:
        try:
            # En Windows, verificamos si el proceso existe
            if sys.platform == 'win32':
                import ctypes
                kernel32 = ctypes.windll.kernel32
                SYNCHRONIZE = 0x00100000
                handle = kernel32.OpenProcess(SYNCHRONIZE, False, pid)
                
                if handle == 0:
                    # El proceso ya no existe
                    if logger:
                        logger.info(f"Proceso {pid} ha terminado")
                    return True
                
                kernel32.CloseHandle(handle)
            else:
                # En Unix, usamos os.kill con señal 0
                os.kill(pid, 0)
            
            time.sleep(0.5)
        except (OSError, ProcessLookupError):
            # El proceso no existe
            if logger:
                logger.info(f"Proceso {pid} ha terminado")
            return True
        except Exception as e:
            if logger:
                logger.warning(f"Error verificando proceso: {e}")
            time.sleep(0.5)
    
    if logger:
        logger.warning(f"Timeout esperando proceso {pid}")
    return False


def create_backup(app_dir: Path, logger: logging.Logger | None = None) -> Path | None:
    """
    Crea un backup de la aplicación actual.
    
    Args:
        app_dir: Directorio de la aplicación
        logger: Logger para mensajes
        
    Returns:
        Ruta al directorio de backup
    """
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_dir = app_dir.parent / f"Glosaap_backup_{timestamp}"
    
    if logger:
        logger.info(f"Creando backup en: {backup_dir}")
    
    try:
        # Copiar archivos importantes (no todo para ahorrar espacio)
        files_to_backup = ['Glosaap.exe', '_internal']
        
        backup_dir.mkdir(exist_ok=True)
        
        for item in files_to_backup:
            source = app_dir / item
            if source.exists():
                dest = backup_dir / item
                if source.is_dir():
                    shutil.copytree(source, dest)
                else:
                    shutil.copy2(source, dest)
                if logger:
                    logger.info(f"  Backup: {item}")
        
        if logger:
            logger.info("Backup completado")
        
        return backup_dir
    except Exception as e:
        if logger:
            logger.warning(f"No se pudo crear backup: {e}")
        return None


def extract_update(update_file: Path, app_dir: Path, logger: logging.Logger | None = None) -> bool:
    """
    Extrae los archivos de actualización.
    
    Args:
        update_file: Ruta al archivo zip de actualización
        app_dir: Directorio destino de la aplicación
        logger: Logger para mensajes
        
    Returns:
        True si se extrajo correctamente
    """
    if logger:
        logger.info(f"Extrayendo actualización desde: {update_file}")
        logger.info(f"Destino: {app_dir}")
    
    if not update_file.exists():
        if logger:
            logger.error(f"Archivo de actualización no encontrado: {update_file}")
        return False
    
    try:
        # Crear directorio temporal para extracción
        temp_extract = app_dir.parent / "glosaap_update_temp"
        if temp_extract.exists():
            shutil.rmtree(temp_extract)
        temp_extract.mkdir()
        
        if logger:
            logger.info("Extrayendo archivos...")
        
        with zipfile.ZipFile(update_file, 'r') as zip_ref:
            zip_ref.extractall(temp_extract)
        
        # Encontrar el directorio raíz dentro del zip
        # (puede ser "Glosaap" o estar directamente en la raíz)
        extracted_items = list(temp_extract.iterdir())
        
        if len(extracted_items) == 1 and extracted_items[0].is_dir():
            # El zip tiene un directorio raíz
            source_dir = extracted_items[0]
            if logger:
                logger.info(f"Directorio raíz del zip: {source_dir.name}")
        else:
            # Los archivos están directamente en la raíz
            source_dir = temp_extract
        
        # Copiar archivos a la aplicación
        if logger:
            logger.info("Reemplazando archivos...")
        
        for item in source_dir.iterdir():
            dest = app_dir / item.name
            
            # ⚠️ IMPORTANTE: Saltar updater.exe (está en uso)
            # Se actualizará en la próxima ejecución
            if item.name.lower() == "updater.exe":
                if logger:
                    logger.warning(f"Saltando {item.name} (está en uso, se actualizará en próxima ejecución)")
                continue
            
            # Eliminar destino si existe
            if dest.exists():
                if dest.is_dir():
                    # Intentar eliminar directorio con reintentos
                    for attempt in range(3):
                        try:
                            shutil.rmtree(dest)
                            break
                        except PermissionError:
                            if logger:
                                logger.warning(f"Permiso denegado para {dest}, reintentando...")
                            time.sleep(1)
                else:
                    for attempt in range(3):
                        try:
                            dest.unlink()
                            break
                        except PermissionError:
                            if logger:
                                logger.warning(f"Permiso denegado para {dest}, reintentando...")
                            time.sleep(1)
            
            # Copiar nuevo archivo/directorio
            if item.is_dir():
                shutil.copytree(item, dest)
            else:
                shutil.copy2(item, dest)
            
            if logger:
                logger.info(f"  Actualizado: {item.name}")
        
        # Limpiar directorio temporal
        try:
            shutil.rmtree(temp_extract)
        except Exception:
            pass
        
        if logger:
            logger.info("Extracción completada")
        
        return True
        
    except zipfile.BadZipFile:
        if logger:
            logger.error("El archivo de actualización está corrupto")
        return False
    except PermissionError as e:
        if logger:
            logger.error(f"Permisos insuficientes: {e}")
        return False
    except Exception as e:
        if logger:
            logger.error(f"Error extrayendo actualización: {e}")
            logger.error(traceback.format_exc())
        return False


def restart_application(app_exe: Path, app_dir: Path, logger: logging.Logger | None = None) -> bool:
    """
    Reinicia la aplicación principal.
    
    Args:
        app_exe: Ruta al ejecutable de la aplicación
        app_dir: Directorio de la aplicación
        logger: Logger para mensajes
        
    Returns:
        True si se inició correctamente
    """
    # Determinar la ruta completa del ejecutable
    if app_exe.is_absolute():
        exe_path = app_exe
    else:
        exe_path = app_dir / app_exe
    
    if logger:
        logger.info(f"Reiniciando aplicación: {exe_path}")
    
    if not exe_path.exists():
        # Buscar el ejecutable en el directorio
        for item in app_dir.iterdir():
            if item.suffix == '.exe' and 'Glosaap' in item.name:
                exe_path = item
                if logger:
                    logger.info(f"Encontrado ejecutable: {exe_path}")
                break
    
    if not exe_path.exists():
        if logger:
            logger.error(f"No se encontró el ejecutable: {exe_path}")
        return False
    
    try:
        # Iniciar la aplicación como proceso independiente
        if sys.platform == 'win32':
            subprocess.Popen(
                [str(exe_path)],
                cwd=str(app_dir),
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS,
                close_fds=True
            )
        else:
            subprocess.Popen(
                [str(exe_path)],
                cwd=str(app_dir),
                start_new_session=True,
                close_fds=True
            )
        
        if logger:
            logger.info("Aplicación reiniciada exitosamente")
        
        return True
        
    except Exception as e:
        if logger:
            logger.error(f"Error reiniciando aplicación: {e}")
        return False


def cleanup_old_backups(app_dir: Path, keep_count: int = 2, logger: logging.Logger | None = None):
    """
    Elimina backups antiguos manteniendo solo los más recientes.
    
    Args:
        app_dir: Directorio de la aplicación
        keep_count: Número de backups a mantener
        logger: Logger para mensajes
    """
    parent_dir = app_dir.parent
    backups = sorted(
        [d for d in parent_dir.iterdir() if d.is_dir() and d.name.startswith("Glosaap_backup_")],
        key=lambda x: x.name,
        reverse=True
    )
    
    for backup in backups[keep_count:]:
        try:
            shutil.rmtree(backup)
            if logger:
                logger.info(f"Backup antiguo eliminado: {backup.name}")
        except Exception as e:
            if logger:
                logger.warning(f"No se pudo eliminar backup {backup.name}: {e}")


def cleanup_update_file(update_file: Path, logger: logging.Logger | None = None):
    """
    Elimina el archivo de actualización después de instalar.
    
    Args:
        update_file: Ruta al archivo de actualización
        logger: Logger para mensajes
    """
    try:
        if update_file.exists():
            update_file.unlink()
            if logger:
                logger.info(f"Archivo de actualización eliminado: {update_file}")
    except Exception as e:
        if logger:
            logger.warning(f"No se pudo eliminar archivo de actualización: {e}")


def show_error_message(title: str, message: str):
    """Muestra un mensaje de error al usuario (Windows)"""
    if sys.platform == 'win32':
        try:
            import ctypes
            MB_OK = 0x0
            MB_ICONERROR = 0x10
            ctypes.windll.user32.MessageBoxW(0, message, title, MB_OK | MB_ICONERROR)
        except Exception:
            print(f"{title}: {message}")
    else:
        print(f"{title}: {message}")


def show_success_message(title: str, message: str):
    """Muestra un mensaje de éxito al usuario (Windows)"""
    if sys.platform == 'win32':
        try:
            import ctypes
            MB_OK = 0x0
            MB_ICONINFORMATION = 0x40
            ctypes.windll.user32.MessageBoxW(0, message, title, MB_OK | MB_ICONINFORMATION)
        except Exception:
            print(f"{title}: {message}")
    else:
        print(f"{title}: {message}")


# ==================== PUNTO DE ENTRADA ====================

def main():
    """Punto de entrada principal del actualizador"""
    parser = argparse.ArgumentParser(
        description="Glosaap Updater - Actualizador de la aplicación"
    )
    parser.add_argument(
        "--update-file", "-u",
        required=True,
        help="Ruta al archivo zip de actualización"
    )
    parser.add_argument(
        "--app-dir", "-d",
        required=True,
        help="Directorio de la aplicación"
    )
    parser.add_argument(
        "--app-exe", "-e",
        required=True,
        help="Nombre del ejecutable principal"
    )
    parser.add_argument(
        "--pid", "-p",
        type=int,
        required=True,
        help="PID del proceso principal a esperar"
    )
    parser.add_argument(
        "--no-backup",
        action="store_true",
        help="No crear backup antes de actualizar"
    )
    parser.add_argument(
        "--no-restart",
        action="store_true",
        help="No reiniciar la aplicación después de actualizar"
    )
    
    args = parser.parse_args()
    
    # Convertir rutas a Path
    update_file = Path(args.update_file)
    app_dir = Path(args.app_dir)
    app_exe = Path(args.app_exe)
    
    # Configurar logging
    logger = setup_logging(app_dir)
    
    logger.info("=" * 50)
    logger.info("Glosaap Updater iniciado")
    logger.info(f"  Update file: {update_file}")
    logger.info(f"  App dir: {app_dir}")
    logger.info(f"  App exe: {app_exe}")
    logger.info(f"  PID: {args.pid}")
    logger.info("=" * 50)
    
    success = False
    
    try:
        # 1. Esperar a que el proceso principal termine
        if not wait_for_process(args.pid, timeout=60, logger=logger):
            logger.warning("El proceso principal no terminó a tiempo, intentando continuar...")
            time.sleep(2)  # Esperar un poco más por si acaso
        
        # 2. Crear backup (opcional)
        if not args.no_backup:
            backup_dir = create_backup(app_dir, logger=logger)
            if not backup_dir:
                logger.warning("No se pudo crear backup, continuando sin backup...")
        
        # 3. Extraer actualización
        if not extract_update(update_file, app_dir, logger=logger):
            raise Exception("Error al extraer la actualización")
        
        # 4. Limpiar backups antiguos
        cleanup_old_backups(app_dir, keep_count=2, logger=logger)
        
        # 5. Eliminar archivo de actualización
        cleanup_update_file(update_file, logger=logger)
        
        # 6. Reiniciar aplicación
        if not args.no_restart:
            time.sleep(1)  # Pequeña pausa antes de reiniciar
            if not restart_application(app_exe, app_dir, logger=logger):
                raise Exception("Error al reiniciar la aplicación")
        
        success = True
        logger.info("Actualización completada exitosamente")
        
    except Exception as e:
        logger.error(f"Error durante la actualización: {e}")
        logger.error(traceback.format_exc())
        
        # Mostrar mensaje de error al usuario
        show_error_message(
            "Error de actualización",
            f"No se pudo completar la actualización:\n\n{str(e)}\n\n"
            f"Por favor, descarga manualmente la última versión desde GitHub."
        )
    
    logger.info("=" * 50)
    logger.info(f"Updater finalizado. Éxito: {success}")
    logger.info("=" * 50)
    
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
