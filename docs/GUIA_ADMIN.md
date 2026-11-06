# Guía del Administrador – Glosaap

Guía operativa para quien administra las PCs, la red y los homologadores.
No es manual de uso diario (eso está en `MANUAL_USUARIO.md`).

## 1. Arquitectura de despliegue

- La app corre desde el ejecutable `Glosaap.exe` (o `python main.py` en
  desarrollo, que redirige solo al `.venv`).
- Todo lo compartido vive en red: `\\MINERVA\Cartera\GLOSAAP`.
  Si la red no está disponible, la app cae a carpetas temporales locales
  (ver `get_output_dir()` en `app/config/settings.py`).
- Las actualizaciones llegan por GitHub Releases y se aplican con
  `updater.exe`. Detalle del mecanismo en `docs/AUTO_UPDATE.md`.

## 2. Rutas de red (fuente única: `app/config/settings.py`)

| Clave (`NETWORK_PATHS`) | Ruta | Contenido |
|---|---|---|
| `homologador` | `...\GLOSAAP\HOMOLOGADOR` | Excels de homologación por EPS |
| `mutualser_output` | `...\REPOSITORIO DE RESULTADOS\MUTUALSER` | Consolidados + objeciones Mutualser |
| `coosalud_output` | `...\REPOSITORIO DE RESULTADOS\COOSALUD` | Idem Coosalud |
| `sanitas_output` | `...\REPOSITORIO DE RESULTADOS\SANITAS` | Idem Sanitas |
| `previsora_output` | `...\REPOSITORIO DE RESULTADOS\PREVISORA` | Registro + objeciones Previsora |

Prohibido hardcodear rutas UNC fuera de `settings.py`
(`eps_config.py` solo usa `get_homologador_path()`).

## 3. Homologadores por EPS (`HOMOLOGADOR_FILES`)

| Clave | Archivo | Columnas |
|---|---|---|
| `mutualser` | `mutualser_homologacion.xlsx` | Código Servicio de la ERP / Código producto en DGH / COD_SERV_FACT |
| `coosalud` | `coosalud_homologacion.xlsx` | Código Servicio de la ERP / Código producto en DGH |
| `sanitas` | `sanitas_homologador_2.xlsx` | CODIGO PROCEDIMIENTO PRESTADOR / CODIGO HOMOLOGO |
| `sanitas_insumos` | `sanitas_homologador.xlsx` | CUM / IUM RDA / CODIGO PRODUCTO |
| `previsora` | `Previsora_homologador.xlsx` | CODIGO PREVISORA / codigo homologado |

Notas:

- Los nombres distinguen mayúsculas en red Windows solo por
  convención: respeta el nombre exacto al reemplazar un archivo.
- Si un homologador falta, la app **no se detiene**: procesa igual y
  conserva los códigos originales, con aviso en el log. Revisa el
  resumen "homologados vs no homologados" después de cada corrida.
- `HomologacionService._guardar()` crea backup en `HOMOLOGADOR\backups\`
  antes de cada guardado. Limpia backups de más de 30 días a mano si el
  disco se llena; nunca borres el `.xlsx` vigente.

## 4. Instalación en un PC nuevo

### Opción A (recomendada): instalador

1. Descarga `Glosaap_Setup_vX.Y.Z.exe` desde
   https://github.com/Damdev80/Glosaap/releases (el `.sha256` viaja
   al lado; si tu navegador lo bloquea, desbloquéalo en Propiedades).
2. Ejecuta sin admin: instala en `%LOCALAPPDATA%\Glosaap` con acceso
   directo en el menú inicio (icono de escritorio opcional).
3. Si Glosaap está corriendo, el instalador pide cerrarlo primero
   (AppMutex): no instala encima de la app en uso.
4. Verifica acceso a `\\MINERVA\Cartera\GLOSAAP` (sin red, la app usa
   temporales locales y avisa en el log).

### Opción B: ZIP portable

Extrae `Glosaap_vX.Y.Z_<ts>.zip` en una carpeta permanente (no en
Descargas) y ejecuta `Glosaap.exe`. El `updater.exe` debe quedar al
lado para las actualizaciones automáticas.

### Desarrollo (solo programadores)

1. Instalar Python 3.11 y clonar el repo.
2. `python -m venv .venv` y `pip install -r requirements.txt`.
3. Ejecutar con `py main.py` (redirige solo al `.venv`) o
   `.venv\Scripts\python.exe main.py`.
4. Iniciar sesión y procesar una EPS pequeña primero (Coosalud o un solo
   correo) para validar rutas de salida.

## 5. Actualizaciones: qué hacer si algo falla

1. La app avisa al arrancar si hay versión nueva (`v0.11.x` en
   https://github.com/Damdev80/Glosaap/releases).
2. Si una actualización deja la app sin arrancar: el `updater` deja
   backup de la versión anterior en la carpeta de instalación.
   Restaura la carpeta del backup y reporta el número de versión.
3. Si un release sale sin assets (ZIP), avisa: ningún release se
   publica sin su `.sha256` (fail-closed, ver `release.py`).
4. Nunca publiques un tag de prueba (`v0.0.0-test` crea un release real).

## 6. Diagnóstico rápido (tabla de errores frecuentes)

| Síntoma | Dónde mirar | Acción |
|---|---|---|
| "No se pudo procesar ningún archivo pdf" + pistas | Diálogo de error | Lee las pistas; si hay `PREVISORA_DEBUG_*.txt` en la salida, pásalo a desarrollo |
| "Sin Nro Factura en ..." | Log + debug txt | El PDF trae otro formato de rótulo; es ajuste de parser, no error de uso |
| "Homologador X no encontrado; se continua sin homologacion" | `HOMOLOGADOR\` en red | Verifica nombre exacto del archivo y permisos de red |
| "0 correos encontrados" con tildes en el asunto | Log IMAP | Desde 0.11.29 el criterio viaja en UTF-8; si persiste, verifica carpeta (INBOX) y `From` real en el webmail |
| Archivos de una corrida anterior mezclados | Carpeta temporal `glosaap_attachments` | La app la limpia sola al buscar; no borrar a mano durante un proceso |
| `ModuleNotFoundError: No module named 'flet'` | Consola | Se ejecutó el Python del sistema; usa `py main.py` (0.11.30+ redirige solo) |
