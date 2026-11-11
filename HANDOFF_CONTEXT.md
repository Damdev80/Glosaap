# HANDOFF_CONTEXT.md — Glosaap

> Documento de traspaso para agentes y desarrolladores que se incorporen al
> proyecto. Resume qué es Glosaap, cómo está construido, qué se hizo en las
> últimas semanas y cuál es el estado real al **2026-11-11**.
>
> **Regla de oro:** si este documento contradice al código, manda el código.
> Varios archivos de `.opencode/agents/` y `.opencode/skills/` tienen cifras o
> estados históricos desactualizados; no los uses como fuente de verdad.

---

## 0. Resumen ejecutivo

- **Producto:** aplicación de escritorio Windows para gestionar glosas médicas
  de EPS colombianas: busca correos IMAP, descarga adjuntos, homologa códigos,
  consolida información y genera archivos de objeciones para cargar en
  Dinámica/DGH.
- **Stack:** Python 3.11 + Flet 0.27.6, pandas/openpyxl, pypdf, Playwright,
  PyInstaller e Inno Setup.
- **Versión publicada:** `v0.11.32` (2026-11-09), con ZIP portable, instalador
  Windows y checksums SHA-256.
- **Estado de calidad:** 790 tests passing, cobertura 58.67 %, Ruff limpio en
  `app/`; CI y Auto Release verdes sobre `c8ed630`.
- **Bloqueo de negocio:** falta confirmar con el usuario dos campos de las
  objeciones de Previsora (`CRNCONOBJ` vacío y `GENUSUARIO4=1103858268`).
- **No existe integración automática con Dinámica/DGH.** La carga de los
  archivos generados sigue siendo manual; los documentos sobre SQL/DGH son
  propuesta de roadmap, no código implementado.

---

## 1. Qué es Glosaap

Glosaap es una herramienta interna del área de cartera/glosas de
**La Concepción**. Automatiza la parte repetitiva del ciclo de glosas:

```text
Correo IMAP / portal web
  -> descarga de Excel/PDF adjuntos
  -> lectura y normalización
  -> homologación de códigos contra maestros Excel
  -> consolidado + archivo de objeciones por EPS
  -> guardado en \\MINERVA\Cartera\GLOSAAP
  -> carga manual en Dinámica/DGH
```

Lo que **sí** hace hoy:

- Login IMAP con credenciales del usuario y sesión recordada/cifrada.
- Búsqueda de correos por EPS, asunto, remitente y rango de fechas.
- Descarga de adjuntos Excel/PDF, con deduplicación por ID de mensaje.
- Procesamiento de Mutualser, Coosalud, Sanitas y Previsora.
- Homologación automática y herramienta manual de homologación.
- Generación de consolidados/registros y archivos de objeciones.
- Descarga web para Familiar de Colombia y Fomag (Playwright).
- Herramientas: gestión de homologación, homologador manual y Mix Excel.
- Actualizaciones automáticas desde GitHub Releases.
- Instalador Windows por usuario, sin permisos de administrador.
- Guías interactivas dentro de la app.

Lo que **no** hace hoy:

- No escribe ni se conecta a Dinámica/DGH; la carga es manual.
- No tiene implementados como flujo completo “Evitar Glosa” ni “Responder
  Glosa”; aparecen como roadmap/placeholder.
- No firma digitalmente el ejecutable ni verifica firma en el updater.
- No es una aplicación web ni multiusuario; es desktop y por usuario.

---

## 2. Estado actual verificable

| Ítem | Estado |
|---|---|
| Rama | `main` |
| Release | `v0.11.32` publicada el 2026-11-09 |
| Tag del release | `v0.11.32` -> `c8ed630` |
| Versión en código | `APP_VERSION = "0.11.32"` |
| Último workflow Auto Release | success (run `42650788378`, 2026-11-09) |
| Último CI sobre `c8ed630` | success |
| Tests | 790 passed (última corrida completa) |
| Cobertura | 58.67 % |
| Ruff | limpio en `app/` y tests tocados |
| Release assets | ZIP, instalador, y un `.sha256` por cada uno |
| Working tree local | solo `.coverage` modificado; **no commitear** |

URL del release:

<https://github.com/Damdev80/Glosaap/releases/tag/v0.11.32>

Assets publicados:

- `Glosaap_v0.11.32_20261109_160547.zip`
- `Glosaap_v0.11.32_20261109_160547.zip.sha256`
- `Glosaap_Setup_v0.11.32.exe`
- `Glosaap_Setup_v0.11.32.exe.sha256`

> Si se agrega documentación después del release, `main` quedará por delante
> del tag. Eso es normal; **no mover ni recrear el tag `v0.11.32`**. El próximo
> cambio funcional debe ir a una versión nueva.

---

## 3. Stack y entorno

### Runtime

- Python **3.11.9** en `.venv` (entorno recomendado).
- `.venv312` tiene Python 3.12.10 y también se usa en CI.
- El `py` del sistema es 3.15 y **no está soportado**. `main.py` redirige
  automáticamente a `.venv` si se ejecuta con el Python del sistema.
- Windows es el único target real: rutas UNC, DPAPI, mutex y empaquetado.

### Dependencias principales

| Área | Dependencias |
|---|---|
| UI | `flet==0.27.6`, `flet-desktop==0.27.6` |
| Excel | `pandas`, `openpyxl` |
| PDF | `pypdf` |
| Web scraping | `playwright` |
| Red/API | `requests`, `python-dotenv` |
| Secretos | `keyring`, `cryptography`, `filelock` |
| Tests | `pytest`, `pytest-cov`, `pytest-mock`, `pytest-asyncio` |
| Calidad | `ruff`, `pyright` |
| Build | `pyinstaller==6.22.3`, Inno Setup 6 |

`flet` y `flet-desktop` deben quedar **exactamente** en la misma versión. Un
rango abierto puede mezclar versiones y dejar el `.exe` sin visor.

### Arranque

```powershell
# Desarrollo normal (redirige solo al .venv)
py main.py

# Alternativa explícita
.\.venv\Scripts\python.exe main.py
```

No ejecutes la app con el Python 3.15 del sistema. Si `py main.py` falla por
`ModuleNotFoundError`, revisa que exista `.venv\Scripts\python.exe`.

---

## 4. Arquitectura

### Capas

```text
app/
  config/        settings.py, eps_config.py
  core/          lógica de negocio pura y procesadores legacy
  service/       servicios de aplicación, procesadores EPS y scrapers
  ui/            Flet: app, vistas, pantallas, componentes, estilos
tests/           32 archivos, 790 tests
main.py          entrypoint + mutex de instancia única
updater.py       actualización desde GitHub Releases
build.py         PyInstaller + ZIP + instalador opcional
release.py       publicación manual alternativa
bump.py          sincronización de versión + CHANGELOG
installer/       glosaap.iss (Inno Setup)
.github/         CI y Auto Release
```

### Archivos clave

| Archivo | Rol |
|---|---|
| `app/config/settings.py` | **Fuente única** de versión, rutas de red, homologadores, logging y salida local |
| `app/config/eps_config.py` | Definición de EPS habilitadas, asunto, remitente, procesador y homologador |
| `app/service/processors/base_processor.py` | Clase base Template Method y helpers compartidos |
| `app/service/processors/coosalud_processor.py` | Procesador Coosalud |
| `app/service/processors/sanitas_processor.py` | Procesador Sanitas (normal + insumos) |
| `app/service/processors/previsora_processor.py` | Procesador Previsora (PDF) |
| `app/core/mutualser_processor.py` | Procesador Mutualser (vive en core por historia) |
| `app/core/imap_client.py` | Búsqueda/descarga IMAP |
| `app/service/email_service.py` | Orquestación de búsqueda y procesamiento por EPS |
| `app/service/attachment_service.py` | Descarga, metadata y limpieza de adjuntos |
| `app/core/homologacion_service.py` | CRUD de homologadores y backups |
| `app/ui/app.py` | Composición de la app Flet y navegación principal |
| `app/ui/navigation.py` | Control de navegación |
| `app/ui/styles.py` | `ThemeManager` y estilos claro/oscuro |
| `app/ui/guide_content.py` | Textos de tour y ayudas por vista |
| `app/ui/components/guide_overlay.py` | Tarjeta flotante de guía |
| `main.py` | Bootstrap, preflight de Flet y mutex `Local\GlosaapAppMutex` |
| `installer/glosaap.iss` | Instalador Inno Setup por usuario |

### Patrón de procesadores

Todos heredan de `BaseProcessor` y siguen el Template Method:

```text
load_homologador()
  -> identify_files()
  -> validate_files()
  -> extract_data()
  -> homologate()
  -> save_result() / save_results()
```

Reglas que **no** se deben romper:

- `identify_files()` devuelve **todos** los archivos válidos, no solo el primero.
- `homologate()` devuelve un `pd.DataFrame`; si se necesitan dos hojas, se
  compone el diccionario en `process_glosas()`.
- Normalizar códigos con `_normalize_code()` (strip, upper, sin `.0`).
- Factura con `_formatear_crncxc()` -> `FC0000{dígitos}`.
- Fechas con `_formatear_fecha_dmy()` -> `DD/MM/YYYY`.
- Valores monetarios con `_obtener_valor_numerico()`; **nunca** `replace('.', '')`.
- Fecha de objeción por archivo, usando `attachment_service.get_file_metadata()`
  y fallback a la fecha del correo.
- Eliminar columnas internas (`_FACTURA`, `fecha_correo`) antes de exportar.
- Sin `print` en loops; usar `app.config.settings.logger`.
- No caer al “primer xlsx” si no se encuentra el homologador: conservar códigos
  originales y avisar.

### Rutas y red

Fuente única: `app/config/settings.py`.

- Base: `\\MINERVA\Cartera\GLOSAAP`
- Homologadores: `...\HOMOLOGADOR`
- Salidas: `...\REPOSITORIO DE RESULTADOS\{MUTUALSER,COOSALUD,SANITAS,PREVISORA}`
- Si la red no está disponible, `get_output_dir()` cae a `%TEMP%\glosaap`.

Prohibido hardcodear rutas UNC fuera de `settings.py`.

---

## 5. Flujo funcional

1. **Login:** el usuario ingresa credenciales IMAP. La app detecta el servidor
   por dominio y puede recordar la sesión de forma cifrada.
2. **Dashboard:** el flujo principal es **Manejar Glosa**. También están
   Herramientas y Descarga Web.
3. **Selección de EPS y fechas:** se elige EPS y rango Desde/Hasta; ambas
   fechas son obligatorias.
4. **Búsqueda IMAP:** se filtra por asunto/remitente de la EPS y se listan
   correos. La búsqueda usa headers, no cuerpos completos.
5. **Descarga:** los adjuntos se guardan en temporales, con deduplicación por
   ID de mensaje y metadata de fecha del correo.
6. **Procesamiento:** el procesador de la EPS lee los archivos, homologa
   códigos y genera consolidado/registro + objeciones.
7. **Revisión:** la app muestra resumen de homologados/no homologados y los
   archivos generados. La carga a Dinámica/DGH sigue siendo manual.
8. **Herramientas:** gestión de homologación (con backup), homologador manual
   y Mix Excel.

La cinta de pasos de la UI refleja el flujo:

```text
Buscar -> Descargar -> Procesar -> Revisar
```

---

## 6. EPS soportadas

| EPS | Estado | Asunto / filtro | Procesador | Homologador |
|---|---|---|---|---|
| Mutualser | Habilitada | `Objeciones de glosa Factura FC` | `MutualserProcessor` (`app/core`) | `mutualser_homologacion.xlsx` |
| Coosalud | Habilitada | `Reporte Glosas y Devoluciones` | `CoosaludProcessor` | `coosalud_homologacion.xlsx` |
| Sanitas | Habilitada | `Referencia: Informe Glosas EPS Sanitas` + remitente | `SanitasProcessor` | `sanitas_homologador_2.xlsx` (normal) y `sanitas_homologador.xlsx` (insumos) |
| Previsora | Habilitada | `Registrado: Notificación agrupada` + remitente | `PrevisoraProcessor` (PDF) | `Previsora_homologador.xlsx` |
| Nueva EPS | Deshabilitada | Sin procesador | — | — |
| Compensar | Deshabilitada | Sin procesador | — | — |
| Famisanar | Deshabilitada | Sin procesador | — | — |
| Cosalud | Deshabilitada | Typo histórico de Coosalud; no usar | — | — |

Notas:

- Sanitas tiene dos tablas de homologación y la UI las agrupa como
  **Normal** e **Insumos**.
- Previsora recibe PDFs de liquidación; no Excel.
- Previsora comparte el set estándar de 15 columnas de objeciones.
- Los nombres de archivo de salida llevan timestamp; los patrones exactos están
  en cada procesador.

---

## 7. Trabajo reciente (qué se hizo)

### 7.1 Fase A — documentación y consistencia de release

Commits principales: `02fa348`.

- Nueva `docs/GUIA_ADMIN.md`: despliegue, rutas de red, homologadores,
  actualizaciones y diagnóstico.
- Nueva `docs/GUIA_NUEVA_EPS.md`: procedimiento completo para integrar una EPS,
  usando Previsora como ejemplo real.
- `docs/DEVELOPER_GUIDE.md` corregido a la API real (Template Method) y a la
  rutina obligatoria de release.
- Nuevo `tests/test_release_consistency.py`: valida versión sincronizada,
  entrada completa del CHANGELOG y resolución de homologadores.

### 7.2 Fase B — instalador, updater y CI

Commits principales: `49bf0c2`.

- Instalador Inno Setup por usuario (`installer/glosaap.iss`):
  - instala en `%LOCALAPPDATA%\Glosaap`;
  - no requiere admin;
  - `AppMutex = Local\GlosaapAppMutex` para no instalar sobre la app abierta;
  - `AppId` estable para upgrades/desinstalación.
- `build.py --installer` compila el Setup y genera `.sha256`.
- `updater.py` con preflight de disco (ZIP × 3 + 50 MB).
- CI Auto Release:
  - compila ZIP + instalador;
  - falla si falta algún `.sha256` (fail-closed);
  - hace smoke test real de instalación, arranque y desinstalación;
  - publica assets y body desde `CHANGELOG.md`.

### 7.3 Fase C — guías interactivas

Commits principales: `5692944`, `ac667bb`.

- Tour de primera vez al llegar al dashboard, con opción “no volver a mostrar”.
- Botón de guía en Dashboard y Mensajes.
- Botón `?` en Herramientas, Homologación, Homologador manual, Mix Excel,
  Descarga Web y EPS.
- Cinta de pasos Buscar -> Descargar -> Procesar -> Revisar, actualizada en
  cada etapa.
- Corrección: el tour creaba un `AlertDialog` por paso y se apilaban; ahora es
  una sola tarjeta flotante no modal que se retira al cerrar.
- La ayuda de Mensajes resalta con parpadeo la cinta y el botón Procesar.

### 7.4 Fix `CROVALOBJ` (Mutualser y todas las EPS)

Commit: `16b3683`.

Problema real: en Mutualser, `"$ 3.404"` se interpretaba como el decimal
`3.404` y Excel en español lo mostraba como `3,404`.

Solución: se corrigió el parser compartido
`BaseProcessor._obtener_valor_numerico()`:

- un separador seguido de exactamente **3 dígitos** es separador de miles;
- 1–2 dígitos finales son centavos;
- soporta `1.234,56`, `1,234.56`, negativos y espacios duros (`\xa0`);
- elimina símbolo de moneda y letras;
- `3.404` -> `3404`; `10.080` -> `10080`; `1500.50` -> `1500.5`;
- `220000` se conserva entero.

Se validó con un consolidado real de Mutualser (`20261030_084550`): los
valores salieron `3404`, `220000`, `1904`, `10080`, etc., todos numéricos.

Tests: `tests/test_valor_monetario.py`, 85 casos, incluye exportación real de
objeciones y cobertura de las 4 EPS.

### 7.5 Release 0.11.32 e incidente de CI

Commits: `3e5a0c7` (release) y `c8ed630` (fix CI).

- Versión sincronizada en `settings.py`, `pyproject.toml`, `README.md`,
  `docs/MANUAL_USUARIO.md` y `docs/AUTO_UPDATE.md`.
- CHANGELOG `## [0.11.32] - 2026-11-09` completo, sin `(completar)`.
- Primer Auto Release se colgó en el smoke test: `Stop-Process` mataba solo el
  bootloader de PyInstaller y el proceso hijo `Glosaap.exe` seguía vivo,
  bloqueando la desinstalación.
- Fix en `.github/workflows/auto-release.yml`:
  - `taskkill /PID <pid> /T /F` para matar el árbol completo;
  - desinstalación con `/VERYSILENT /SUPPRESSMSGBOXES /NORESTART`;
  - `WaitForExit` con timeout para no colgar el job.
- Se recreó el tag `v0.11.32` sobre `c8ed630` y el workflow terminó en success.
- Release final con 4 assets y smoke test real aprobado.

---

## 8. Pendientes, riesgos y deuda técnica

### Bloqueado por negocio

1. **Previsora — confirmar campos de objeciones**
   - `CRNCONOBJ` sale vacío porque el PDF no trae concepto de glosa.
   - `GENUSUARIO4 = 1103858268` está fijo en
     `app/service/processors/previsora_processor.py`.
   - Hay que confirmar con el usuario si Dinámica acepta el archivo así.
   - Si no, ajustar `_build_objeciones_df()` en `previsora_processor.py`.
   - No inventar valores ni cambiar el flujo sin esa confirmación.

### Verificación recomendada

2. **`CROVALOBJ` en producción**
   - Mutualser ya se validó con un consolidado real.
   - Conviene revisar una exportación reciente de Coosalud, Sanitas y Previsora
     para confirmar que no hay valores con coma ni centavos perdidos.
   - El fix es compartido, pero cada EPS tiene formatos de origen distintos.

3. **Instalador y updater en un PC limpio**
   - El smoke test de CI cubre instalación/arranque/desinstalación.
   - Falta probar una actualización real desde una versión anterior en un equipo
     de usuario, incluyendo red disponible y ausente.

### Riesgos conocidos

4. **Updater sin firma digital**
   - Solo se publica `.sha256`; el updater no verifica firma del ejecutable.
   - Riesgo supply-chain documentado. No eliminar los checksums del release.

5. **PyInstaller onefile y procesos hijos**
   - Cualquier smoke test o script que cierre la app debe matar el árbol
     (`taskkill /T /F`), no solo el PID del bootloader.
   - No volver a `Stop-Process` simple en CI.

6. **Dependencia de red**
   - Sin `\\MINERVA`, la app funciona con temporales locales, pero los
     homologadores reales no están disponibles.
   - No usar la red real en tests.

7. **Documentación de agentes desactualizada**
   - `.opencode/agents/glosa-qa.md` y
     `.opencode/skills/glosa-qa-python315/SKILL.md` hablan de 461 tests, 1 fallo
     y cobertura ~10 %; eso ya no es el estado actual.
   - El skill de homologación dice que solo Mutualser y Coosalud están
     habilitadas; hoy también lo están Sanitas y Previsora.
   - El skill de release menciona versiones viejas; el flujo vigente es
     `bump.py` + CHANGELOG + tag + Auto Release.
   - Cargar esos skills por sus reglas de dominio, pero contrastar estado con
     este documento y con el código.

8. **Deuda técnica**
   - `pyright` corre en CI como informativo (`|| true`); hay baseline de errores.
   - Cobertura 58.67 %; la UI queda mayormente fuera de la métrica.
   - Coosalud conserva dos variantes históricas de merge; no crear otra.
   - `homologar_observacion.py` tiene lógica duplicada con el procesador de
     Mutualser; si se toca, extraer lookup común en vez de parchear dos veces.
   - `.coverage` está versionado y suele aparecer modificado; **no commitearlo**.

### Roadmap (no implementado)

- Integración de solo lectura con Dinámica/DGH (catálogo, facturación, tarifas,
  autorizaciones, histórico). Ver `docs/AUTOMATIZACION_DINAMICA.md` y
  `docs/PROPUESTA_REUNION.md`.
- “Evitar Glosa” y “Responder Glosa” como flujos completos.
- Firma digital/code signing del ejecutable y verificación en updater.
- Limpieza de baseline de pyright y aumento real de cobertura de UI.

---

## 9. Reglas de trabajo para agentes

### Antes de tocar código

1. Lee este documento y el CHANGELOG superior.
2. Carga el skill correspondiente:
   - procesadores EPS: `glosa-eps-processor`;
   - IMAP/email: `glosa-imap-flow`;
   - homologación: `glosa-homologacion`;
   - UI Flet: `glosa-flet-theme`;
   - tests/cobertura: `glosa-qa-python315`;
   - release: `glosa-release`;
   - secretos: `glosa-secrets`.
3. Verifica el estado real con `git status`, `git log` y el código; no asumas
   que las cifras de los skills están vigentes.

### Convenciones

- **Rutas:** solo en `app/config/settings.py`; nada de UNC hardcodeado.
- **Logs:** `logger`, no `print` con emojis en código nuevo.
- **Fechas:** `DD/MM/YYYY`; facturas `FC0000{dígitos}`.
- **Valores:** `_obtener_valor_numerico()`; no destruir decimales.
- **Excel:** quitar columnas internas antes de exportar.
- **UI:** `ThemeManager`/`ft.Colors`, contenedores con
  `bgcolor=ft.Colors.SURFACE`, verificar tema claro y oscuro.
- **Navegación Flet:** registrar rutas en `app/ui/app.py` y
  `app/ui/navigation.py`; no usar `overlay.clear()`.
- **Threads:** no llamar `page.update()` desde hilos secundarios.
- **Tests:** `tmp_path`; prohibido tocar `\\MINERVA` o servicios reales.
- **Commits:** `feat:`, `fix:`, `docs:`, `chore:`, `refactor:`, `test:`.
- **Release:** semver, CHANGELOG completo, tag coincidente; nunca tags de prueba.

### Qué no hacer

- No commitear `.env`, `.session.json`, `.coverage`, `dist/`, `build/`,
  `release/` ni credenciales.
- No cambiar `AppId` del instalador ni el nombre del mutex sin actualizar
  `main.py`, `.iss` y `tests/test_installer.py`.
- No publicar un release sin ZIP, instalador y `.sha256`.
- No “arreglar” un test fallido ocultándolo con `skip` o bajando el umbral.
- No asumir que Dinámica/DGH está integrado: no lo está.

---

## 10. Mapa de agentes y skills

### Agentes

| Agente | Alcance |
|---|---|
| `glosa-architect` | Planifica y delega; no edita ni ejecuta shell |
| `glosa-backend` | `app/core`, `app/service`, `app/config`, tests backend |
| `glosa-frontend` | Vistas, componentes, temas y navegación Flet |
| `glosa-qa` | Reproduce bugs, corre tests y mide cobertura; no edita código |
| `glosa-security` | Secretos, credenciales y rutas de red; solo propone |
| `glosa-devops` | Build PyInstaller, releases, updater y CI |
| `glosa-docs` | READMEs, guías, CHANGELOG y versiones |

### Skills

| Skill | Cuándo usarlo |
|---|---|
| `glosa-eps-processor` | Crear/corregir procesadores EPS y homologación |
| `glosa-imap-flow` | Tocar IMAP, email o autenticación |
| `glosa-homologacion` | Tocar servicio de homologación, backups o rutas |
| `glosa-flet-theme` | Tocar UI, temas o navegación Flet |
| `glosa-qa-python315` | Correr/interpretar tests y cobertura |
| `glosa-release` | Bump, build, tag y publicación |
| `glosa-secrets` | Migrar secretos a keyring/DPAPI |

---

## 11. Comandos frecuentes

### Tests y calidad

```powershell
# Suite completa con cobertura (pytest.ini manda)
.\.venv\Scripts\python.exe -m pytest

# Validación rápida sin cobertura
.\.venv\Scripts\python.exe -m pytest --no-cov

# Un módulo
.\.venv\Scripts\python.exe -m pytest tests/test_valor_monetario.py -v

# Lint (CI lintea app/)
.\.venv\Scripts\python.exe -m ruff check app/

# Lint de tests tocados
.\.venv\Scripts\python.exe -m ruff check tests/test_mi_test.py
```

### Build local

```powershell
# ZIP portable; no abre explorer ni pide Enter
.\.venv\Scripts\python.exe build.py --yes --skip-open

# ZIP + instalador (requiere ISCC/Inno Setup)
.\.venv\Scripts\python.exe build.py --yes --skip-open --installer
```

Salidas en `release/` (ignorado por git). Los nombres llevan timestamp; no
asumas un nombre fijo.

### Release

```powershell
# 1. Bump + sincronización de versiones
.\.venv\Scripts\python.exe bump.py X.Y.Z

# 2. Completar CHANGELOG (sin "(completar)")

# 3. Tests + lint
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe -m ruff check app/

# 4. Commit, tag y push
git add <archivos>
git commit -m "chore: release vX.Y.Z (...)"
git tag vX.Y.Z
git push origin main
git push origin vX.Y.Z
```

El push del tag dispara `.github/workflows/auto-release.yml`, que compila,
verifica checksums, hace smoke test y publica. No hay `gh` instalado; para
consultar runs/releases se puede usar la API de GitHub o `release.py`.

### Verificación del release

```powershell
git rev-parse HEAD
git rev-parse vX.Y.Z
git status --short
```

Debe coincidir el tag con el commit del release. Si se agregó documentación
después, el tag queda atrás: es esperado.

---

## 12. Glosario mínimo

| Término | Significado |
|---|---|
| **Glosa** | Objeción o descuento que una EPS aplica a una factura médica |
| **EPS** | Entidad Promotora de Salud (pagador) |
| **Homologación** | Traducir un código interno/facturado al código que espera Dinámica/DGH |
| **Homologador** | Excel maestro con la equivalencia de códigos por EPS |
| **DGH / Dinámica** | Sistema Gerencial Hospitalaria donde se cargan las respuestas |
| **CROVALOBJ** | Valor objetado en el archivo de objeciones |
| **CRNCXC** | Número de factura en formato `FC0000{dígitos}` |
| **CRNCONOBJ** | Concepto de objeción; en Previsora queda vacío por el PDF |
| **CUM / IUM** | Códigos de medicamentos/insumos; Sanitas usa una tabla aparte |
| **SO4801** | Código especial de Mutualser que unifica servicios |
| **IMAP** | Protocolo de correo usado para buscar y descargar glosas |
| **PyInstaller onefile** | Empaquetado que crea un proceso bootloader + proceso hijo |

---

## 13. Documentos relacionados

| Documento | Contenido |
|---|---|
| `README.md` | Visión general, instalación, uso y estructura |
| `docs/MANUAL_USUARIO.md` | Manual paso a paso para el operador |
| `docs/DEVELOPER_GUIDE.md` | Arquitectura, Flet, procesadores, testing y release |
| `docs/GUIA_ADMIN.md` | Despliegue, red, homologadores, updates y diagnóstico |
| `docs/GUIA_NUEVA_EPS.md` | Procedimiento para integrar una EPS nueva |
| `docs/AUTO_UPDATE.md` | Mecanismo de actualización y checksums |
| `docs/AUTOMATIZACION_DINAMICA.md` | Propuesta de integración SQL con DGH (no implementada) |
| `docs/PROPUESTA_REUNION.md` | Propuesta de migración de homologación a SQL Server |
| `docs/GUIA_GIT_CAMBIOS.md` | Guía básica de Git para el equipo |
| `CHANGELOG.md` | Historial de versiones; la entrada superior es la vigente |

---

## 14. Primer día de un agente: checklist

1. `git status --short` y `git log --oneline -10`.
2. Confirmar que `main` está en el commit del release o posterior.
3. Leer `CHANGELOG.md` (entrada `0.11.32`) y este documento.
4. Cargar el skill del área que va a tocar.
5. Correr `pytest --no-cov` o el módulo relevante antes de cambiar nada.
6. Si toca Previsora, leer la sección de pendientes y **no** cambiar
   `CRNCONOBJ`/`GENUSUARIO4` sin confirmación.
7. Si toca release/CI, revisar el smoke test y no reintroducir
   `Stop-Process` simple.
8. Al terminar: tests, lint, `git diff`, y dejar claro qué quedó pendiente.

---

**Última actualización:** 2026-11-11  
**Responsable del traspaso:** equipo Glosaap / sesión de release 0.11.32
