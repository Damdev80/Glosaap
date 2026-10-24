# Changelog - Glosaap

Todos los cambios notables en este proyecto serán documentados en este archivo.

El formato está basado en [Keep a Changelog](https://keepachangelog.com/es-ES/1.0.0/).

---

## [0.11.24] - 2026-10-24

### ✨ Nuevas Características
- Homologador Manual con soporte para SANITAS: modos Auto (detecta filas
  INSUMOS por columna de procedimiento), Normal (ERP → DGH) e Insumos
  (cascada CUM / IUM RDA / CODIGO PRODUCTO), reutilizando `SanitasProcessor`.
- `settings.get_homologador_paths()` como fuente única de rutas de
  homologador por EPS (Sanitas usa dos archivos).

### 🔧 Mejoras Técnicas
- `SanitasProcessor.homologar_codigo_servicio()` y `es_insumo()` extraídos
  como API reutilizable; `homologate()` ahora los consume (sin lógica
  duplicada).
- `homologador_manual_view.py` deja de hardcodear rutas UNC de homologación.


## [0.11.23] - 2026-10-23

### 🐛 Correcciones
- Sanitas: columna prestador se resuelve por contenido (PROCEDIMIENTO +
  PRESTADOR, tolerante a tildes/orden) en vez de literal exacto; ya no cae
  en `CODIGO PROCEDIMIENTO` solo.
- Sanitas: columnas numéricas con vacíos (floats 7.0/1.0 de Excel) paddeden
  a "07"/"01", no "70"/"10".


## [0.11.22] - 2026-10-23

### ✨ Nuevas Características
- Homologación Sanitas en dos vías: INSUMOS por cascada CUM/IUM RDA/
  CODIGO PRODUCTO (`sanitas_homologador.xlsx`); resto por homologador
  normal (`sanitas_homologador_2.xlsx`, prestador→homólogo).
- Código de objeción Sanitas de 6 caracteres (GENERAL 1-6 → FA/TA/SO/AU/
  CO/CL, ESPECIFICO/APLICACIÓN a 2 dígitos, APLICACIÓN vacía → "01").
- Observación Sanitas vacía → "MVC EN <procedimiento>".
- Homologación Sanitas por columna CODIGO PROCEDIMIENTO PRESTADOR.


## [0.11.21] - 2026-10-22

### 🐛 Correcciones
- Build reproducible: PyInstaller fijado a `6.22.3` en CI y releases (la
  versión sin fijar del runner no empaquetaba `flet_desktop` y el exe moría
  en el preflight con "No module named 'flet_desktop'").
- `build.py` falla rápido si `flet_desktop` falta o difiere de versión en
  el entorno de build, en vez de producir un exe cojo.


## [0.11.20] - 2026-10-22

### 🐛 Correcciones
- Exe portable: empaquetar `flet_desktop` (`--collect-all`); sin esto flet
  intentaba `sys.executable -m pip install` y el exe se re-ejecutaba en
  bucle infinito (decenas de procesos `Glosaap.exe`, uno por segundo).
- Preflight en `main.py`: si falta el visor Flet en el exe, salida limpia
  con mensaje en vez del bucle de re-ejecución.


## [0.11.19] - 2026-10-22

### ✨ Nuevas Características
- Sanitas end-to-end: reglas de negocio, homologación y cableado UI (`3d084b6`)

### 🐛 Correcciones
- Sanitas: nombre exacto de columna de valor (`f9dedc8`)
- Arranque en Windows: prints de diagnóstico con emojis movidos a logger (crash `UnicodeEncodeError` en consola cp1252)
- `imap_client`: import faltante de `email.message` (fallaba según orden de imports)
- `main.py`: stdout/stderr forzados a UTF-8 al arrancar


## [0.11.18] - 2026-10-21

### ✨ Nuevas Características
- Búsqueda Sanitas por remitente y asunto exacto a nivel IMAP
- Ventana con memoria, atajos ESC/F5, diálogo de settings único
- Release automático desde tag con ZIP + checksum en CI

### 🐛 Correcciones
- Build invoca PyInstaller vía python -m (sin depender del PATH)
- Tarjeta Sanitas sin badge de desarrollo


## [0.11.17] - 2026-10-20

### 🔄 Actualizaciones verificadas
- Verificación SHA256 del ZIP antes de instalar (fail-closed)
- Rollback automático si la instalación falla
- Updater auto-actualizable, botón omitir versión e intervalo real

### ✨ Nuevas Características
- EPS Sanitas visible con aviso de en desarrollo
- Resumen post-procesado con homologados y no homologados
- Búsqueda exacta por patrón de asunto de cada EPS
- Progreso con botón cancelar y confirmaciones antes de borrados

### 🔧 Mejoras Técnicas
- Secretos migrados a keyring/DPAPI, navegación por canal único
- Logs silenciosos en búsquedas masivas, botones minimalistas

## [Unreleased]

### ✨ Nuevas Características
- **Sistema de Temas Claro/Oscuro**: Toggle en el dashboard para cambiar entre temas
- **Descarga por Web**: Nueva opción para descargar glosas desde portales web (Familiar, Fomag)
- **Navegación mejorada**: Botones de navegación en todas las vistas

### 🐛 Correcciones
- Corregido bug donde el contenido del dashboard se veía detrás de otras vistas
- Solucionado problema de pantalla negra al cambiar tema antes de iniciar sesión
- Eliminada navegación por tecla ESC que causaba comportamientos inesperados

### 🔧 Mejoras Técnicas
- Migración completa a `ft.Colors.*` para soporte de temas
- Todos los contenedores ahora tienen `bgcolor=ft.Colors.SURFACE` para evitar transparencia
- Refactorizado `ThemeManager` para mejor gestión de colores
- Simplificado `toggle_theme()` para dejar que Flet maneje las actualizaciones automáticamente

### 📚 Documentación
- Creado `DEVELOPER_GUIDE.md` con guía completa para desarrolladores
- Actualizado `README.md` con información actualizada del proyecto
- Documentadas buenas prácticas para uso de colores y temas

---

## [0.11.16] - 2026-02-05

### 🐛 Correcciones
- **Fechas individuales por correo en COOSALUD**: cada glosa usa la fecha de su propio correo en vez de una fecha global (`3f336ff`, `920aef5`, tag `v0.11.16`)

### 📚 Documentación
- Comentario de carga de variables de entorno en `release.py` (`8b376ab`)

---

## [0.11.15] - 2026-02-02

### ✨ Nuevas Características
- Nuevo archivo de configuración de base de datos (`eb0b17a`)

### 🔧 Mejoras Técnicas
- Cambio de versión (`2d846bb`, tag `v0.11.15`)

---

## [0.11.14] - 2026-01-31

### 🔧 Mejoras Técnicas
- La ventana ya no cambia de tamaño si está maximizada o en pantalla completa; simplificado el breadcrumb en `ToolsView` (`c3e8892`)
- Eliminada la tarjeta de configuración de `ToolsView` (`53e995c`)
- Suprimido aviso de type checking (`4e78016`)

### 📚 Documentación
- Nueva guía para subir cambios a Git (`docs/GUIA_GIT_CAMBIOS.md`, `2c794ee`)

---

## [0.11.13] - 2026-01-30

### ✨ Nuevas Características
- **CoosaludProcessor con fecha de correo**: extrae la fecha del email con logging y `process_glosas` acepta `email_date` (`2711f18`, tag `v0.11.13`)

### 🔧 Mejoras Técnicas
- Merge de PR #1 y bumps de versión a 0.11.12 / 0.11.13 (`deea0b3`, `894231d`, `c8aa5ee`)

---

## [0.11.12] - 2026-01-29

### 🔧 Mejoras Técnicas
- Bump a 0.11.11; refactor del manejo de tema en vistas UI con métodos `rebuild` (`d7ecc6a`)
- Refactor de legibilidad: firmas de métodos simplificadas sin type hints (`c61fae7`, `33975f2`, tag `v0.11.12`)
- Componentes UI con colores adaptativos al tema (`e002a35`)

### 📚 Documentación
- Formato y enlaces del `README.md`, incluido el link a `DEVELOPER_GUIDE` (`3e172f2`, `86a74b3`)

---

## [0.11.11] - 2026-01-28

### ✨ Nuevas Características
- Refactor de `EmailService` y `CoosaludProcessor` con documentación ampliada; eliminadas pantallas obsoletas de login y mensajes (`47bfbd4`)

### 🐛 Correcciones
- Constructor de `BaseProcessor` acepta `homologador_path` como `Optional` (`6631539`)

### 🧪 Tests
- Tests de integración de `FomagScraper` y validación de carga de datos de servicios (`80b86a0`, `469d122`, tag `v0.11.11`)

---

## [0.11.8 - 0.11.10] - 2026-01-28

> Sin tags para este rango. Cambios verificables en commits intermedios entre `v0.11.7` y `v0.11.11`:

### ✨ Nuevas Características
- Bump a 0.11.7; mejora de type hints en encabezado de navegación y manejo de errores en `build.py` (`75c1fb4`, 2026-01-27)
- Bump a 0.11.9; mejor manejo de diálogos y notificaciones toast (`dc7cc60`, 2026-01-28)

### 🔧 Mejoras Técnicas
- Navegación y retroalimentación de carga entre vistas (`ac24fb5`)
- Limpieza de tests del scraper de Fomag (`ed47efa`)

### 🧪 Tests
- Nuevos tests unitarios para varios módulos (`0aecb16`)

---

## [0.11.6 - 0.11.7] - 2026-01-27

> Los tags `v0.11.6` y `v0.11.7` apuntan al mismo commit (`8e8ed8c`, cuyo mensaje indica bump a 0.11.5):

### 🐛 Correcciones
- El updater omite `updater.exe` en uso durante las actualizaciones (`8e8ed8c`)

---

## [0.11.5] - 2026-01-27

### 🔧 Mejoras Técnicas
- Mejora del proceso de build y script de release para integración con GitHub (`a424dfa`, tag `v0.11.5`; el mensaje del commit indica versión 0.11.4)

---

## [0.11.1 - 0.11.4] - 2026-01-27

> Los tags `v0.11.1`, `v0.11.2` y `v0.11.4` apuntan al mismo commit que `v0.11.0` (`901644d`); `v0.11.3` no tiene tag. Sin cambios propios en este rango:

### 🔧 Mejoras Técnicas
- Release script carga `GITHUB_TOKEN` desde `.env` (`901644d`)
- Refactor del script de build y del proceso de release (`3667409`)

---

## [0.11.0] - 2026-01-27

### ✨ Nuevas Características
- **Sistema de Actualizaciones Automáticas**: La app ahora verifica nuevas versiones automáticamente
- **Campo `fecha_correo`**: Se captura la fecha en que se recibe el correo con glosas
- **Merge inteligente por `id_detalle`**: Las observaciones se vinculan específicamente a cada servicio
- **Priorización de códigos**: Los códigos se ordenan por prioridad (FA > SO > AU > CO > CL > TA)

### 🐛 Correcciones
- Corregido problema de concatenación masiva de observaciones
- Mejorada la validación de tokens de GitHub
- Implementado uso de variables de entorno para credenciales

### 🔧 Mejoras Técnicas
- Refactorizado sistema de homologación
- Optimización de procesamiento de archivos masivos
- Mejor manejo de errores en build automático

### 📦 Actualizaciones de Dependencias
- Actualizado PyInstaller a última versión
- Agregado soporte para python-dotenv

---

## [0.10.0] - 2026-01-25

### ✨ Nuevas Características
- **Carga masiva de homologaciones**: Ahora puedes cargar múltiples códigos de una vez
- **Interfaz mejorada de gestión**: Dashboard actualizado

### 🐛 Correcciones
- Corregidos errores en procesamiento de Coosalud

---
