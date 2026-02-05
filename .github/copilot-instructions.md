# Glosaap - Instrucciones para Agentes de IA

## Contexto del Proyecto
**Glosaap** es una aplicación de escritorio para gestionar glosas médicas. Automatiza la descarga de correos IMAP, procesamiento de archivos Excel de EPS (Entidades Promotoras de Salud), homologación de códigos de servicios médicos, y generación de respuestas. Construida con **Python 3.10+** y **Flet** (framework UI tipo Flutter/Material Design).

### Dominio de Negocio
- **Glosas**: Objeciones de EPS a cobros médicos que requieren justificación documental
- **Homologación**: Mapeo entre códigos internos de servicios y códigos estándar (CUPS/DGH)
- **EPS**: Entidades Promotoras de Salud (aseguradoras médicas colombianas)
- **Flujo**: Correo/Web → Excel → Homologación → Archivos respuesta

## Arquitectura en Capas

### Estructura de Directorios (Separación Estricta)
```
app/
├── config/          # Configuración centralizada (settings.py, eps_config.py)
│   └── settings.py  # ÚNICA fuente de verdad para VERSION, rutas, constantes
├── core/            # Lógica de negocio pura (sin dependencias UI/Flet)
│   ├── imap_client.py          # Cliente IMAP crudo (sin EmailService)
│   ├── homologacion_service.py # CRUD códigos homologación (SQLite)
│   └── session_manager.py      # Sesiones persistentes (cryptography)
├── service/         # Capa orquestación (coordina core + I/O)
│   ├── email_service.py        # Orquesta IMAP + procesadores
│   ├── processors/             # Patrón Template Method por EPS
│   │   ├── base_processor.py  # ABC define flujo: identify→validate→extract→homologate→save
│   │   └── coosalud_processor.py # Ej: lee pares DETALLE/GLOSA, genera 2 Excel
│   └── web_scraper/            # Playwright headless por portal EPS
│       ├── base_scraper.py     # Interface scrape(user, pass) -> List[str]
│       └── familiar_scraper.py # Ej: login + descarga PDFs de portal
└── ui/              # Interfaz Flet (NO lógica de negocio)
    ├── app.py       # Punto entrada, orquesta servicios, maneja eventos Flet
    ├── styles.py    # ThemeManager (persistencia tema), get_colors()
    ├── navigation.py # NavigationController para transiciones (go_to, show/hide)
    └── views/       # Vistas completas (LoginView, DashboardView, etc.)
```

### Flujo de Datos Típico (Ej: Búsqueda por Correo)
```
Usuario (UI) → DashboardView.on_search_click()
    ↓
EmailService.search_messages(eps, date_from, date_to)  # Orquesta
    ↓
IMAPClient.search(criteria)  # Core: interacción pura IMAP
    ↓
EmailService.download_attachments()  # Guarda a TEMP_DIR
    ↓
CoosaludProcessor.process()  # Identifica pares DETALLE/GLOSA
    ↓
    identify_files() → validate_files() → extract_data()
    ↓
    homologate() usando HomologacionService.get_homologador_df()
    ↓
    save_results() → \\MINERVA\Cartera\GLOSAAP\COOSALUD\
    ↓
UI muestra toast éxito + abre carpeta
```

## Convenciones Críticas (Violación = Bug Seguro)

### 1. Rutas de Red: Usar SIEMPRE Constantes
```python
# ✅ CORRECTO
from app.config.settings import NETWORK_PATHS, HOMOLOGADOR_FILES
output_dir = NETWORK_PATHS["coosalud_output"]  # \\MINERVA\Cartera\GLOSAAP\COOSALUD

# ❌ INCORRECTO - Nunca hardcodear
output_dir = r"\\MINERVA\Cartera\GLOSAAP\COOSALUD"  # NO!
```
- **Validar acceso red** con `check_network_access()` antes de E/S (evita crashes en VPN caída)
- Rutas UNC `\\SERVIDOR\` son **críticas** (app corre en red corporativa Windows)

### 2. Sistema de Temas Flet: Colores Dinámicos
```python
# ✅ CORRECTO - Colores reactivos al tema
from app.ui.styles import get_colors, ThemeManager
colors = get_colors()  # Retorna dict según tema actual
btn = ft.ElevatedButton(bgcolor=colors["primary"], color=colors["on_primary"])

# ❌ INCORRECTO - Colores literales rompen tema oscuro
btn = ft.ElevatedButton(bgcolor="#2563eb", color="#ffffff")  # NO!
```
- **ThemeManager.toggle_theme(page)** cambia tema + persiste con `client_storage`
- **Después de toggle**: llamar `update_colors()` para actualizar dict global `COLORS`
- Tema persiste entre sesiones (SQLite local vía Flet)

### 3. Navegación con Estado: NavigationController
```python
# app.py define app_state global y NavigationController
app_state = {
    "selected_eps": "COOSALUD",  # EPS activa (ver EPS_CONFIG en eps_config.py)
    "date_from": datetime.now(),
    "date_to": datetime.now(),
    "found_messages": [],        # Lista de Message objects del IMAP
    "dashboard_action": "manejar_glosa"  # Acción pendiente
}

# Navegación centralizada (no manual show/hide)
nav_controller.go_to("dashboard")  # Auto-oculta otras, ajusta window size
nav_controller.go_to("messages", state={"eps": "COOSALUD"})
```
- **Cada vista** implementa `show()`/`hide()` para gestionar `container.visible`
- **app_state** es el contexto compartido (no usar variables globales adicionales)
- Ver [app.py L84-92](app/ui/app.py#L84-L92) para estructura de app_state

### 4. Procesadores de EPS: Patrón Template Method Extensible
```python
# base_processor.py define el contrato
class BaseProcessor(ABC):
    @abstractmethod
    def identify_files(self, paths: List[str]) -> Dict: pass
    @abstractmethod
    def validate_files(self, files: Dict) -> bool: pass
    @abstractmethod
    def extract_data(self, files: Dict) -> pd.DataFrame: pass
    @abstractmethod
    def homologate(self, data: pd.DataFrame) -> pd.DataFrame: pass
    @abstractmethod
    def save_results(self, data: pd.DataFrame, output_dir: str): pass
```

**Ejemplo real: CoosaludProcessor**
- Lee **pares** `DETALLE FC*.xlsx` + `GLOSA FC*.xlsx` (mismo número de factura)
- Hace merge por `id_detalle` (columna clave)
- Homologa códigos con `homologador_df` (join por 'Código Servicio de la ERP')
- Genera **2 salidas**: `ObjecionesArchivo.xlsx` + `ObjecionesError.xlsx`
- Ver [coosalud_processor.py](app/service/processors/coosalud_processor.py) como referencia

**Para agregar nueva EPS**:
1. Crear `app/service/processors/{eps}_processor.py` heredando de `BaseProcessor`
2. Implementar los 5 métodos abstractos (ver [DEVELOPER_GUIDE.md](docs/DEVELOPER_GUIDE.md))
3. Registrar en `EPS_CONFIG` ([eps_config.py](app/config/eps_config.py)):
   ```python
   "nueva_eps": {
       "name": "Nueva EPS",
       "processor": "app.service.processors.nueva_eps_processor.NuevaEpsProcessor",
       "imap_keywords": ["glosa", "objecion"],
       "has_web_scraper": False
   }
   ```

### 5. Web Scrapers: Playwright Headless
```python
# base_scraper.py interface
class BaseScraper(ABC):
    @abstractmethod
    def scrape(self, username: str, password: str) -> List[str]:
        """Retorna lista de rutas a archivos descargados"""
        pass
```

**Ejemplo: FamiliarScraper** ([familiar_scraper.py](app/service/web_scraper/familiar_scraper.py))
- Usa `playwright.sync_api` en modo headless
- **Navegadores pre-instalados** en `PLAYWRIGHT_BROWSERS_PATH` (configurado en settings.py)
- **Credenciales**: `CredentialManager` con encriptación Fernet (nunca en código)
- Descarga archivos a `TEMP_DIR` y retorna rutas

**Setup Playwright (solo primera vez)**:
```powershell
playwright install chromium  # Instala navegador en .venv/playwright
```

**Patrones comunes**:
- `page.wait_for_selector()` para elementos dinámicos
- `page.wait_for_load_state("networkidle")` tras navegación
- Guardar sesión con `context.storage_state()` para evitar re-login

## Comandos de Desarrollo

### Setup y Ejecución
```powershell
# Crear y activar entorno virtual
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# Instalar dependencias
pip install -r requirements.txt
pip install -r requirements-dev.txt  # Para testing (pytest, ruff, etc.)

# Instalar navegadores Playwright (solo primera vez)
playwright install chromium

# Ejecutar aplicación en modo desarrollo
python main.py

# Revisar logs en tiempo real
Get-Content -Path "logs\glosaap.log" -Wait  # PowerShell
# O abrir logs/glosaap.log con editor
```

### Testing
```powershell
# Ejecutar todos los tests
pytest

# Test específico con verbose
pytest tests/test_coosalud_processor.py -v

# Con coverage
pytest --cov=app --cov-report=html

# Ver resultados coverage
start htmlcov/index.html  # Windows
```

**Fixtures importantes** ([conftest.py](tests/conftest.py)):
- `sample_detalle_df`, `sample_glosa_df`: DataFrames Excel simulados
- `sample_homologador_df`: Tabla de homologación de prueba
- `temp_excel_file`, `mock_file_pairs`: Archivos Excel temporales en `tmp_path`
- Los tests **NO ensucian** workspace (usan `tmp_path` de pytest)

### Linting y Formato
```powershell
# Ruff: linter + formatter (reemplaza flake8, black, isort)
ruff check .              # Verificar errores
ruff check . --fix        # Auto-fix problemas
ruff format .             # Formatear código

# Configuración en pyproject.toml:
# - line-length = 120
# - Python 3.10+ target
# - Ignora E501 (line too long), B008, E722
```

### Build y Release
```powershell
# Build ejecutable portable (PyInstaller)
python build.py
# Salida: dist/Glosaap.exe + release/Glosaap_v{VERSION}_{TIMESTAMP}/

# Publicar release a GitHub (requiere GITHUB_TOKEN en .env)
python release.py
# Workflow:
# 1. Lee VERSION de settings.py
# 2. Crea tag git v{VERSION}
# 3. Sube a GitHub Releases con CHANGELOG.md
# 4. Adjunta ZIP del build como asset

# Updater independiente (se incluye en release)
python build.py --updater-only  # Genera dist/updater.exe
```

**Versionado** ([settings.py L14](app/config/settings.py#L14)):
```python
APP_VERSION = "0.11.15"  # Formato semver: MAJOR.MINOR.PATCH
```
- Cambiar **manualmente** antes de build/release
- `build.py` detecta versión automáticamente
- `release.py` crea tag `v{VERSION}` en git

## Patrones de UI (Flet)

### Anatomía de una Vista
```python
class NewView:
    def __init__(self, page: ft.Page, nav_controller, app_state):
        self.page = page
        self.nav = nav_controller
        self.state = app_state
        self.container = ft.Container(visible=False)  # Inicialmente oculto
    
    def show(self):
        """Hace visible la vista y actualiza colores según tema actual"""
        colors = get_colors()  # Obtener colores dinámicos
        self.container.visible = True
        self.page.update()
    
    def hide(self):
        """Oculta la vista"""
        self.container.visible = False
```

**Ciclo de vida de vista**:
1. Constructor: Define estructura UI, bindea callbacks
2. `show()`: Actualiza colores, hace visible, refresh data si es necesario
3. Usuario interactúa → Callbacks modifican `app_state` o llaman servicios
4. `hide()`: Oculta vista, NO destruye (mantiene estado)

### Sistema de Colores Flet
```python
# ThemeManager usa ColorScheme nativo de Flet (no dict custom)
# Tema DARK (styles.py L39-53)
cls._page.dark_theme = ft.Theme(
    color_scheme=ft.ColorScheme(
        primary="#3b82f6",           # Azul vibrante
        on_primary="#ffffff",
        surface="#161b22",           # GitHub dark surface
        on_surface="#e6edf3",
        background="#0d1117",        # GitHub dark bg
        error="#f87171"
    )
)

# Tema LIGHT (styles.py L55-68)
cls._page.theme = ft.Theme(
    color_scheme=ft.ColorScheme(
        primary="#2563eb",           # Azul profesional
        on_primary="#ffffff",
        surface="#ffffff",
        on_surface="#1e293b",
        background="#f6f8fa",
        error="#ef4444"
    )
)

# Acceder en componentes
colors = get_colors()  # Retorna page.theme/dark_theme.color_scheme
ft.Container(
    bgcolor=colors["surface"],
    border=ft.border.all(1, colors["outline"])
)
```

### Componentes Reutilizables
- **AlertDialog** ([alert_dialog.py](app/ui/components/alert_dialog.py)):
  ```python
  from app.ui.components.alert_dialog import show_alert
  show_alert(page, "Error", "Archivo no encontrado", "error")
  # Tipos: "info", "warning", "error", "success"
  ```

- **UpdateChecker** ([update_dialog.py](app/ui/components/update_dialog.py)):
  ```python
  # Verificación automática en startup (app.py)
  if AUTO_UPDATE_CONFIG["check_on_startup"]:
      UpdateChecker.check_for_updates(page, show_always=False)
  ```

- **ProgressRing/Spinner** (loading común):
  ```python
  self.loading = ft.ProgressRing(visible=False)
  # Al iniciar operación larga:
  self.loading.visible = True
  page.update()
  # Al terminar:
  self.loading.visible = False
  ```

### Manejo de Estados Asíncronos
Flet NO tiene async/await nativo. Para operaciones largas:
```python
import threading

def long_operation():
    # Simular procesamiento largo
    result = email_service.search_messages(...)
    # Actualizar UI en thread principal
    def update_ui():
        self.result_text.value = f"Encontrados: {len(result)}"
        self.loading.visible = False
        page.update()
    page.run_thread_safe(update_ui)

# Ejecutar en background
threading.Thread(target=long_operation, daemon=True).start()
```

**Patrón típico en app.py**:
1. Mostrar `loading_overlay`
2. Lanzar `threading.Thread` con operación
3. Thread llama `page.run_thread_safe()` para actualizar UI
4. Ocultar overlay, mostrar resultado/error

## Dependencias Externas
- **Flet 0.27.6**: Framework UI declarativo (no confundir con Streamlit/Tkinter)
  - Usa Flutter engine pero API Python
  - `ft.Page` es el contenedor raíz
  - `page.update()` refresca UI (no automático como React)
- **Playwright**: Automatización navegadores (web scraping)
  - Navegadores se instalan en `.venv` con `playwright install chromium`
  - `PLAYWRIGHT_BROWSERS_PATH` configurado automáticamente en settings.py
- **pandas/openpyxl**: Manipulación Excel (crítico para EPS)
  - openpyxl para lectura/escritura `.xlsx`
  - pandas para transformaciones DataFrame
- **cryptography**: Encriptación credenciales con Fernet
  - Keys en `CredentialManager` (nunca en código)
- **PyInstaller**: Build ejecutable portable Windows
  - `--onefile` genera un solo `.exe`
  - `--add-data` incluye assets/app folders

## Problemas Comunes

### Error "Navegadores Playwright no encontrados"
```python
# settings.py configura automáticamente:
os.environ["PLAYWRIGHT_BROWSERS_PATH"] = str(PLAYWRIGHT_BROWSERS_PATH)
# Si persiste, ejecutar manualmente:
# playwright install chromium
```

### Error "No se puede acceder a \\MINERVA"
- Validar VPN/acceso red corporativa
- Verificar con `check_network_access()` antes de procesar
- Tests mockean rutas red con `tmp_path` (no requieren \\MINERVA)

### Theme no actualiza UI después de toggle
```python
ThemeManager.toggle_theme(page)
update_colors()  # ¡CRÍTICO! Actualiza COLORS global
# Re-crear componentes si es necesario (algunos cacheados)
page.update()
```

### PyInstaller no incluye archivos
```python
# Verificar en build.py:
"--add-data", "app;app",      # Incluye todo app/ en bundle
"--add-data", "assets;assets" # Incluye assets/ en bundle
# Para dependencias hidden:
"--hidden-import", "module_name"
```

### Tests fallan por rutas de red
```python
# Tests deben usar tmp_path fixture, nunca NETWORK_PATHS
def test_processor(tmp_path, sample_detalle_df):
    output_dir = tmp_path / "output"
    processor.save_results(data, str(output_dir))
    assert (output_dir / "result.xlsx").exists()
```

## Prioridades al Modificar Código
1. **Mantener separación de capas** (UI no debe llamar directamente a IMAPClient, usar EmailService)
2. **Usar constantes de settings.py** para rutas/configuración (NUNCA hardcodear)
3. **Respetar patrón BaseProcessor** para nuevos procesadores (5 métodos abstractos)
4. **Actualizar tests** al cambiar lógica core/services (mantener >80% coverage)
5. **Documentar en CHANGELOG.md** cambios importantes (seguir formato Keep a Changelog)
6. **Threading seguro en Flet**: Usar `page.run_thread_safe()` para actualizar UI desde threads

## Referencias Rápidas
- **Estado Global**: `app_state` dict en [app.py L84-92](app/ui/app.py#L84) (selected_eps, dates, messages, dashboard_action)
- **Logging**: Configurado en [settings.py L102-137](app/config/settings.py#L102), output a `logs/glosaap.log` con rotación
- **EPS Soportadas**: `EPS_CONFIG` en [eps_config.py](app/config/eps_config.py) (MUTUALSER, COOSALUD, FAMILIAR, FOMAG)
- **Homologación CRUD**: [homologacion_service.py](app/core/homologacion_service.py) (SQLite en TEMP_DIR)
- **Convenciones Git**: [GUIA_GIT_CAMBIOS.md](docs/GUIA_GIT_CAMBIOS.md) para flujo de trabajo
- **Manual Usuario**: [MANUAL_USUARIO.md](docs/MANUAL_USUARIO.md) para documentar features

---

**Nota**: Este proyecto requiere acceso a recursos corporativos (red `\\MINERVA`). Para desarrollo local sin acceso, mockear rutas de red en tests con `tmp_path` fixture.
