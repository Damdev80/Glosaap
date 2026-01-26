# Sistema de Actualización Automática - Glosaap

## Descripción General

Este documento describe el sistema de actualización automática implementado para Glosaap. El sistema permite que la aplicación verifique, descargue e instale actualizaciones desde GitHub Releases de forma segura y automatizada.

## Arquitectura

### Componentes

```
┌─────────────────────────────────────────────────────────────┐
│                    GLOSAAP (app principal)                  │
│                                                             │
│  ┌──────────────────┐    ┌─────────────────────────────┐   │
│  │  UpdateService   │───▶│  GitHub Releases API        │   │
│  │  (update_service)│    │  - Verificar versiones      │   │
│  │                  │◀───│  - Descargar assets         │   │
│  └────────┬─────────┘    └─────────────────────────────┘   │
│           │                                                 │
│           ▼                                                 │
│  ┌──────────────────┐                                      │
│  │   UpdateDialog   │    UI de notificación y              │
│  │  (update_dialog) │    descarga                          │
│  └────────┬─────────┘                                      │
│           │                                                 │
│           ▼                                                 │
│  ┌──────────────────┐                                      │
│  │   Lanzar         │    Inicia updater.exe con args       │
│  │   Updater        │    Cierra la app principal           │
│  └──────────────────┘                                      │
│                                                             │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│                  UPDATER (proceso separado)                 │
│                                                             │
│  1. Espera que Glosaap.exe termine                         │
│  2. Crea backup de la versión actual                       │
│  3. Extrae el ZIP descargado                               │
│  4. Reemplaza archivos                                     │
│  5. Reinicia Glosaap.exe                                   │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### Archivos del Sistema

| Archivo | Ubicación | Descripción |
|---------|-----------|-------------|
| `update_service.py` | `app/service/` | Lógica de verificación y descarga |
| `update_dialog.py` | `app/ui/components/` | Diálogos de UI para actualizaciones |
| `updater.py` | Raíz | Script del actualizador independiente |
| `updater.spec` | Raíz | Configuración PyInstaller para updater.exe |
| `settings.py` | `app/config/` | Configuración (versión, repo, etc.) |

## Flujo de Actualización

### 1. Verificación al Inicio

```
[App Inicia]
     │
     ▼
[AUTO_UPDATE_CONFIG.check_on_startup == True?]
     │
     ├── Sí ──▶ [Verificar en segundo plano]
     │                    │
     │                    ▼
     │          [¿Hay nueva versión?]
     │                    │
     │                    ├── Sí ──▶ [Mostrar diálogo]
     │                    │
     │                    └── No ──▶ [Continuar silenciosamente]
     │
     └── No ──▶ [Continuar sin verificar]
```

### 2. Verificación Manual

El usuario puede verificar actualizaciones manualmente haciendo clic en el indicador de versión (`v1.0.0`) en la esquina inferior izquierda del Dashboard.

### 3. Proceso de Actualización

```
[Usuario acepta actualización]
           │
           ▼
[Descargar ZIP desde GitHub Release]
           │
           ▼
[Lanzar updater.exe con argumentos:
  --update-file: ruta al ZIP
  --app-dir: directorio de la app
  --app-exe: Glosaap.exe
  --pid: PID actual]
           │
           ▼
[Cerrar Glosaap.exe]
           │
           ▼
[updater.exe:
  1. Espera que termine el PID
  2. Crea backup
  3. Extrae ZIP
  4. Reemplaza archivos
  5. Reinicia Glosaap.exe]
```

## Configuración

### settings.py

```python
# Versión actual (actualizar manualmente en cada release)
APP_VERSION = "1.0.0"

# Repositorio de GitHub
GITHUB_REPO = "tu-organizacion/glosaap"

# Configuración de auto-actualización
AUTO_UPDATE_CONFIG = {
    "enabled": True,              # Habilitar verificación automática
    "check_on_startup": True,     # Verificar al iniciar
    "check_interval_hours": 24,   # Intervalo (no implementado aún)
    "show_changelog": True,       # Mostrar changelog
    "create_backup": True,        # Crear backup antes de actualizar
}
```

### Cambiar el Repositorio

Para apuntar a tu propio repositorio:

1. Editar `app/config/settings.py`:
   ```python
   GITHUB_REPO = "mi-organizacion/mi-repo"
   ```

2. Opcionalmente, editar `app/service/update_service.py`:
   ```python
   GITHUB_REPO = "mi-organizacion/mi-repo"
   ```

## Estructura de GitHub Release

Para que el sistema funcione correctamente, las releases de GitHub deben seguir esta estructura:

### Tag de Versión

- Formato: `v1.0.0` o `1.0.0`
- Seguir semver (MAJOR.MINOR.PATCH)

### Assets

- Incluir un archivo ZIP con la distribución completa
- Nombre sugerido: `Glosaap_v1.0.0.zip`
- El ZIP debe contener:
  ```
  Glosaap/
  ├── Glosaap.exe
  ├── updater.exe
  ├── _internal/
  └── assets/
  ```

### Changelog

- Usar Markdown en el body de la release
- Será mostrado al usuario en el diálogo de actualización

### Ejemplo de Release

```
Tag: v1.1.0
Nombre: Versión 1.1.0 - Nueva funcionalidad X

Body (Markdown):
## Novedades

- ✨ Nueva funcionalidad X
- 🐛 Corrección de bug Y
- 🚀 Mejora de rendimiento Z

## Cambios

- Actualizado componente A
- Mejorada interfaz de B
```

## Compilación

### Compilar Todo

```bash
python build.py
```

Esto genera:
- `dist/Glosaap/Glosaap.exe`
- `dist/Glosaap/updater.exe`
- `dist/Glosaap_v1.0.0.zip` (listo para GitHub Release)

### Compilar Solo la App

```bash
python build.py --app-only
```

### Compilar Solo el Updater

```bash
python build.py --updater-only
```

### Limpiar y Recompilar

```bash
python build.py --clean
```

## Manejo de Errores

### Sin Conexión

Si no hay conexión a internet, el sistema:
1. Registra el error en el log
2. Si es verificación automática: continúa silenciosamente
3. Si es verificación manual: muestra mensaje de error

### Descarga Fallida

Si la descarga falla:
1. Muestra mensaje de error
2. Ofrece botón "Reintentar"
3. Registra detalles en el log

### Permisos Insuficientes

El updater:
1. Intenta escribir con reintentos (3 intentos)
2. Si falla, muestra diálogo de error con instrucciones
3. Mantiene el backup para recuperación manual

### Proceso Principal No Termina

Si el proceso principal no termina en 60 segundos:
1. El updater continúa de todos modos
2. Registra advertencia en el log
3. Puede haber conflictos de archivos

## Logs

### Ubicación

- App principal: `%TEMP%/glosaap/glosaap.log`
- Updater: `<app_dir>/logs/updater_YYYYMMDD_HHMMSS.log`

### Formato

```
2026-01-26 10:30:00 [INFO] Verificando actualizaciones para tu-org/glosaap...
2026-01-26 10:30:01 [INFO] Versión actual: 1.0.0, Versión remota: 1.1.0
2026-01-26 10:30:01 [INFO] Actualización disponible: 1.1.0 (25.5 MB)
```

## Comparación de Versiones

El sistema usa comparación semver:

```python
# Ejemplos
is_update_available("1.0.0", "1.1.0")  # True
is_update_available("2.0.0", "1.9.9")  # False
is_update_available("1.0.0", "1.0.0")  # False
is_update_available("1.0.0-beta", "1.0.0")  # True (release > prerelease)
```

## Seguridad

### HTTPS

Todas las conexiones a GitHub usan HTTPS con verificación SSL.

### Sin Ejecución Arbitraria

El sistema solo:
1. Descarga desde URLs de `github.com`
2. Extrae archivos ZIP a ubicaciones predefinidas
3. Ejecuta el único ejecutable conocido (Glosaap.exe)

### Backups Automáticos

Antes de cada actualización se crea un backup en:
```
<parent_dir>/Glosaap_backup_YYYYMMDD_HHMMSS/
```

## Solución de Problemas

### "No se encontró el actualizador"

- Verificar que `updater.exe` está en el mismo directorio que `Glosaap.exe`
- Recompilar con `python build.py`

### "Error al descargar"

- Verificar conexión a internet
- Verificar que el release en GitHub tiene assets descargables
- Revisar logs para más detalles

### "Permisos insuficientes"

- Ejecutar como administrador
- Verificar que la aplicación no está en `Program Files` (requiere permisos especiales)

### La actualización no se aplica

1. Verificar logs del updater en `<app_dir>/logs/`
2. Verificar que el ZIP tiene la estructura correcta
3. Restaurar desde backup si es necesario

## Desarrollo

### Probar Verificación de Versiones

```python
from app.service.update_service import UpdateService

service = UpdateService("1.0.0", "tu-organizacion/glosaap")
release = service.check_for_updates()
if release:
    print(f"Nueva versión: {release.version}")
    print(f"Changelog: {release.changelog}")
```

### Probar UI

```python
from app.ui.components.update_dialog import UpdateChecker

checker = UpdateChecker(page, "1.0.0", "tu-organizacion/glosaap")
checker.check_updates()  # Abre diálogo manual
```

### Simular Actualización (sin descargar)

Editar `update_service.py` para usar una versión local:
```python
# En check_for_updates(), antes de retornar:
return ReleaseInfo(
    version="99.0.0",  # Versión alta para forzar actualización
    # ... resto de campos con datos de prueba
)
```
