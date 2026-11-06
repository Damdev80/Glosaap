# 📚 Guía de Desarrollo - Glosaap

Esta guía está diseñada para que desarrolladores nuevos puedan entender rápidamente la arquitectura del proyecto y comenzar a contribuir.

---

## 📋 Tabla de Contenidos

1. [Inicio Rápido](#-inicio-rápido)
2. [Arquitectura del Proyecto](#-arquitectura-del-proyecto)
3. [Sistema de UI con Flet](#-sistema-de-ui-con-flet)
4. [Sistema de Temas](#-sistema-de-temas)
5. [Crear una Nueva Vista](#-crear-una-nueva-vista)
6. [Crear un Nuevo Componente](#-crear-un-nuevo-componente)
7. [Crear un Procesador de EPS](#-crear-un-procesador-de-eps)
8. [Sistema de Navegación](#-sistema-de-navegación)
9. [Buenas Prácticas](#-buenas-prácticas)
10. [Testing](#-testing)
11. [Debugging](#-debugging)
12. [Rutina de release](#-rutina-de-release-obligatoria)

---

## 🚀 Inicio Rápido

### Requisitos
- Python 3.11+ (CI verificado en 3.11 y 3.12; 3.15 local no soportado)
- Git
- Acceso a red corporativa (para rutas `\\MINERVA\...`)

### Setup del Entorno

```powershell
# 1. Clonar el repositorio
git clone https://github.com/Damdev80/Glosaap.git
cd Glosaap

# 2. Crear entorno virtual
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# 3. Instalar dependencias
pip install -r requirements.txt

# 4. Instalar navegadores de Playwright (para descarga web)
playwright install chromium

# 5. Ejecutar la aplicación
python main.py
```

---

## 🏗️ Arquitectura del Proyecto

### Diagrama de Capas

```
┌─────────────────────────────────────────────────────────────┐
│                      CAPA DE UI                              │
│                   (app/ui/)                                  │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐        │
│  │   views/     │ │  screens/    │ │ components/  │        │
│  │ (Vistas)     │ │ (Pantallas)  │ │ (Widgets)    │        │
│  └──────────────┘ └──────────────┘ └──────────────┘        │
│                                                              │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐        │
│  │   app.py     │ │  styles.py   │ │ navigation.py│        │
│  │  (Main App)  │ │ (Temas)      │ │ (Navegación) │        │
│  └──────────────┘ └──────────────┘ └──────────────┘        │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    CAPA DE SERVICIOS                         │
│                      (app/service/)                          │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐        │
│  │ email_service│ │ attachment_  │ │ auth_service │        │
│  │              │ │ service      │ │              │        │
│  └──────────────┘ └──────────────┘ └──────────────┘        │
│                                                              │
│  ┌──────────────┐ ┌──────────────┐                         │
│  │ processors/  │ │ web_scraper/ │                         │
│  │ (Por EPS)    │ │ (Scrapers)   │                         │
│  └──────────────┘ └──────────────┘                         │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                      CAPA CORE                               │
│                       (app/core/)                            │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐        │
│  │ imap_client  │ │ homologacion │ │ session_     │        │
│  │              │ │ _service     │ │ manager      │        │
│  └──────────────┘ └──────────────┘ └──────────────┘        │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                  RECURSOS EXTERNOS                           │
│  • Servidores IMAP           • Rutas de red (\\MINERVA\)   │
│  • GitHub API (updates)       • Portales web EPS           │
└─────────────────────────────────────────────────────────────┘
```

### Estructura de Carpetas

```
app/
├── config/           # Configuración de la aplicación
│   ├── settings.py   # → VERSION, rutas, constantes
│   └── eps_config.py # → Definición de EPS soportadas
│
├── core/             # Lógica de negocio pura
│   ├── imap_client.py        # → Cliente IMAP
│   ├── homologacion_service.py # → CRUD homologación
│   └── session_manager.py    # → Gestión de sesiones
│
├── service/          # Servicios de aplicación
│   ├── email_service.py      # → Orquestación de correos
│   ├── attachment_service.py # → Manejo de adjuntos
│   ├── processors/           # → Procesadores por EPS
│   └── web_scraper/          # → Scrapers web
│
└── ui/               # Interfaz de usuario
    ├── app.py        # → Punto de entrada de UI
    ├── styles.py     # → ThemeManager y estilos
    ├── navigation.py # → Control de navegación
    ├── views/        # → Vistas principales
    ├── screens/      # → Pantallas completas
    └── components/   # → Widgets reutilizables
```

---

## 🎨 Sistema de UI con Flet

### ¿Qué es Flet?
[Flet](https://flet.dev) es un framework de Python que permite crear aplicaciones de escritorio, web y móvil con una API similar a Flutter.

### Conceptos Básicos

```python
import flet as ft

def main(page: ft.Page):
    # page es la ventana principal de la aplicación
    page.title = "Mi App"
    
    # Los controles son widgets
    texto = ft.Text("Hola mundo")
    boton = ft.ElevatedButton("Click me", on_click=lambda e: print("clicked"))
    
    # Se agregan a la página
    page.add(texto, boton)

ft.app(target=main)
```

### Controles Más Usados en Glosaap

```python
# Textos
ft.Text("Mi texto", size=16, weight=ft.FontWeight.BOLD)

# Botones
ft.ElevatedButton("Primario", color=ft.Colors.WHITE, bgcolor=ft.Colors.PRIMARY)
ft.OutlinedButton("Secundario")
ft.IconButton(icon=ft.Icons.SETTINGS)

# Contenedores
ft.Container(
    content=ft.Text("En container"),
    padding=20,
    bgcolor=ft.Colors.SURFACE,
    border_radius=10
)

# Layouts
ft.Column([...], spacing=10)  # Vertical
ft.Row([...], spacing=10)     # Horizontal
ft.Stack([...])               # Superpuestos (para navegación)

# Inputs
ft.TextField(label="Email")
ft.Dropdown(options=[...])
ft.Checkbox(label="Acepto")
```

---

## 🌓 Sistema de Temas

### ThemeManager

El sistema de temas está centralizado en `app/ui/styles.py`:

```python
from app.ui.styles import ThemeManager

# Verificar tema actual
if ThemeManager.is_dark():
    print("Modo oscuro")
else:
    print("Modo claro")

# Cambiar tema
ThemeManager.toggle_theme()
```

### Colores que se Adaptan al Tema

**SIEMPRE** usar `ft.Colors.*` en lugar de colores hardcodeados:

```python
# ✅ CORRECTO - Se adapta al tema automáticamente
ft.Container(
    bgcolor=ft.Colors.SURFACE,           # Fondo principal
    content=ft.Text(
        "Hola",
        color=ft.Colors.ON_SURFACE       # Texto que contrasta
    )
)

# ❌ INCORRECTO - No se adapta al tema
ft.Container(
    bgcolor="#ffffff",                    # Siempre blanco
    content=ft.Text(
        "Hola",
        color="#000000"                   # Siempre negro
    )
)
```

### Tabla de Colores Semánticos

| Color | Uso | Tema Oscuro | Tema Claro |
|-------|-----|-------------|------------|
| `ft.Colors.SURFACE` | Fondo de contenedores | Gris oscuro | Blanco |
| `ft.Colors.ON_SURFACE` | Texto principal | Blanco | Negro |
| `ft.Colors.SURFACE_VARIANT` | Fondo secundario | Gris más oscuro | Gris claro |
| `ft.Colors.ON_SURFACE_VARIANT` | Texto secundario | Gris claro | Gris oscuro |
| `ft.Colors.PRIMARY` | Color de acento | Azul brillante | Azul |
| `ft.Colors.ON_PRIMARY` | Texto sobre primary | Blanco | Blanco |
| `ft.Colors.OUTLINE` | Bordes | Gris | Gris |
| `ft.Colors.ERROR` | Errores | Rojo | Rojo |

---

## 📄 Crear una Nueva Vista

### Paso 1: Crear el archivo

```python
# app/ui/views/mi_vista_view.py
"""
Vista para Mi Nueva Funcionalidad.

Esta vista muestra información sobre X y permite al usuario hacer Y.
"""
import flet as ft
from typing import Optional, Callable


class MiVistaView:
    """
    Vista de Mi Funcionalidad.
    
    Attributes:
        page: Referencia a la página principal de Flet
        on_back: Callback opcional para volver atrás
        container: Contenedor principal de la vista
    """
    
    def __init__(
        self, 
        page: ft.Page, 
        on_back: Optional[Callable[[], None]] = None
    ):
        """
        Inicializa la vista.
        
        Args:
            page: Página principal de Flet
            on_back: Callback para navegación hacia atrás
        """
        self.page = page
        self.on_back = on_back
        self.container = self._build()
    
    def _build(self) -> ft.Container:
        """Construye la interfaz de la vista."""
        
        # Header con navegación
        header = ft.Container(
            content=ft.Row([
                ft.IconButton(
                    icon=ft.Icons.ARROW_BACK,
                    icon_color=ft.Colors.ON_SURFACE_VARIANT,
                    tooltip="Volver",
                    on_click=lambda e: self.on_back() if self.on_back else None
                ),
                ft.Text(
                    "Mi Nueva Vista",
                    size=18,
                    weight=ft.FontWeight.W_500,
                    color=ft.Colors.ON_SURFACE
                ),
            ], alignment=ft.MainAxisAlignment.START, spacing=8),
            padding=ft.padding.symmetric(horizontal=24, vertical=16),
        )
        
        # Contenido principal
        content = ft.Container(
            content=ft.Column([
                ft.Text(
                    "Contenido aquí",
                    color=ft.Colors.ON_SURFACE
                ),
                ft.ElevatedButton(
                    "Acción Principal",
                    bgcolor=ft.Colors.PRIMARY,
                    color=ft.Colors.ON_PRIMARY,
                    on_click=self._handle_action
                )
            ], spacing=16),
            padding=ft.padding.all(24),
            expand=True
        )
        
        # Layout principal
        main_column = ft.Column(
            [header, content],
            spacing=0,
            expand=True
        )
        
        return ft.Container(
            content=main_column,
            bgcolor=ft.Colors.SURFACE,  # ⚠️ OBLIGATORIO - Fondo sólido
            expand=True,
            visible=False  # Inicialmente oculta
        )
    
    def _handle_action(self, e):
        """Maneja el click en el botón de acción."""
        # Implementar lógica aquí
        print("Acción ejecutada")
    
    def show(self):
        """Muestra la vista."""
        self.container.visible = True
        self.page.update()
    
    def hide(self):
        """Oculta la vista."""
        self.container.visible = False
        self.page.update()
```

### Paso 2: Registrar en app.py

```python
# app/ui/app.py

# 1. Importar la nueva vista
from app.ui.views.mi_vista_view import MiVistaView

def main(page: ft.Page):
    # ... código existente ...
    
    # 2. Instanciar la vista
    mi_vista_view = MiVistaView(
        page=page,
        on_back=go_to_dashboard  # Callback para volver
    )
    
    # 3. Crear función de navegación
    def go_to_mi_vista():
        current_view["name"] = "mi_vista"
        # Ocultar todas las vistas
        dashboard_view.hide()
        tools_view.hide()
        homologacion_view.hide()
        # ... ocultar otras vistas ...
        
        # Mostrar la nueva vista
        mi_vista_view.show()
        page.update()
    
    # 4. Agregar al Stack principal
    page.add(
        ft.Stack([
            # ... otras vistas ...
            mi_vista_view.container,  # ← Agregar aquí
        ], expand=True)
    )
```

---

## 🧩 Crear un Nuevo Componente

Los componentes son widgets reutilizables que se usan en múltiples vistas.

### Ejemplo: Tarjeta de Información

```python
# app/ui/components/info_card.py
"""
Componente: Tarjeta de Información.

Muestra información resumida con título, descripción e icono.
"""
import flet as ft
from typing import Optional, Callable


class InfoCard(ft.UserControl):
    """
    Tarjeta de información reutilizable.
    
    Ejemplo de uso:
        InfoCard(
            title="Usuarios",
            value="125",
            icon=ft.Icons.PEOPLE,
            on_click=lambda: print("clicked")
        )
    """
    
    def __init__(
        self,
        title: str,
        value: str,
        icon: str = ft.Icons.INFO,
        on_click: Optional[Callable[[], None]] = None
    ):
        super().__init__()
        self.title = title
        self.value = value
        self.icon = icon
        self._on_click = on_click
    
    def build(self):
        return ft.Container(
            content=ft.Column([
                ft.Row([
                    ft.Icon(
                        self.icon,
                        color=ft.Colors.PRIMARY,
                        size=24
                    ),
                    ft.Text(
                        self.title,
                        size=14,
                        color=ft.Colors.ON_SURFACE_VARIANT
                    )
                ], spacing=8),
                ft.Text(
                    self.value,
                    size=28,
                    weight=ft.FontWeight.BOLD,
                    color=ft.Colors.ON_SURFACE
                )
            ], spacing=8),
            padding=20,
            bgcolor=ft.Colors.SURFACE_VARIANT,
            border_radius=12,
            on_click=lambda e: self._on_click() if self._on_click else None,
            ink=True  # Efecto de ripple al hacer click
        )


# Uso en una vista:
# from app.ui.components.info_card import InfoCard
# 
# card = InfoCard(
#     title="Glosas Pendientes",
#     value="47",
#     icon=ft.Icons.PENDING_ACTIONS,
#     on_click=lambda: go_to_pending()
# )
```

---

## \U0001f3e5 Crear un Procesador de EPS

Los procesadores heredan de `BaseProcessor` (`app/service/processors/`)
y respetan su Template Method. El procedimiento completo paso a paso
está en `docs/GUIA_NUEVA_EPS.md` (con Previsora como ejemplo real);
aquí va el contrato mínimo que el código exige:

```python
# app/service/processors/nueva_eps_processor.py
import pandas as pd
from typing import Any
from .base_processor import BaseProcessor


class NuevaEpsProcessor(BaseProcessor):
    """Un xlsx por correo. Ver SanitasProcessor como referencia."""

    def identify_files(self, file_paths: list[str]) -> list[str]:
        # Retorna TODOS los válidos (nunca solo el primero).
        return [f for f in (file_paths or []) if f.lower().endswith(".xlsx")]

    def validate_files(self, identified_files) -> bool:
        # Verifica que existan en disco; errores a self.errors.
        ...

    def extract_data(self, identified_files) -> dict[str, pd.DataFrame]:
        # Lee y concatena TODAS las hojas si aplica; una entrada por archivo.
        ...

    def homologate(self, data: dict[str, pd.DataFrame]) -> pd.DataFrame:
        # OBLIGATORIO: retorna DataFrame (no dict). Si el flujo necesita
        # 2 salidas, el dict {"detalle", "glosa", ...} se compone en
        # process_glosas, no aquí. Usa helpers de la base:
        # _normalize_code, _formatear_crncxc, _formatear_fecha_dmy,
        # _obtener_valor_numerico, y _drop_internal_columns al exportar.
        ...
```

### Registrar en Configuración

```python
# app/config/settings.py  (fuente única de rutas)
NETWORK_PATHS["nuevaeps_output"] = os.path.join(
    NETWORK_BASE, "REPOSITORIO DE RESULTADOS", "NUEVAEPS")
HOMOLOGADOR_FILES["nuevaeps"] = os.path.join(
    NETWORK_PATHS["homologador"], "nuevaeps_homologacion.xlsx")
```

```python
# app/config/eps_config.py
class NuevaEps(EpsInfo):
    def __init__(self):
        super().__init__(
            name="Nueva EPS",
            filter_value="nuevaeps",
            filter_type="subject_exact_pattern",  # match por substring
            subject_pattern="Texto del asunto",
            processor_class="NuevaEpsProcessor",
            enabled=True,
            sender_filter="remitente@ejemplo.com",
            homologador_file="nuevaeps",  # clave de HOMOLOGADOR_FILES
        )
```

Y cablear `EmailService.procesar_nuevaeps()` + botón y rama en
`app/ui/app.py` (patrón idéntico al de Sanitas/Previsora), opción en
`homologador_manual_view.py` y entradas en `HomologacionService`.
El checklist completo —incluidos los tests mínimos exigidos— está en
`docs/GUIA_NUEVA_EPS.md`.

---

## 🧭 Sistema de Navegación

### Cómo Funciona

La navegación usa un `ft.Stack` donde todas las vistas están superpuestas pero solo una es visible:

```python
# Pseudocódigo de app.py
page.add(
    ft.Stack([
        login_view.container,      # visible=True  si no autenticado
        dashboard_view.container,  # visible=True  si autenticado
        tools_view.container,      # visible=False
        homologacion_view.container,  # visible=False
        # ... más vistas
    ], expand=True)
)
```

### Patrón de Navegación

```python
# Variable para trackear vista actual
current_view = {"name": "login"}

def go_to_dashboard():
    """Navega al dashboard."""
    current_view["name"] = "dashboard"
    
    # Ocultar todas
    login_view.hide()
    tools_view.hide()
    homologacion_view.hide()
    
    # Mostrar destino
    dashboard_view.show()
    page.update()

def go_to_tools():
    """Navega a herramientas."""
    current_view["name"] = "tools"
    
    # Ocultar todas
    login_view.hide()
    dashboard_view.hide()
    homologacion_view.hide()
    
    # Mostrar destino
    tools_view.show()
    page.update()
```

### Navegación con Callback

Las vistas reciben un callback `on_back` para volver:

```python
# En la vista:
class MiVista:
    def __init__(self, page, on_back=None):
        self.on_back = on_back
        
    def _build(self):
        return ft.IconButton(
            icon=ft.Icons.ARROW_BACK,
            on_click=lambda e: self.on_back() if self.on_back else None
        )

# En app.py:
mi_vista = MiVista(
    page=page,
    on_back=go_to_dashboard  # ← Callback inyectado
)
```

---

## ✅ Buenas Prácticas

### 1. Colores - NUNCA Hardcodear

```python
# ✅ CORRECTO
ft.Text("Hola", color=ft.Colors.ON_SURFACE)
ft.Container(bgcolor=ft.Colors.SURFACE)

# ❌ INCORRECTO  
ft.Text("Hola", color="#000000")
ft.Container(bgcolor="#ffffff")
```

### 2. Contenedores - SIEMPRE con bgcolor

```python
# ✅ CORRECTO - No se ve contenido detrás
ft.Container(
    content=...,
    bgcolor=ft.Colors.SURFACE,  # ← OBLIGATORIO
    expand=True
)

# ❌ INCORRECTO - Transparente, se ve contenido detrás
ft.Container(
    content=...,
    expand=True
)
```

### 3. Callbacks - Verificar None

```python
# ✅ CORRECTO
on_click=lambda e: self.on_back() if self.on_back else None

# ❌ INCORRECTO - Puede crashear
on_click=lambda e: self.on_back()
```

### 4. Type Hints

```python
# ✅ CORRECTO
def process_file(self, filepath: str) -> Optional[pd.DataFrame]:
    """Procesa archivo y retorna DataFrame o None."""
    pass

# ❌ INCORRECTO
def process_file(self, filepath):
    pass
```

### 5. Docstrings

```python
# ✅ CORRECTO
def calculate_total(items: list[dict]) -> float:
    """
    Calcula el total de una lista de items.
    
    Args:
        items: Lista de diccionarios con key 'valor'
        
    Returns:
        Suma total de valores
        
    Raises:
        ValueError: Si algún item no tiene key 'valor'
    """
    return sum(item['valor'] for item in items)
```

### 6. Manejo de Errores

```python
# ✅ CORRECTO
try:
    df = pd.read_excel(filepath)
except FileNotFoundError:
    self.logger.error(f"Archivo no encontrado: {filepath}")
    return None
except Exception as e:
    self.logger.error(f"Error inesperado: {e}")
    return None

# ❌ INCORRECTO
df = pd.read_excel(filepath)  # Puede crashear
```

---

## 🧪 Testing

### Ejecutar Tests

```powershell
# Todos los tests
pytest tests/

# Test específico
pytest tests/test_processors.py

# Con cobertura
pytest --cov=app tests/
```

### Estructura de Test

```python
# tests/test_mi_modulo.py
import pytest
from app.service.processors.nueva_eps_processor import NuevaEpsProcessor


class TestNuevaEpsProcessor:
    """Tests para NuevaEpsProcessor (sin red, sin IMAP, con tmp_path)."""

    @pytest.fixture
    def processor(self):
        """Fixture que crea un procesador para testing."""
        return NuevaEpsProcessor(homologador_path="")
```

---

## 🐛 Debugging

### Logs

```python
import logging

# Configurar logger
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Usar en código
logger.debug("Variable x = %s", x)
logger.info("Proceso completado")
logger.warning("Archivo no encontrado, usando default")
logger.error("Error al procesar: %s", e)
```

### Inspeccionar Estado de Flet

```python
# En cualquier evento handler
def on_click(e):
    print(f"Page theme mode: {self.page.theme_mode}")
    print(f"Vista visible: {self.container.visible}")
    print(f"Current view: {current_view}")
```

### Hot Reload

Flet soporta hot reload durante desarrollo:

```powershell
# Con hot reload
flet run main.py --hot

# Sin hot reload (producción)
python main.py
```

---

## 📚 Recursos Adicionales

- [Documentación de Flet](https://flet.dev/docs/)
- [Flet Controls Gallery](https://flet.dev/docs/controls)
- [Python Type Hints Cheatsheet](https://mypy.readthedocs.io/en/stable/cheat_sheet_py3.html)
- [Guía del Administrador](./GUIA_ADMIN.md) (red, homologadores, updates)
- [Guía: agregar una nueva EPS](./GUIA_NUEVA_EPS.md) (procedimiento con ejemplo real)

---

## 🚀 Rutina de release (obligatoria)

1. `python bump.py X.Y.Z` (sincroniza `settings.py`, `pyproject.toml`,
   `README.md`, `MANUAL_USUARIO.md`, `AUTO_UPDATE.md` + entrada en
   `CHANGELOG.md`).
2. Completar los bullets del CHANGELOG (prohibido dejar `(completar)`).
3. `pytest` en verde + `ruff check` limpio. El test
   `tests/test_release_consistency.py` verifica en CI que la versión
   coincida en todos los archivos y que el CHANGELOG tenga la entrada.
4. Commit + tag `vX.Y.Z` + push (el workflow auto-release compila y
   publica ZIP + `.sha256`; nunca taguear `v0.0.0-test`: crea un
   release real).

---

<div align="center">

**¿Tienes dudas? Contacta al equipo de desarrollo.**

</div>
