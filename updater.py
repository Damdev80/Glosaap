#!/usr/bin/env python3
"""
Glosaap Updater - Actualizador independiente

Este script se ejecuta como un proceso separado para actualizar
la aplicación principal sin conflictos de archivos en uso.

Flujo:
1. Recibe argumentos con la ubicación del archivo de actualización
2. Si el ZIP trae updater.exe nuevo y distinto, hace handoff
   auto-actualizable (Fase 5, técnica rename): lo extrae como
   updater_new.exe, lo lanza con --replace-self --takeover-from y
   termina (exit 0). El proceso nuevo espera al viejo, se copia
   sobre updater.exe y continúa la instalación normal re-enviando
   --update-file/--app-dir/--app-exe/--pid.
3. Espera a que el proceso principal termine
4. Crea backup de la versión anterior (opcional, --no-backup lo omite)
5. Extrae el ZIP a subdir temporal (sin tocar la app)
6. Verifica smoke del nuevo Glosaap.exe (existe + tamaño>0); si falla
   aborta ANTES de tocar la app
7. Solo entonces reemplaza los archivos de la aplicación
8. Ante cualquier fallo en extracción/verificación/reemplazo, restaura
   automáticamente desde el backup más reciente, MessageBox de error
   y exit code != 0
9. Reinicia la aplicación principal (un fallo aquí NO dispara rollback)

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
import hashlib
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


def find_latest_backup(app_dir: Path, logger: logging.Logger | None = None) -> Path | None:
    """
    Busca el backup más reciente disponible.

    Args:
        app_dir: Directorio de la aplicación
        logger: Logger para mensajes

    Returns:
        Ruta al backup más reciente o None si no hay ninguno
    """
    try:
        parent_dir = app_dir.parent
        if not parent_dir.exists():
            return None
        backups = sorted(
            [d for d in parent_dir.iterdir() if d.is_dir() and d.name.startswith("Glosaap_backup_")],
            key=lambda x: x.name,
            reverse=True,
        )
        if backups:
            if logger:
                logger.info(f"Backup más reciente encontrado: {backups[0]}")
            return backups[0]
        return None
    except Exception as e:
        if logger:
            logger.warning(f"Error buscando backups: {e}")
        return None


def verify_staged_update(source_dir: Path, logger: logging.Logger | None = None) -> bool:
    """
    Smoke check del update ya extraído al temporal (sin tocar la app).

    Verifica que el nuevo Glosaap.exe existe y tiene tamaño > 0.

    Args:
        source_dir: Directorio staging con los archivos nuevos
        logger: Logger para mensajes

    Returns:
        True si pasa el smoke check
    """
    candidate = source_dir / "Glosaap.exe"
    if not candidate.exists():
        # Fallback case-insensitive (zip puede traer distinta capitalización)
        found = None
        try:
            for item in source_dir.iterdir():
                if item.is_file() and item.name.lower() == "glosaap.exe":
                    found = item
                    break
        except OSError:
            found = None
        if found is None:
            if logger:
                logger.error(
                    f"Smoke check fallido: no se encontró Glosaap.exe en {source_dir}"
                )
            return False
        candidate = found

    try:
        size = candidate.stat().st_size
    except OSError as e:
        if logger:
            logger.error(f"Smoke check fallido: no se pudo leer {candidate}: {e}")
        return False

    if size <= 0:
        if logger:
            logger.error(f"Smoke check fallido: {candidate} tiene tamaño 0")
        return False

    if logger:
        logger.info(f"Smoke check OK: {candidate.name} ({size} bytes)")
    return True


def restore_from_backup(
    app_dir: Path, backup_dir: Path, logger: logging.Logger | None = None
) -> bool:
    """
    Restaura la app desde un backup (rollback).

    Copia el contenido del backup sobre app_dir, sin tocar updater.exe
    (puede estar en uso).

    Args:
        app_dir: Directorio de la aplicación a restaurar
        backup_dir: Directorio del backup origen
        logger: Logger para mensajes

    Returns:
        True si la restauración fue exitosa
    """
    if backup_dir is None or not backup_dir.exists():
        if logger:
            logger.error(f"Backup no disponible para rollback: {backup_dir}")
        return False

    if logger:
        logger.warning(f"Iniciando rollback desde: {backup_dir}")

    try:
        app_dir.mkdir(parents=True, exist_ok=True)
        for item in backup_dir.iterdir():
            if item.name.lower() in ("updater.exe", "updater_new.exe"):
                continue
            src = item
            dest = app_dir / item.name
            # Eliminar destino parcial/actual
            if dest.exists():
                if dest.is_dir():
                    shutil.rmtree(dest)
                else:
                    dest.unlink()
            if src.is_dir():
                shutil.copytree(src, dest)
            else:
                shutil.copy2(src, dest)
            if logger:
                logger.info(f"  Restaurado: {item.name}")
        if logger:
            logger.warning("Rollback completado")
        return True
    except Exception as e:
        if logger:
            logger.error(f"Rollback fallido: {e}")
            logger.error(traceback.format_exc())
        return False


def _cleanup_temp_dir(temp_dir: Path, logger: logging.Logger | None = None):
    """Elimina el directorio temporal de staging (best-effort)."""
    try:
        if temp_dir.exists():
            shutil.rmtree(temp_dir)
    except Exception as e:
        if logger:
            logger.warning(f"No se pudo limpiar temporal {temp_dir}: {e}")


def _app_looks_broken(app_dir: Path) -> bool:
    """
    Heurística rápida: la app está rota si no hay Glosaap.exe o está vacío.

    Usada como red de seguridad antes de decidir un rollback adicional
    en main() (evita downgrades innecesarios cuando el fallo ocurrió
    antes de tocar la app).
    """
    try:
        candidate = app_dir / "Glosaap.exe"
        if candidate.exists():
            try:
                return candidate.stat().st_size <= 0
            except OSError:
                return True
        # Fallback case-insensitive
        for item in app_dir.iterdir():
            if item.is_file() and item.name.lower() == "glosaap.exe":
                try:
                    return item.stat().st_size <= 0
                except OSError:
                    return True
        return True
    except OSError:
        return True


# ==================== AUTO-UPDATE DEL UPDATER (Fase 5) ====================
# Problema: extract_update() salta updater.exe porque está en ejecución
# (Windows lo bloquea), así que un bug del updater sería permanente hasta
# reinstalación manual. Técnica rename (solo stdlib):
#   viejo: detecta updater.exe nuevo y distinto en el ZIP -> lo extrae como
#          updater_new.exe al lado, lo lanza con --replace-self
#          --takeover-from <viejo> --takeover-pid <pid> y termina (exit 0
#          sin instalar el update).
#   nuevo: espera al viejo, se copia sobre updater.exe y continúa la
#          instalación normal con los args originales re-enviados.
# Si el takeover falla, se trata como fallo normal de Fase 2 (rollback).
# Sin terceros, solo stdlib. Riesgo conocido: el ZIP/updater no verifica
# firma, solo se descarga por HTTPS (ver build.py).

UPDATER_EXE_NAME = "updater.exe"
UPDATER_NEW_NAME = "updater_new.exe"
TAKEOVER_WAIT_TIMEOUT = 30
TAKEOVER_COPY_ATTEMPTS = 15


def _sha256_file(path: Path) -> str | None:
    """SHA-256 hex de un archivo (bloques de 1 MB). None si no se puede leer."""
    try:
        digest = hashlib.sha256()
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()
    except OSError:
        return None


def _sha256_bytes(data: bytes) -> str:
    """SHA-256 hex de bytes en memoria."""
    return hashlib.sha256(data).hexdigest()


def _get_own_binary_path() -> Path:
    """
    Ruta del binario/script actualmente en ejecución.

    En producción (PyInstaller, frozen) es sys.executable (updater.exe o
    updater_new.exe). En desarrollo (script) es sys.argv[0].
    El proceso nuevo (takeover) usa esto como origen para copiarse sobre
    el updater viejo.
    """
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve()
    argv0 = sys.argv[0] if sys.argv else ""
    if argv0 and argv0 != "-c":
        p = Path(argv0)
        if not p.is_absolute():
            p = Path.cwd() / p
        try:
            return p.resolve()
        except OSError:
            return p
    return Path(__file__).resolve()


def _resolve_takeover_target(app_dir: Path) -> Path:
    """
    Ruta del updater instalado a reemplazar (app_dir/updater.exe).

    Busca case-insensitive para preservar el nombre real en disco;
    si no existe, devuelve app_dir / "updater.exe" (la instalación
    normal lo creará, sin necesidad de takeover).
    """
    candidate = app_dir / UPDATER_EXE_NAME
    if candidate.exists():
        return candidate
    try:
        for item in app_dir.iterdir():
            if item.is_file() and item.name.lower() == UPDATER_EXE_NAME.lower():
                return item
    except OSError:
        pass
    return candidate


def _find_updater_entry(update_file: Path) -> str | None:
    """
    Busca el miembro del ZIP que corresponde a updater.exe.

    Compara por basename case-insensitive a cualquier profundidad
    (el ZIP de build.py trae un subdir raíz). Ignora updater_new.exe.

    Returns:
        arcname del miembro o None si el ZIP no trae updater.exe.
    """
    try:
        with zipfile.ZipFile(update_file, "r") as zf:
            for name in zf.namelist():
                if name.endswith("/"):
                    continue
                base = Path(name).name
                if base.lower() == UPDATER_NEW_NAME.lower():
                    continue
                if base.lower() == UPDATER_EXE_NAME.lower():
                    return name
    except (zipfile.BadZipFile, OSError):
        return None
    return None


def updater_needs_replace(
    takeover_target: Path,
    update_file: Path,
    logger: logging.Logger | None = None,
) -> tuple[bool, str | None]:
    """
    Decide si el updater instalado difiere del que trae el ZIP.

    Compara sha256 (con fallback a tamaño si el hash no se puede leer).
    Si el ZIP no trae updater.exe o el instalado no existe, no se necesita
    takeover (la instalación normal lo pondrá).

    Returns:
        (necesita_reemplazo, arcname_en_zip)
    """
    arcname = _find_updater_entry(update_file)
    if arcname is None:
        return False, None
    if not takeover_target.exists() or not takeover_target.is_file():
        if logger:
            logger.info("No hay updater.exe instalado, no se necesita takeover")
        return False, None
    try:
        with zipfile.ZipFile(update_file, "r") as zf:
            new_bytes = zf.read(arcname)
    except (zipfile.BadZipFile, OSError, KeyError) as e:
        if logger:
            logger.warning(f"No se pudo leer updater del ZIP para comparar: {e}")
        return False, None

    current_hash = _sha256_file(takeover_target)
    new_hash = _sha256_bytes(new_bytes)
    if current_hash is not None:
        if current_hash != new_hash:
            if logger:
                logger.info(
                    f"Updater distinto (sha256 {current_hash[:12]}... != "
                    f"{new_hash[:12]}...), se requiere takeover"
                )
            return True, arcname
        if logger:
            logger.info("Updater del ZIP idéntico (sha256), sin takeover")
        return False, arcname
    # Fallback tamaño+mtime si no se pudo hashear el instalado.
    try:
        if takeover_target.stat().st_size != len(new_bytes):
            if logger:
                logger.info("Updater con tamaño distinto, se requiere takeover")
            return True, arcname
    except OSError:
        return False, None
    return False, arcname


def _extract_single_entry(
    update_file: Path,
    arcname: str,
    dest: Path,
    logger: logging.Logger | None = None,
) -> bool:
    """Extrae un solo miembro del ZIP a dest (solo stdlib)."""
    try:
        dest.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(update_file, "r") as zf:
            data = zf.read(arcname)
        dest.write_bytes(data)
        if sys.platform != "win32":
            try:
                os.chmod(dest, 0o755)
            except OSError:
                pass
        if logger:
            logger.info(f"Updater nuevo extraído como: {dest} ({len(data)} bytes)")
        return True
    except (zipfile.BadZipFile, OSError, KeyError) as e:
        if logger:
            logger.error(f"No se pudo extraer {arcname} como {dest}: {e}")
        return False


def _looks_like_windows_pe(path: Path) -> bool:
    """True si el archivo empieza con firma MZ (binario PE Windows)."""
    try:
        with open(path, "rb") as f:
            return f.read(2) == b"MZ"
    except OSError:
        return False


def _launch_takeover_process(
    new_updater_path: Path,
    update_file: Path,
    app_dir: Path,
    app_exe: Path,
    pid: int,
    no_backup: bool,
    no_restart: bool,
    takeover_from: Path,
    takeover_pid: int,
    logger: logging.Logger | None = None,
) -> bool:
    """
    Lanza updater_new.exe con --replace-self re-enviando los args originales.

    En frozen se ejecuta el .exe directamente; en desarrollo (script) se
    lanza con sys.executable. Proceso detached para que sobreviva a la
    salida del viejo.
    """
    inner_args = [
        "--update-file", str(update_file),
        "--app-dir", str(app_dir),
        "--app-exe", str(app_exe),
        "--pid", str(pid),
    ]
    if no_backup:
        inner_args.append("--no-backup")
    if no_restart:
        inner_args.append("--no-restart")
    inner_args += [
        "--replace-self",
        "--takeover-from", str(takeover_from),
        "--takeover-pid", str(takeover_pid),
    ]
    if getattr(sys, "frozen", False):
        cmd = [str(new_updater_path)] + inner_args
    else:
        cmd = [sys.executable, str(new_updater_path)] + inner_args
    if logger:
        logger.info(f"Lanzando takeover: {' '.join(cmd)}")
    try:
        if sys.platform == "win32":
            subprocess.Popen(
                cmd,
                cwd=str(app_dir),
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS,
                close_fds=True,
            )
        else:
            subprocess.Popen(cmd, cwd=str(app_dir), start_new_session=True, close_fds=True)
        return True
    except Exception as e:
        if logger:
            logger.error(f"No se pudo lanzar takeover: {e}")
        return False


def _perform_takeover(
    takeover_from: Path,
    takeover_pid: int | None,
    logger: logging.Logger | None = None,
) -> bool:
    """
    Ejecuta el lado nuevo del takeover: espera al viejo y se copia sobre él.

    El origen es el propio binario en ejecución (_get_own_binary_path(),
    que es updater_new.exe tras el handoff). Reintenta ante el bloqueo de
    Windows y verifica por sha256 que la copia quedó idéntica.

    Returns:
        True si updater.exe quedó reemplazado.
    """
    if takeover_pid is not None:
        try:
            wait_for_process(takeover_pid, timeout=TAKEOVER_WAIT_TIMEOUT, logger=logger)
        except Exception as e:
            if logger:
                logger.warning(f"Error esperando al updater viejo ({takeover_pid}): {e}")

    src = _get_own_binary_path()
    dst = takeover_from
    try:
        if src.resolve() == dst.resolve():
            if logger:
                logger.info("Takeover: origen y destino son el mismo archivo, nada que hacer")
            return True
    except OSError:
        pass

    if not src.exists():
        if logger:
            logger.error(f"Takeover fallido: origen no existe: {src}")
        return False

    src_hash = _sha256_file(src)
    last_err: Exception | None = None
    for attempt in range(1, TAKEOVER_COPY_ATTEMPTS + 1):
        try:
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
            # Verificar copia idéntica por hash.
            if src_hash is not None:
                dst_hash = _sha256_file(dst)
                if dst_hash != src_hash:
                    raise OSError(f"verificación hash falló (src={src_hash[:12]} dst={dst_hash})")
            if logger:
                logger.info(f"Takeover OK: {src.name} -> {dst} (intento {attempt})")
            return True
        except (PermissionError, OSError) as e:
            last_err = e
            if logger:
                logger.warning(f"Takeover intento {attempt} bloqueado: {e}, reintentando...")
            time.sleep(1)
    if logger:
        logger.error(f"Takeover fallido tras {TAKEOVER_COPY_ATTEMPTS} intentos: {last_err}")
    return False


def maybe_handoff_self_update(
    update_file: Path,
    app_dir: Path,
    app_exe: Path,
    pid: int,
    no_backup: bool,
    no_restart: bool,
    logger: logging.Logger | None = None,
) -> bool:
    """
    Lado viejo del takeover (Fase 5).

    Si el ZIP trae updater.exe nuevo y distinto, lo extrae como
    updater_new.exe al lado, lo lanza con --replace-self y devuelve True
    (el llamador debe terminar con exit 0 sin instalar el update; el
    proceso nuevo continúa la instalación).

    Returns:
        True si el handoff se lanzó (terminar exit 0).
        False si no hacía falta o falló (continuar flujo legacy que salta
        updater.exe; no dispara rollback por sí solo).
    """
    if not update_file.exists():
        return False
    takeover_target = _resolve_takeover_target(app_dir)
    needs, arcname = updater_needs_replace(takeover_target, update_file, logger=logger)
    if not needs or arcname is None:
        return False

    dest_new = takeover_target.parent / UPDATER_NEW_NAME
    if logger:
        logger.info(f"Updater nuevo detectado, preparando handoff -> {dest_new}")
    if not _extract_single_entry(update_file, arcname, dest_new, logger=logger):
        if logger:
            logger.warning("Handoff abortado (no se pudo extraer updater_new), sigo con flujo legacy")
        return False

    # En desarrollo (script) un PE real no es ejecutable vía python; en ese
    # caso no hacemos handoff para no perder el update (sigo legacy).
    if not getattr(sys, "frozen", False) and _looks_like_windows_pe(dest_new):
        if logger:
            logger.warning(
                "Handoff omitido en modo script: el updater del ZIP es binario PE "
                "(solo ejecutable como .exe compilado). Sigo con flujo legacy."
            )
        try:
            dest_new.unlink()
        except OSError:
            pass
        return False

    if _launch_takeover_process(
        new_updater_path=dest_new,
        update_file=update_file,
        app_dir=app_dir,
        app_exe=app_exe,
        pid=pid,
        no_backup=no_backup,
        no_restart=no_restart,
        takeover_from=takeover_target,
        takeover_pid=os.getpid(),
        logger=logger,
    ):
        if logger:
            logger.info("Handoff lanzado, el updater nuevo continuará la instalación. Saliendo.")
        return True

    if logger:
        logger.warning("Handoff falló al lanzar, sigo con flujo legacy")
    return False


def _cleanup_updater_new(app_dir: Path, logger: logging.Logger | None = None):
    """
    Limpieza best-effort de updater_new.exe residual.

    No borra el binario en ejecución (Windows lo bloquea mientras corre el
    takeover); solo limpia restos de corridas anteriores.
    """
    try:
        candidate = app_dir / UPDATER_NEW_NAME
        own = _get_own_binary_path()
        try:
            if candidate.resolve() == own.resolve():
                return
        except OSError:
            pass
        if candidate.exists():
            candidate.unlink()
            if logger:
                logger.info(f"Restos de takeover eliminados: {candidate.name}")
    except OSError as e:
        if logger:
            logger.warning(f"No se pudo limpiar {UPDATER_NEW_NAME}: {e}")


def extract_update(
    update_file: Path,
    app_dir: Path,
    logger: logging.Logger | None = None,
    backup_dir: Path | None = None,
) -> bool:
    """
    Extrae los archivos de actualización con staging + smoke + rollback.

    Fases:
    1. Extrae el ZIP a un subdirectorio temporal (sin tocar la app).
    2. Verifica smoke del nuevo Glosaap.exe (existe + tamaño > 0).
       Si 1 o 2 fallan, aborta ANTES de tocar la app (no deja instalación
       parcial). No requiere backup para este caso.
    3. Solo entonces reemplaza los archivos en app_dir.
       Si 3 falla a medias echa rollback desde backup_dir (si se proveyó).

    Args:
        update_file: Ruta al archivo zip de actualización
        app_dir: Directorio destino de la aplicación
        logger: Logger para mensajes
        backup_dir: Backup a usar para rollback en fase de reemplazo.
            Si es None no se intenta restaurar (modo --no-backup).

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

    # Directorio temporal de staging (hermano de app_dir, no dentro)
    temp_extract = app_dir.parent / "glosaap_update_temp"

    # --- Preparar temporal limpio ---
    try:
        if temp_extract.exists():
            shutil.rmtree(temp_extract)
        temp_extract.mkdir(parents=True)
    except Exception as e:
        if logger:
            logger.error(f"No se pudo preparar directorio temporal: {e}")
        return False

    # --- FASE 1: extraer ZIP al temporal (sin tocar la app) ---
    try:
        if logger:
            logger.info("Extrayendo archivos al temporal...")
        with zipfile.ZipFile(update_file, 'r') as zip_ref:
            zip_ref.extractall(temp_extract)
    except zipfile.BadZipFile:
        if logger:
            logger.error("El archivo de actualización está corrupto")
        _cleanup_temp_dir(temp_extract, logger)
        return False
    except Exception as e:
        if logger:
            logger.error(f"Error extrayendo actualización al temporal: {e}")
            logger.error(traceback.format_exc())
        _cleanup_temp_dir(temp_extract, logger)
        return False

    # Encontrar el directorio raíz dentro del zip
    # (puede ser "Glosaap" o estar directamente en la raíz)
    try:
        extracted_items = list(temp_extract.iterdir())
    except Exception as e:
        if logger:
            logger.error(f"No se pudo listar el temporal: {e}")
        _cleanup_temp_dir(temp_extract, logger)
        return False

    if len(extracted_items) == 1 and extracted_items[0].is_dir():
        # El zip tiene un directorio raíz
        source_dir = extracted_items[0]
        if logger:
            logger.info(f"Directorio raíz del zip: {source_dir.name}")
    else:
        # Los archivos están directamente en la raíz
        source_dir = temp_extract

    # --- FASE 2: smoke check ANTES de tocar la app ---
    if not verify_staged_update(source_dir, logger=logger):
        # Aborto limpio: la app sigue intacta, solo limpiamos el temporal.
        _cleanup_temp_dir(temp_extract, logger)
        return False

    # --- FASE 3: reemplazo (único punto donde se toca la app) ---
    if logger:
        logger.info("Smoke OK. Reemplazando archivos...")

    try:
        for item in source_dir.iterdir():
            dest = app_dir / item.name

            # ⚠️ IMPORTANTE: Saltar updater.exe (está en uso).
            # Fase 5: el caso normal ya hizo takeover antes (el updater nuevo
            # en ejecución copió updater_new.exe sobre updater.exe), así que
            # este skip es un no-op idempotente. En el flujo legacy sin
            # takeover (p. ej. handoff omitido en modo script con PE real),
            # el updater viejo sigue corriendo y se conserva para la próxima.
            if item.name.lower() == "updater.exe":
                if logger:
                    logger.warning(f"Saltando {item.name} (en uso; Fase 5 ya lo reemplazó vía takeover si aplicaba)")
                continue
            # No tocar el resto del takeover en staging.
            if item.name.lower() == UPDATER_NEW_NAME.lower():
                if logger:
                    logger.info(f"Omitiendo {item.name} (artefacto de takeover, no parte de la app)")
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
        _cleanup_temp_dir(temp_extract, logger)

        if logger:
            logger.info("Extracción completada")

        return True

    except PermissionError as e:
        if logger:
            logger.error(f"Permisos insuficientes durante el reemplazo: {e}")
    except Exception as e:
        if logger:
            logger.error(f"Error reemplazando archivos: {e}")
            logger.error(traceback.format_exc())

    # --- Rollback: el reemplazo falló a medias ---
    _cleanup_temp_dir(temp_extract, logger)
    if backup_dir is not None and backup_dir.exists():
        if logger:
            logger.warning("Reemplazo fallido, intentando rollback automático...")
        if restore_from_backup(app_dir, backup_dir, logger=logger):
            if logger:
                logger.warning("Rollback exitoso tras fallo de reemplazo")
        else:
            if logger:
                logger.error("Rollback fallido: la instalación puede estar parcial")
    else:
        if logger:
            logger.warning(
                "Reemplazo fallido y no hay backup para rollback "
                "(modo --no-backup o backup no disponible)"
            )
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
    parser.add_argument(
        "--replace-self",
        action="store_true",
        help="Modo takeover (Fase 5): este proceso es updater_new.exe y debe "
             "reemplazar al updater viejo indicado en --takeover-from antes de "
             "continuar la instalación normal"
    )
    parser.add_argument(
        "--takeover-from",
        default=None,
        help="Ruta del updater viejo a reemplazar (solo con --replace-self)"
    )
    parser.add_argument(
        "--takeover-pid",
        type=int,
        default=None,
        help="PID del updater viejo a esperar antes de reemplazarlo "
             "(solo con --replace-self)"
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
    if args.replace_self:
        logger.info(f"  Modo takeover: replace-self desde {args.takeover_from} "
                    f"(pid viejo={args.takeover_pid})")
    logger.info("=" * 50)
    
    success = False
    backup_for_rollback: Path | None = None
    
    try:
        # 0a. Lado nuevo del takeover (Fase 5): reemplazar al updater viejo
        # antes de la instalación normal. Si falla, se aborta con rollback
        # normal de Fase 2 (el except de abajo lo maneja).
        if args.replace_self:
            if not args.takeover_from:
                raise Exception("--replace-self requiere --takeover-from <ruta>")
            takeover_from = Path(args.takeover_from)
            logger.info(f"Takeover: reemplazando {takeover_from} por el updater nuevo...")
            if not _perform_takeover(takeover_from, args.takeover_pid, logger=logger):
                raise Exception(
                    f"Takeover del updater falló (no se pudo reemplazar {takeover_from}). "
                    "Abortando con rollback normal."
                )
            logger.info("Takeover completado, continuando con la instalación normal...")

        # 0b. Lado viejo del takeover (Fase 5): si el ZIP trae updater.exe
        # nuevo y distinto, extraerlo como updater_new.exe, lanzarlo con
        # --replace-self y terminar (exit 0 sin instalar el update).
        # Se omite en modo --replace-self para evitar bucles.
        if not args.replace_self:
            if maybe_handoff_self_update(
                update_file, app_dir, app_exe, args.pid,
                args.no_backup, args.no_restart, logger=logger,
            ):
                logger.info("Handoff al updater nuevo exitoso (exit 0, sin instalar el update)")
                logger.info("=" * 50)
                return 0

        # 1. Esperar a que el proceso principal termine
        if not wait_for_process(args.pid, timeout=60, logger=logger):
            logger.warning("El proceso principal no terminó a tiempo, intentando continuar...")
            time.sleep(2)  # Esperar un poco más por si acaso
        
        # 2. Crear backup (opcional)
        # backup_for_rollback es el backup a usar si extracción/verificación/
        # reemplazo fallan. Con --no-backup queda en None (sin rollback,
        # pero extracción/verificación abortan antes de tocar la app).
        if not args.no_backup:
            fresh_backup = create_backup(app_dir, logger=logger)
            if fresh_backup is not None and fresh_backup.exists():
                backup_for_rollback = fresh_backup
            else:
                logger.warning("No se pudo crear backup, buscando backup previo para rollback...")
                fallback = find_latest_backup(app_dir, logger=logger)
                if fallback is not None:
                    logger.warning(f"Usando backup existente para rollback: {fallback}")
                    backup_for_rollback = fallback
                else:
                    logger.warning("Sin backup disponible: el rollback no será posible")
        else:
            logger.info("Omitiendo backup por flag --no-backup (sin rollback; "
                        "extracción/verificación abortan antes de tocar la app)")
        
        # 3. Extraer actualización (staging -> smoke -> reemplazo con rollback interno)
        if not extract_update(update_file, app_dir, logger=logger, backup_dir=backup_for_rollback):
            # extract_update ya intentó rollback en fase de reemplazo.
            # Red de seguridad: solo restaurar de nuevo si la app quedó rota
            # (evita downgrades cuando el fallo fue antes del reemplazo y la
            # app sigue intacta).
            if backup_for_rollback is not None and backup_for_rollback.exists():
                if _app_looks_broken(app_dir):
                    logger.warning("La app quedó en estado parcial, rollback de seguridad...")
                    restore_from_backup(app_dir, backup_for_rollback, logger=logger)
                else:
                    logger.info("La app sigue intacta (fallo antes del reemplazo), "
                                "no se requiere rollback adicional")
            raise Exception("Error al extraer la actualización")
        
        # 4. Limpiar backups antiguos
        cleanup_old_backups(app_dir, keep_count=2, logger=logger)
        
        # 5. Eliminar archivo de actualización
        cleanup_update_file(update_file, logger=logger)

        # 5b. Limpiar updater_new.exe residual de un takeover previo
        # (best-effort; si este proceso ES updater_new.exe, Windows lo
        # bloquea y se conserva hasta la próxima corrida).
        _cleanup_updater_new(app_dir, logger=logger)
        
        # 6. Reiniciar aplicación
        # NOTA: un fallo aquí NO dispara rollback (los archivos ya están bien).
        if not args.no_restart:
            time.sleep(1)  # Pequeña pausa antes de reiniciar
            if not restart_application(app_exe, app_dir, logger=logger):
                raise Exception("Error al reiniciar la aplicación")
        
        success = True
        logger.info("Actualización completada exitosamente")
        
    except Exception as e:
        logger.error(f"Error durante la actualización: {e}")
        logger.error(traceback.format_exc())

        # Red de seguridad final: si la excepción escapó sin pasar por el
        # chequeo de arriba (p. ej. error inesperado) y la app está rota,
        # intentar rollback desde el backup más reciente disponible.
        try:
            effective_backup = backup_for_rollback
            if (
                not success
                and effective_backup is None
                and not args.no_backup
            ):
                effective_backup = find_latest_backup(app_dir, logger=logger)
            if (
                effective_backup is not None
                and effective_backup.exists()
                and _app_looks_broken(app_dir)
            ):
                logger.warning("Rollback final de seguridad...")
                restore_from_backup(app_dir, effective_backup, logger=logger)
        except Exception as rb_e:
            logger.error(f"Error en rollback final: {rb_e}")
        
        # Mostrar mensaje de error al usuario (exit code != 0 abajo)
        show_error_message(
            "Error de actualización",
            f"No se pudo completar la actualización:\n\n{str(e)}\n\n"
            f"Se intentó restaurar la versión anterior. "
            f"Si la app no inicia, restaura manualmente desde "
            f"Glosaap_backup_* o descarga la última versión desde GitHub."
        )
    
    logger.info("=" * 50)
    logger.info(f"Updater finalizado. Éxito: {success}")
    logger.info("=" * 50)
    
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
