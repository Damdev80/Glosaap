# 🛠️ Guía del Desarrollador - Glosaap

> **Documento técnico para desarrolladores**  
> Última actualización: Enero 2026

---
## 📁 Estructura del Proyecto

```
Glosaap/
├── main.py                    # Punto de entrada de la aplicación
├── app/
│   ├── config/                # Configuraciones centralizadas
│   │   ├── settings.py        # ⚠️ CRÍTICO - Rutas y constantes globales
│   │   └── eps_config.py      # ⚠️ CRÍTICO - Configuración de cada EPS
│   │
│   ├── core/                  # Lógica de negocio principal
│   │   ├── imap_client.py     # Cliente IMAP para conexión a correos
│   │   ├── homologacion_service.py  # CRUD de archivos de homologación
│   │   ├── mutualser_processor.py   # Procesador específico de Mutualser
│   │   └── web_scraper.py     # Scraping web (deprecated)
│   │
│   ├── service/               # Servicios de alto nivel
│   │   ├── email_service.py   # ⭐ Orquestador principal de emails
│   │   ├── attachment_service.py  # Gestión de adjuntos
│   │   ├── processors/        # Procesadores por EPS
│   │   │   ├── base_processor.py  # 📌 Clase base abstracta
│   │   │   └── coosalud_processor.py
│   │   └── web_scraper/       # Scrapers de portales web
│   │       ├── base_scraper.py    # 📌 Clase base abstracta
│   │       ├── familiar_scraper.py
│   │       └── fomag_scraper.py
│   │
│   └── ui/                    # Interfaz gráfica (Flet)
│       ├── app.py             # ⭐ Aplicación principal y navegación
│       ├── styles.py          # Colores, tamaños, estilos
│       ├── components/        # Componentes reutilizables
│       └── views/             # Pantallas de la aplicación
│
├── assets/                    # Recursos estáticos
│   ├── icons/                 # Iconos de la app
│   └── img/eps/               # Logos de las EPS
│
└── temp/                      # Archivos temporales (gitignore)
```

---

## 🔑 Archivos Críticos - NO MODIFICAR SIN ENTENDER

### 1. `app/config/settings.py`
**Propósito:** Configuración centralizada de rutas y constantes.

```python
# Rutas de red (servidor MINERVA)
NETWORK_BASE = r"\\MINERVA\Cartera\GLOSAAP"

NETWORK_PATHS = {
    "homologador": "...",      # Archivos Excel de homologación
    "resultados": "...",       # Donde se guardan los resultados
    "mutualser_output": "...", # Resultados de Mutualser
    "coosalud_output": "...",  # Resultados de Coosalud
}
```

⚠️ **CUIDADO:** Si cambias las rutas de red, la app no encontrará los archivos de homologación.

---

### 2. `app/config/eps_config.py`
**Propósito:** Define cada EPS con su configuración.

```python
class MutualserEps(EpsInfo):
    def __init__(self):
        super().__init__(
            name="Mutualser",
            filter_value="mutualser",           # Clave única de la EPS
            subject_pattern="Objeciones de glosa Factura FC",  # Patrón en asunto
            processor_class="MutualserProcessor",  # Clase que procesa
            homologador_file="HOMOLOGADOR_MUTUALSER.xlsx",  # Archivo en red
            sender_filter=None  # Filtrar por remitente (opcional)
        )
```

#### 📌 Para agregar una nueva EPS:

1. **Crear la clase** en `eps_config.py`:
   ```python
   class NuevaEpsConfig(EpsInfo):
       def __init__(self):
           super().__init__(
               name="Nueva EPS",
               filter_value="nuevaeps",
               subject_pattern="PATRÓN DEL ASUNTO",
               processor_class="NuevaEpsProcessor",
               homologador_file="HOMOLOGADOR_NUEVAEPS.xlsx",
               sender_filter="correo@nuevaeps.com"  # Opcional
           )
   ```

2. **Agregar al registro** al final de `eps_config.py`:
   ```python
   EPS_REGISTRY["nuevaeps"] = NuevaEpsConfig()
   ```

3. **Crear el procesador** (ver sección de procesadores abajo).

---

## 🔧 Servicios Principales

### `EmailService` - El Orquestador
**Ubicación:** `app/service/email_service.py`

Este servicio coordina todo el flujo de correos:

```python
email_service = EmailService()

# 1. Conectar al servidor IMAP
email_service.connect(email, password, server="imap.gmail.com")

# 2. Buscar mensajes por palabra clave
mensajes = email_service.search_messages(
    keyword="Objeciones de glosa",
    date_from="2025-01-01",
    date_to="2025-12-31",
    limit=None  # Sin límite
)

# 3. Descargar adjuntos
stats = email_service.download_all_attachments(
    messages=mensajes,
    on_progress=lambda idx, total, msg, files: print(f"{idx}/{total}")
)

# 4. Procesar archivos Excel
resultado = email_service.process_mutualser_files()
```

#### Métodos importantes:
| Método | Descripción |
|--------|-------------|
| `connect()` | Conecta al servidor IMAP |
| `search_messages()` | Busca correos por asunto/fecha |
| `download_all_attachments()` | Descarga todos los adjuntos |
| `get_excel_files()` | Lista archivos Excel descargados |
| `process_mutualser_files()` | Procesa y homologa archivos |

---

### `ImapClient` - Conexión a Correo
**Ubicación:** `app/core/imap_client.py`

Cliente de bajo nivel para IMAP. **No modificar** a menos que entiendas el protocolo IMAP.

```python
# Auto-detecta servidor IMAP por dominio del correo
client = ImapClient()
client.connect("usuario@gmail.com", "password")

# Buscar por asunto con rango de fechas
mensajes = client.search_by_subject(
    keyword="glosa",
    date_from=datetime(2025, 1, 1),
    date_to=datetime(2025, 12, 31)
)

# Descargar adjuntos de un mensaje
archivos = client.download_attachments(mensaje_id, dest_dir="./temp")
```

#### ⚠️ NO MODIFICAR:
- Función `_decode_header()` - Maneja encoding de headers
- Formato de fechas IMAP (`DD-Mon-YYYY`)
- Lógica de timeout en `search_by_subject()`

---

### `HomologacionService` - CRUD de Homologación
**Ubicación:** `app/core/homologacion_service.py`

Gestiona los archivos Excel de homologación por EPS.

```python
# Inicializar para una EPS
service = HomologacionService(eps="mutualser")

# Operaciones CRUD
service.agregar_codigo("123456", "789012", "COD_FACT")
service.buscar_por_codigo("123456")
service.editar_registro(indice=5, nuevos_valores={...})
service.eliminar_registro(indice=5)

# Guardar cambios (crea backup automático)
service.guardar()
```

#### Columnas requeridas en Excel:
```python
COLUMNAS = [
    'Código Servicio de la ERP',    # Código original
    'Código producto en DGH',       # Código homologado
    'COD_SERV_FACT'                 # Código de facturación
]
```

---

## � Componentes de UI y Feedback Visual

### Nuevos Componentes de Loading (v1.0.0)
**Ubicación:** `app/ui/components/loading_overlay.py`

#### 1. LoadingOverlay - Overlay Modal
Capa semi-transparente que bloquea la interfaz durante operaciones:

```python
from app.ui.components.loading_overlay import LoadingOverlay

# En tu vista:
def __init__(self, page: ft.Page):
    self.loading_overlay = LoadingOverlay(page)

# Usar con operaciones largas:
def async_operation(self):
    self.loading_overlay.show("Procesando archivos...")
    try:
        # Tu operación aquí
        await process_files()
    finally:
        self.loading_overlay.hide()

# O usar con context manager:
def sync_operation(self):
    with self.loading_overlay.context("Cargando datos..."):
        data = fetch_data()
```

#### 2. ToastNotification - Notificaciones No-bloqueantes
Notificaciones temporales estilo "toast":

```python
from app.ui.components.loading_overlay import ToastNotification

# En tu vista:
def __init__(self, page: ft.Page):
    self.toast = ToastNotification(page)

# Mostrar mensajes:
self.toast.show("¡Operación exitosa!", True)   # Verde (éxito)
self.toast.show("Error de conexión", False)    # Rojo (error)
```

#### 3. LoadingButton - Botón con Estado de Carga
Botón que muestra spinner cuando está procesando:

```python
from app.ui.components.loading_overlay import LoadingButton

# Crear botón:
self.login_button = LoadingButton(
    text="Iniciar Sesión",
    icon=ft.Icons.LOGIN,
    on_click=self._handle_login,
    width=380,
    height=52
)

# Usar en operaciones:
def _handle_login(self, e):
    self.login_button.set_loading(True, "Conectando...")
    try:
        await connect_to_server()
        self.login_button.set_loading(False)
    except Exception as ex:
        self.login_button.set_loading(False)
        # Manejar error
```

#### 4. ProgressIndicator - Indicador de Progreso
Barra de progreso con porcentaje:

```python
from app.ui.components.loading_overlay import ProgressIndicator

# Crear indicador:
self.progress = ProgressIndicator()

# Actualizar progreso:
def process_files(self, files):
    total = len(files)
    for i, file in enumerate(files):
        self.progress.update(i, total, f"Procesando {file}")
        process_file(file)
    self.progress.update(total, total, "¡Completado!")
```

#### 🎯 Patrones de Uso Recomendados

**1. Vista de Login:**
```python
class LoginView:
    def __init__(self, page: ft.Page):
        self.loading_overlay = LoadingOverlay(page)
        self.toast_notification = ToastNotification(page)
        self.login_button = LoadingButton("Iniciar Sesión", ...)
    
    def _handle_login(self, e):
        # Usar LoadingButton para feedback inmediato
        self.login_button.set_loading(True, "Conectando...")
        # Usar overlay para bloquear UI
        self.loading_overlay.show("Conectando al servidor IMAP...")
        
        def connect_worker():
            try:
                connect()
                self.login_button.set_loading(False)
                self.loading_overlay.hide()
                self.toast_notification.show("¡Conexión exitosa!")
            except Exception as ex:
                self.login_button.set_loading(False)
                self.loading_overlay.hide()
                self.toast_notification.show(f"Error: {ex}", False)
```

**2. Vista de Mensajes:**
```python
class MessagesView:
    def show_loading(self, message: str):
        self.loading_overlay.show(message)
    
    def hide_loading(self):
        self.loading_overlay.hide()
    
    def show_toast(self, message: str, is_success: bool = True):
        self.toast_notification.show(message, is_success)
    
    def set_loading_progress(self, current: int, total: int, message: str = ""):
        if total > 0:
            progress = current / total
            self.processing_progress.value = progress
            self.processing_percentage.value = f"{int(progress * 100)}%"
        
        if message:
            self.processing_status.value = message
        
        self.page.update()
```

#### ⚠️ Consideraciones Importantes

1. **Thread Safety:** Los componentes son seguros para usar con threading
2. **Performance:** Usa `context manager` para operaciones síncronas cortas
3. **UX:** Siempre proporciona mensajes descriptivos al usuario
4. **Error Handling:** Siempre oculta loading en bloques finally
5. **Consistencia:** Usa los mismos componentes en toda la aplicación

---

### Integración en Vistas Existentes

**Pasos para integrar:**

1. **Importar componentes:**
```python
from app.ui.components.loading_overlay import LoadingOverlay, ToastNotification, LoadingButton
```

2. **Inicializar en constructor:**
```python
def __init__(self, page: ft.Page):
    self.loading_overlay = LoadingOverlay(page)
    self.toast_notification = ToastNotification(page)
```

3. **Usar en métodos:**
```python
def process_data(self):
    self.loading_overlay.show("Procesando...")
    try:
        # Tu lógica aquí
        pass
    finally:
        self.loading_overlay.hide()
```

---

## �🏭 Procesadores de EPS

### Clase Base - `BaseProcessor`
**Ubicación:** `app/service/processors/base_processor.py`

Define la interfaz que **TODO procesador debe implementar**:

```python
from abc import ABC, abstractmethod

class BaseProcessor(ABC):
    
    @abstractmethod
    def identify_files(self, file_paths: List[str]) -> Dict[str, str]:
        """Identifica y clasifica archivos de entrada"""
        pass
    
    @abstractmethod
    def validate_files(self, identified_files: Dict[str, str]) -> bool:
        """Valida que los archivos sean correctos"""
        pass
    
    @abstractmethod
    def extract_data(self, identified_files: Dict[str, str]) -> Dict[str, pd.DataFrame]:
        """Extrae datos de los archivos"""
        pass
    
    @abstractmethod
    def homologate(self, data: Dict[str, pd.DataFrame]) -> pd.DataFrame:
        """Realiza homologación de códigos"""
        pass
    
    @abstractmethod
    def generate_output(self, df_homologated: pd.DataFrame) -> str:
        """Genera archivo de salida"""
        pass
```

### Crear un Nuevo Procesador

1. **Crear archivo** `app/service/processors/nuevaeps_processor.py`:

```python
from app.service.processors.base_processor import BaseProcessor
import pandas as pd

class NuevaEpsProcessor(BaseProcessor):
    
    # Columnas que debe tener el archivo de esta EPS
    COLUMNAS_REQUERIDAS = ['Factura', 'Codigo', 'Valor', 'Glosa']
    
    def __init__(self, output_dir: str = 'outputs'):
        homologador = r"\\MINERVA\Cartera\GLOSAAP\HOMOLOGADOR\nuevaeps_homologacion.xlsx"
        super().__init__(homologador_path=homologador)
        self.output_dir = output_dir
    
    def identify_files(self, file_paths):
        # Tu lógica para identificar archivos
        return {"detalle": file_paths[0]}
    
    def validate_files(self, identified_files):
        # Validar que existan las columnas requeridas
        return True
    
    def extract_data(self, identified_files):
        df = pd.read_excel(identified_files["detalle"])
        return {"detalle": df}
    
    def homologate(self, data):
        df = data["detalle"]
        # Tu lógica de homologación
        return df
    
    def generate_output(self, df_homologated):
        output_path = f"{self.output_dir}/resultado_nuevaeps.xlsx"
        df_homologated.to_excel(output_path, index=False)
        return output_path
```

2. **Registrar en `__init__.py`**:
```python
# app/service/processors/__init__.py
from .nuevaeps_processor import NuevaEpsProcessor
```

3. **Agregar a EPS_REGISTRY** (ver sección de eps_config.py arriba)

---

## 🌐 Web Scrapers

### Clase Base - `BaseScraper`
**Ubicación:** `app/service/web_scraper/base_scraper.py`

Para automatización de portales web de EPS.

```python
class BaseScraper(ABC):
    
    def __init__(self, download_dir: str = None, progress_callback = None):
        self.download_dir = download_dir or "~/Desktop/descargas_glosaap"
        self.progress_callback = progress_callback or print
    
    def log(self, message: str):
        """Envía mensaje de progreso"""
        self.progress_callback(message)
    
    @abstractmethod
    def login_and_download(self, **kwargs) -> dict:
        """
        Ejecuta login y descarga
        Returns: {"success": bool, "files": int, "message": str}
        """
        pass
```

### Ejemplo de Scraper (Playwright)

```python
from playwright.sync_api import sync_playwright
from app.service.web_scraper.base_scraper import BaseScraper

class MiEpsScraper(BaseScraper):
    
    def login_and_download(self, usuario: str, password: str) -> dict:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=False)
            page = browser.new_page()
            
            self.log("Navegando al portal...")
            page.goto("https://portal.mieps.com")
            
            self.log("Iniciando sesión...")
            page.fill("#usuario", usuario)
            page.fill("#password", password)
            page.click("#btnLogin")
            
            self.log("Descargando archivos...")
            # Tu lógica de descarga...
            
            browser.close()
            
        return {"success": True, "files": 5, "message": "Descarga exitosa"}
```

---

## 🖼️ Interfaz de Usuario (Flet)

### Archivo Principal - `app/ui/app.py`

Contiene la función `main(page)` y toda la navegación:

```python
def main(page: ft.Page):
    # Configuración inicial
    page.title = "Glosaap"
    page.bgcolor = COLORS["bg_white"]
    
    # Servicios
    email_service = EmailService()
    
    # Funciones de navegación
    def go_to_login(): ...
    def go_to_dashboard(): ...
    def go_to_tools(): ...
    # ... más funciones go_to_*
    
    # Instanciar vistas
    login_view = LoginView(page, ...)
    dashboard_view = DashboardView(page, ...)
    # ... más vistas
    
    # Agregar todo a la página
    page.add(login_view.container, dashboard_view.container, ...)
```

### Crear una Nueva Vista

1. **Crear archivo** `app/ui/views/mi_vista.py`:

```python
import flet as ft
from app.ui.styles import COLORS, FONT_SIZES

class MiVista:
    """Descripción de la vista"""
    
    def __init__(self, page: ft.Page, on_back=None, on_action=None):
        self.page = page
        self.on_back = on_back
        self.on_action = on_action
        self.container = self.build()
    
    def build(self) -> ft.Container:
        return ft.Container(
            content=ft.Column([
                ft.Text("Mi Vista", size=24, weight=ft.FontWeight.BOLD),
                ft.ElevatedButton("Acción", on_click=self._handle_action),
                ft.TextButton("Volver", on_click=lambda _: self.on_back())
            ]),
            visible=False,  # Inicialmente oculta
            padding=20
        )
    
    def _handle_action(self, e):
        if self.on_action:
            self.on_action()
    
    def show(self):
        self.container.visible = True
    
    def hide(self):
        self.container.visible = False
```

---

## 🧪 Testing y Cobertura de Código

### Estado Actual de Tests
- **Total de tests:** 431 tests pasando ✅
- **Cobertura actual:** 31.02%
- **Archivos de test:** 23 archivos

### Estructura de Tests

```
tests/
├── test_app.py                    # Tests de la aplicación principal
├── test_app_state.py             # Tests del estado global
├── test_attachment_service.py    # Tests del servicio de adjuntos
├── test_auth_service.py          # Tests del servicio de autenticación
├── test_base_scraper.py          # Tests del scraper base
├── test_business_logic.py        # Tests de lógica de negocio
├── test_coosalud_processor.py    # Tests del procesador Coosalud
├── test_credential_manager.py    # Tests del gestor de credenciales
├── test_email_service.py         # Tests del servicio de email
├── test_eps_config.py            # Tests de configuración EPS
├── test_homologacion_service.py  # Tests del servicio de homologación
├── test_homologar_observacion.py # Tests del homologador observación
├── test_imap_client.py           # Tests del cliente IMAP
├── test_mix_excel_service.py     # Tests del servicio Mix Excel
├── test_mutualser_processor.py   # Tests del procesador Mutualser
├── test_navigation.py            # Tests de navegación UI
├── test_processors.py            # Tests de procesadores generales
├── test_session_manager.py       # Tests del gestor de sesiones
├── test_settings.py              # Tests de configuración
├── test_styles.py                # Tests de estilos UI
└── test_update_service.py        # Tests del servicio de actualización
```

### Comandos de Testing

```bash
# Ejecutar todos los tests
pytest tests/

# Ejecutar con cobertura
pytest tests/ --cov=app --cov-report=html

# Ejecutar tests específicos
pytest tests/test_coosalud_processor.py -v

# Ejecutar tests con patrón
pytest tests/ -k "test_login" -v

# Ver reporte de cobertura
pytest tests/ --cov=app --cov-report=term-missing
```

### Configuración de Pytest (pytest.ini)
```ini
[tool:pytest]
testpaths = tests
python_files = test_*.py
python_functions = test_*
python_classes = Test*
addopts = 
    -v 
    --tb=short 
    --strict-markers
    --disable-warnings
    --cov=app
    --cov-report=html:htmlcov
    --cov-report=term-missing
    --cov-fail-under=15
```

### Buenas Prácticas para Tests

#### 1. Estructura de Test
```python
class TestComponentName:
    """Tests para ComponentName."""
    
    def test_creation(self):
        """El componente se crea correctamente"""
        component = ComponentName()
        assert component is not None
    
    def test_functionality(self):
        """La funcionalidad principal funciona"""
        component = ComponentName()
        result = component.do_something()
        assert result == expected_value
```

#### 2. Usar Mocking para Dependencias
```python
from unittest.mock import Mock, patch, MagicMock

@patch('app.service.external_service.ExternalAPI')
def test_with_external_dependency(self, mock_api):
    mock_api.return_value.fetch_data.return_value = {"data": "test"}
    
    service = MyService()
    result = service.process_data()
    
    assert result["data"] == "test"
    mock_api.return_value.fetch_data.assert_called_once()
```

#### 3. Tests Parametrizados
```python
import pytest

@pytest.mark.parametrize("input_value,expected", [
    ("test@gmail.com", "imap.gmail.com"),
    ("user@outlook.com", "outlook.office365.com"),
    ("admin@empresa.com", "mail.empresa.com"),
])
def test_detect_imap_server(self, input_value, expected):
    client = ImapClient()
    result = client._detect_imap_server(input_value)
    assert result == expected
```

#### 4. Fixtures para Setup/Teardown
```python
import pytest
import tempfile

@pytest.fixture
def temp_excel_file(tmp_path):
    """Crea archivo Excel temporal para tests"""
    file_path = tmp_path / "test.xlsx"
    df = pd.DataFrame({'col1': [1, 2], 'col2': ['a', 'b']})
    df.to_excel(file_path, index=False)
    return str(file_path)

def test_load_excel(self, temp_excel_file):
    service = ExcelService()
    result = service.load_file(temp_excel_file)
    assert result.success is True
```

### Cobertura por Módulos

| Módulo | Cobertura | Estado |
|--------|-----------|--------|
| app_state.py | 100% | ✅ Completo |
| eps_config.py | 100% | ✅ Completo |
| styles.py | 100% | ✅ Completo |
| settings.py | 92% | ✅ Alto |
| base_scraper.py | 93% | ✅ Alto |
| session_manager.py | 78% | ⚠️ Bueno |
| navigation.py | 69% | ⚠️ Bueno |
| auth_service.py | 64% | ⚠️ Medio |
| credential_manager.py | 61% | ⚠️ Medio |
| update_service.py | 52% | ⚠️ Medio |
| coosalud_processor.py | 43% | ❌ Bajo |
| homologacion_service.py | 18% | ❌ Muy bajo |

### Objetivos de Cobertura
- **Meta actual:** 31% → 50%
- **Prioridad 1:** Servicios principales (email, auth, attachment)
- **Prioridad 2:** Procesadores (coosalud, mutualser)
- **Prioridad 3:** UI components y navegación

---

## 📚 Documentación y Docstrings

### Formato de Docstrings
Seguimos el estilo Google para docstrings:

```python
def process_file(self, file_path: str, options: dict = None) -> dict:
    """
    Procesa un archivo Excel y extrae datos relevantes.
    
    Este método analiza un archivo Excel, valida su estructura,
    extrae los datos según las opciones proporcionadas y retorna
    un diccionario con el resultado del procesamiento.
    
    Args:
        file_path (str): Ruta absoluta al archivo Excel a procesar.
        options (dict, optional): Opciones de configuración.
            - validate_columns (bool): Si validar columnas requeridas.
            - skip_empty_rows (bool): Si saltar filas vacías.
            Default: {"validate_columns": True, "skip_empty_rows": True}
    
    Returns:
        dict: Resultado del procesamiento con las siguientes claves:
            - success (bool): Si el procesamiento fue exitoso.
            - data (pd.DataFrame): Datos extraídos del archivo.
            - errors (list): Lista de errores encontrados.
            - warnings (list): Lista de advertencias.
    
    Raises:
        FileNotFoundError: Si el archivo no existe.
        PermissionError: Si no hay permisos para leer el archivo.
        ValueError: Si el archivo no tiene el formato esperado.
    
    Example:
        >>> processor = FileProcessor()
        >>> result = processor.process_file("/path/to/file.xlsx")
        >>> if result["success"]:
        ...     print(f"Procesados {len(result['data'])} registros")
        ... else:
        ...     print(f"Errores: {result['errors']}")
    
    Note:
        - El archivo debe estar en formato .xlsx o .xls
        - Las columnas requeridas son: 'Código', 'Descripción', 'Valor'
        - El procesamiento puede tardar varios segundos para archivos grandes
    
    Todo:
        - Agregar soporte para archivos CSV
        - Implementar cache para archivos grandes
        - Mejorar validación de tipos de datos
    """
    # Implementación del método
```

### Estado de Documentación

| Componente | Docstrings | Estado |
|------------|------------|--------|
| base_processor.py | ✅ Completo | Documentación completa con ejemplos |
| loading_overlay.py | ✅ Completo | Documentación completa con ejemplos |
| email_service.py | ⚠️ Parcial | Faltan ejemplos en algunos métodos |
| coosalud_processor.py | ⚠️ Parcial | Métodos complejos sin documentar |
| imap_client.py | ❌ Básico | Solo docstrings básicos |

---

## 🚀 Proceso de Release y Versionado

### Versioning Scheme
Seguimos Semantic Versioning (SemVer): `MAJOR.MINOR.PATCH`

- **MAJOR:** Cambios incompatibles de API
- **MINOR:** Nueva funcionalidad compatible hacia atrás  
- **PATCH:** Bug fixes compatibles

### Proceso de Release

1. **Preparar Release:**
```bash
# Actualizar versión en settings.py
APP_VERSION = "0.11.8"

# Ejecutar tests
pytest tests/ --cov=app

# Verificar que todos los tests pasen
```

2. **Crear Release:**
```bash
# Ejecutar script de release
python release.py

# Se crean automáticamente:
# - Tag en Git
# - Build con PyInstaller  
# - Release en GitHub con assets
```

3. **Estructura de Build:**
```
release/
└── Glosaap_v0.11.8/
    ├── Glosaapp.exe          # Aplicación principal
    ├── updater.exe           # Actualizador automático
    └── Glosaap_v0.11.8.zip   # Package para distribución
```

---

## 🛠️ Desarrollo Local
```

2. **Agregar a `app/ui/views/__init__.py`**:
```python
from .mi_vista import MiVista
```

3. **Integrar en `app.py`**:
```python
# En main():
mi_vista = MiVista(
    page=page,
    on_back=go_to_dashboard,
    on_action=lambda: print("Acción!")
)

def go_to_mi_vista():
    # Ocultar otras vistas...
    mi_vista.show()
    page.update()

# Agregar a la página
page.add(..., mi_vista.container)
```

---

## 📋 Estilos - `app/ui/styles.py`

Colores y tamaños centralizados:

```python
COLORS = {
    "primary": "#6366F1",       # Morado principal
    "primary_light": "#818CF8",
    "bg_white": "#FFFFFF",
    "bg_gray": "#F8FAFC",
    "text_primary": "#1E293B",
    "text_secondary": "#64748B",
    "success": "#10B981",
    "error": "#EF4444",
    "warning": "#F59E0B",
}

FONT_SIZES = {
    "xs": 12,
    "sm": 14,
    "md": 16,
    "lg": 18,
    "xl": 24,
    "xxl": 32,
}

WINDOW_SIZES = {
    "login": {"width": 450, "height": 550},
    "dashboard": {"width": 800, "height": 550},
    # ...
}
```

**USAR SIEMPRE** estos valores en lugar de hardcodear:
```python
# ✅ Correcto
ft.Text("Título", color=COLORS["primary"], size=FONT_SIZES["xl"])

# ❌ Incorrecto
ft.Text("Título", color="#6366F1", size=24)
```

---

## ⚠️ Reglas de Oro - NO ROMPER

### 1. Rutas de Red
```python
# SIEMPRE verificar si la ruta existe antes de usarla
if os.path.exists(NETWORK_PATHS["homologador"]):
    # usar ruta de red
else:
    # usar fallback local
```

### 2. DataFrames de Pandas
```python
# SIEMPRE limpiar columnas después de leer Excel
df = pd.read_excel(path)
df.columns = df.columns.str.strip()  # Quitar espacios

# SIEMPRE verificar si columna existe
if 'MiColumna' in df.columns:
    # usar columna
```

### 3. Hilos y Async
```python
# Las operaciones de red/archivo van en hilos separados
import threading

def tarea_lenta():
    # Operación que toma tiempo...
    pass

threading.Thread(target=tarea_lenta).start()
```

### 4. Actualizar UI
```python
# SIEMPRE llamar page.update() después de cambios visuales
self.container.visible = True
self.page.update()  # ¡No olvidar!
```

### 5. Manejo de Errores
```python
try:
    resultado = operacion_riesgosa()
except Exception as e:
    print(f"❌ Error: {e}")
    self.errors.append(str(e))
    # NO dejar que la app crashee
```

---

## 🧪 Testing

### Configuración de Pruebas

El proyecto utiliza **pytest** para las pruebas unitarias con configuración en `pytest.ini`:

```ini
[tool:pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts = --verbose --tb=short --cov=app --cov-report=html --cov-report=term
```

### Ejecutar Pruebas

```bash
# Ejecutar todas las pruebas
python -m pytest

# Con cobertura detallada
python -m pytest --cov=app --cov-report=html

# Test específico
python -m pytest tests/test_processors.py -v

# Ver reporte de cobertura en navegador
# Abrir htmlcov/index.html
```

### Estructura de Tests

**Total de pruebas:** 431 tests pasando
**Cobertura actual:** 31.02%

#### Tests por Módulo

```
tests/
├── test_app_state.py (46 tests)            # Estados de aplicación
├── test_attachment_service.py (11 tests)   # Manejo de archivos adjuntos
├── test_auth_service.py (37 tests)         # Autenticación
├── test_base_processor.py (18 tests)       # Procesador base
├── test_base_scraper.py (19 tests)         # Scraper base
├── test_business_logic.py (42 tests)       # Lógica de negocio
├── test_coosalud_processor.py (17 tests)   # Procesador Coosalud
├── test_credential_manager.py (14 tests)   # Gestión de credenciales
├── test_email_service.py (25 tests)        # Servicios de email
├── test_eps_config.py (27 tests)           # Configuración EPS
├── test_familiar_scraper.py (19 tests)     # Scraper Familiar
├── test_fomag_scraper.py (19 tests)        # Scraper Fomag
├── test_homologacion_service.py (25 tests) # Homologación
├── test_imap_client.py (22 tests)         # Cliente IMAP
├── test_loading_components.py (29 tests)   # Componentes de UI
├── test_mix_excel_service.py (19 tests)    # Servicio Mix Excel
├── test_mutualser_processor.py (17 tests)  # Procesador Mutualser
├── test_navigation.py (17 tests)          # Navegación
├── test_processors.py (8 tests)           # Tests originales
├── test_session_manager.py (20 tests)     # Gestión de sesiones
├── test_settings.py (13 tests)            # Configuraciones
├── test_styles.py (8 tests)               # Estilos UI
└── test_web_scraper.py (20 tests)         # Web scraping
```

#### Escribir Nuevos Tests

**Ejemplo de test para un procesador:**

```python
import pytest
from unittest.mock import Mock, patch
from app.service.processors.nueva_eps_processor import NuevaEpsProcessor

class TestNuevaEpsProcessor:
    
    @pytest.fixture
    def processor(self):
        return NuevaEpsProcessor("test_output")
    
    def test_identify_files_success(self, processor):
        """Test identificación exitosa de archivos"""
        files = ["detalle_nueva.xlsx", "other_file.txt"]
        result = processor.identify_files(files)
        
        assert result is not None
        assert "detalle" in result
        assert result["detalle"] == "detalle_nueva.xlsx"
    
    def test_identify_files_missing(self, processor):
        """Test cuando falta archivo requerido"""
        files = ["wrong_file.txt"]
        result = processor.identify_files(files)
        
        assert result is None
    
    @patch('pandas.read_excel')
    def test_extract_data(self, mock_read_excel, processor):
        """Test extracción de datos con mock"""
        # Setup mock
        mock_df = Mock()
        mock_read_excel.return_value = mock_df
        
        identified_files = {"detalle": "test.xlsx"}
        result = processor.extract_data(identified_files)
        
        assert "detalle" in result
        mock_read_excel.assert_called_once_with("test.xlsx")
```

**Ejemplo de test para componente UI:**

```python
import pytest
import flet as ft
from unittest.mock import Mock, patch
from app.ui.components.loading_overlay import LoadingOverlay

class TestLoadingOverlay:
    
    @pytest.fixture
    def mock_page(self):
        page = Mock(spec=ft.Page)
        page.overlay = []
        page.update = Mock()
        return page
    
    def test_initialization(self, mock_page):
        """Test inicialización correcta"""
        overlay = LoadingOverlay(mock_page)
        
        assert overlay.page == mock_page
        assert overlay.is_visible is False
        assert overlay.overlay_container is not None
    
    def test_show_loading(self, mock_page):
        """Test mostrar loading"""
        overlay = LoadingOverlay(mock_page)
        
        overlay.show("Test message")
        
        assert overlay.is_visible is True
        assert len(mock_page.overlay) == 1
        mock_page.update.assert_called()
    
    def test_hide_loading(self, mock_page):
        """Test ocultar loading"""
        overlay = LoadingOverlay(mock_page)
        overlay.show("Test")
        
        overlay.hide()
        
        assert overlay.is_visible is False
        assert len(mock_page.overlay) == 0
        mock_page.update.assert_called()
```

### Mejores Prácticas para Tests

1. **Usar fixtures** para setup común
2. **Mock dependencias externas** (archivos, APIs, base de datos)
3. **Nombres descriptivos** para tests
4. **Separar casos de éxito y error**
5. **Tests independientes** (no dependen entre sí)
6. **Cobertura mínima 80%** para código crítico

### Tests de Integración

```python
# Ejemplo de test de integración para flujo completo
def test_complete_processing_flow():
    """Test del flujo completo de procesamiento"""
    # Setup
    processor = CoosaludProcessor("test_output")
    test_files = ["rips_detalle.xlsx", "glosas_coosalud.xlsx"]
    
    # Execute
    identified = processor.identify_files(test_files)
    assert identified is not None
    
    valid = processor.validate_files(identified)
    assert valid is True
    
    data = processor.extract_data(identified)
    assert data is not None
    
    result = processor.homologate(data)
    assert result is not None
```

---

## 📋 Integración de Componentes Loading en Vistas

### Patrón de Integración Estándar

#### 1. Importaciones Necesarias
```python
from app.ui.components.loading_overlay import LoadingOverlay, ToastNotification, LoadingButton
```

#### 2. Inicialización en Constructor
```python
class MyView:
    def __init__(self, page: ft.Page, ...):
        self.page = page
        
        # Componentes de loading
        self.loading_overlay = LoadingOverlay(page)
        self.toast = ToastNotification(page)
        
        self.container = self.build()
```

#### 3. Métodos de Control de Loading
```python
def show_loading(self, message="Cargando..."):
    """Muestra el overlay de carga"""
    if self.loading_overlay:
        self.loading_overlay.show(message)

def hide_loading(self):
    """Oculta el overlay de carga"""
    if self.loading_overlay:
        self.loading_overlay.hide()

def show_toast(self, message, toast_type="success"):
    """Muestra una notificación toast"""
    if self.toast:
        self.toast.show(message, toast_type)
```

#### 4. Uso en Event Handlers
```python
def _handle_action(self):
    """Maneja una acción con feedback visual"""
    try:
        self.show_loading("Procesando...")
        # Realizar operación
        result = self._perform_operation()
        self.show_toast("Operación completada exitosamente", "success")
    except Exception as ex:
        self.show_toast(f"Error: {str(ex)}", "error")
    finally:
        self.hide_loading()
```

### Ejemplos de Implementación Actual

#### DashboardView
- **LoadingOverlay**: Durante navegación entre cards
- **ToastNotification**: Para notificaciones de estado y verificación de actualizaciones
- **Feedback en Cards**: Loading al hacer click con mensaje personalizado

#### MessagesView
- **LoadingOverlay**: Durante búsqueda de mensajes
- **ToastNotification**: Para resultados de búsqueda y errores de conexión
- **ProgressIndicator**: Para descarga de archivos adjuntos

#### LoginView
- **LoadingButton**: Para botón de conexión con estado de carga
- **ToastNotification**: Para resultados de autenticación
- **LoadingOverlay**: Para validación de credenciales

#### ToolsView
- **LoadingOverlay**: Para navegación a herramientas específicas
- **ToastNotification**: Para funciones en desarrollo y feedback
- **Feedback Visual**: En todas las cards de herramientas con mensajes descriptivos

### Componentes Disponibles Integrados

1. **LoadingOverlay**: Overlay modal con spinner y mensaje personalizable
2. **ToastNotification**: Notificaciones no invasivas con tipos (success, error, warning, info)
3. **LoadingButton**: Botón con estado de carga integrado y spinner
4. **ProgressIndicator**: Barra de progreso para operaciones largas

### Patrones de Uso Recomendados

#### Para Operaciones de Red
```python
def _fetch_data(self):
    """Obtener datos de API con feedback"""
    try:
        self.show_loading("Conectando con servidor...")
        data = api_call()
        self.show_toast("Datos actualizados", "success")
        return data
    except ConnectionError:
        self.show_toast("Error de conexión", "error")
    except Exception as ex:
        self.show_toast(f"Error inesperado: {str(ex)}", "error")
    finally:
        self.hide_loading()
```

#### Para Procesamiento de Archivos
```python
def _process_file(self, file_path):
    """Procesar archivo con progreso"""
    try:
        self.show_loading("Procesando archivo...")
        # Si hay progreso conocido, usar ProgressIndicator
        result = process_file(file_path)
        self.show_toast("Archivo procesado exitosamente", "success")
    except FileNotFoundError:
        self.show_toast("Archivo no encontrado", "error")
    finally:
        self.hide_loading()
```

#### Para Navegación Entre Vistas
```python
def _navigate_to_view(self, view_name):
    """Navegar con feedback visual"""
    self.show_loading(f"Cargando {view_name}...")
    # La vista de destino se encarga de ocultar el loading
    self.navigation_controller.navigate_to(view_name)
```

---

## 🚀 Compilar Ejecutable

```bash
# Usar PyInstaller con el spec existente
pyinstaller glosaapp.spec

# El ejecutable estará en dist/glosaapp.exe
```

---

## 📞 Contacto / Soporte

Si tienes dudas sobre alguna parte del código, revisa:

1. Los comentarios en el código (docstrings)
2. Este documento
3. El README.md principal

---

**Recuerda:** Si no entiendes algo, **no lo modifiques**. Pregunta primero. 🙏
