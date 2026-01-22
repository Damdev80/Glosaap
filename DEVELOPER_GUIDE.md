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

## 🏭 Procesadores de EPS

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

```bash
# Ejecutar tests
python -m pytest tests/ -v

# Test específico
python -m pytest tests/test_processors.py -v
```

---

## 🚀 Compilar Ejecutable

```bash
# Usar PyInstaller con el spec existente
pyinstaller glosaap.spec

# El ejecutable estará en dist/glosaap.exe
```

---

## 📞 Contacto / Soporte

Si tienes dudas sobre alguna parte del código, revisa:

1. Los comentarios en el código (docstrings)
2. Este documento
3. El README.md principal

---

**Recuerda:** Si no entiendes algo, **no lo modifiques**. Pregunta primero. 🙏
