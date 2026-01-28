# 🏥 Glosaap — Sistema de Gestión de Glosas

<div align="center">

![Glosaap Logo](assets/icons/app_logo.png)

**Sistema integral para la gestión, procesamiento y respuesta de glosas médicas**

[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Flet](https://img.shields.io/badge/Flet-0.27.6-green.svg)](https://flet.dev/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![GitHub Release](https://img.shields.io/github/v/release/Damdev80/Glosaap)](https://github.com/Damdev80/Glosaap/releases)

</div>

---

## 📋 Tabla de Contenidos

- [Descripción](#-descripción)
- [Características](#-características)
- [Requisitos](#-requisitos)
- [Instalación](#-instalación)
- [Uso](#-uso)
- [Estructura del Proyecto](#-estructura-del-proyecto)
- [Guía de Desarrollo](#-guía-de-desarrollo)
- [Sistema de Temas](#-sistema-de-temas)
- [Actualizaciones Automáticas](#-actualizaciones-automáticas)
- [Configuración](#-configuración)
- [Herramientas](#-herramientas)
- [Procesadores de EPS](#-procesadores-de-eps)
- [Compilación](#-compilación)
- [Solución de Problemas](#-solución-de-problemas)

---

## 📝 Descripción

**Glosaap** es una aplicación de escritorio desarrollada con Python y Flet para automatizar el proceso de gestión de glosas médicas. Permite:

- 📧 Conectarse a servidores IMAP para buscar correos de glosas
- 📥 Descargar automáticamente archivos Excel adjuntos
- 🔄 Homologar códigos de servicios médicos
- 📊 Procesar y consolidar información de glosas por EPS
- 📄 Generar archivos de objeciones listos para cargar en sistemas

---

## ✨ Características

### 🔐 Sistema de Autenticación
- Login con credenciales IMAP
- Auto-detección de servidor IMAP por dominio
- Opción "Recordar sesión" para auto-login
- Sesiones persistentes cifradas

### 🏠 Dashboard Principal
- **Evitar Glosa**: Prevención y validación antes de facturar
- **Manejar Glosa**: Gestión y seguimiento de glosas activas (búsqueda de correos)
- **Responder Glosa**: Respuesta a objeciones y documentación

### 📧 Métodos de Obtención de Glosas

#### Glosa por Correo
- Búsqueda de correos por palabra clave "glosa"
- Filtrado por EPS (MUTUALSER, COOSALUD, etc.)
- Filtrado por rango de fechas
- Descarga automática de adjuntos Excel

#### Glosa por Web
- **Familiar de Colombia**: Automatización con Playwright
- **Fomag (Horus)**: Descarga desde portal web
- Guardado seguro de credenciales

### 🔄 Homologación de Códigos
- Homologación automática usando archivos maestros
- Validación de códigos contra COD_SERV_FACT
- Soporte multi-EPS
- CRUD completo para gestionar códigos
- Carga masiva desde Excel

### 🎨 Interfaz Moderna
- **Tema Claro/Oscuro** con persistencia (toggle en el dashboard)
- Diseño minimalista con Flet
- Cards con efectos hover
- Indicadores de progreso
- Notificaciones toast

### 🔄 Actualizaciones Automáticas
- Verificación automática desde GitHub Releases
- Descarga e instalación en segundo plano
- Updater independiente para evitar conflictos

---

## 📋 Requisitos

### Software
- **Python** 3.10 o superior
- **Windows** 10/11 (para rutas de red UNC)
- Acceso a red corporativa (para rutas `\\MINERVA\...`)

### Dependencias Python
```
flet>=0.27.6
pandas>=2.0.0
openpyxl>=3.0.0
playwright>=1.40.0
python-dotenv>=1.0.0
requests>=2.31.0
```

---

## 🚀 Instalación

### 1. Clonar el repositorio
```powershell
git clone https://github.com/Damdev80/Glosaap.git
cd Glosaap
```

### 2. Crear entorno virtual
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### 3. Instalar dependencias
```powershell
pip install -r requirements.txt
```

### 4. Instalar navegadores de Playwright (para descarga web)
```powershell
playwright install chromium
```

### 5. Verificar instalación
```powershell
python -c "import flet; import pandas; print('✅ Dependencias instaladas correctamente')"
```

---

## 💻 Uso

### Ejecutar la aplicación
```powershell
python main.py
```

### Flujo de trabajo típico

#### 1️⃣ **Iniciar sesión**
```
┌─────────────────────────────────────┐
│           🔐 Glosaap                │
│                                     │
│  Correo: usuario@empresa.com        │
│  Contraseña: ********               │
│  Servidor IMAP: (auto-detecta)      │
│                                     │
│  ☑️ Recordar sesión                 │
│                                     │
│       [ Iniciar Sesión ]            │
└─────────────────────────────────────┘
```

#### 2️⃣ **Seleccionar método**
- **📧 Glosa por Correo**: Busca en tu bandeja de entrada
- **🌐 Glosa por Web**: Descarga desde portales EPS

#### 3️⃣ **Dashboard principal**
- Seleccionar acción (Evitar/Manejar/Responder)
- O usar Herramientas para funciones adicionales
- Toggle de tema claro/oscuro disponible

#### 4️⃣ **Configurar búsqueda**
- Seleccionar rango de fechas
- Elegir EPS a procesar

#### 5️⃣ **Procesar y revisar resultados**
- Los archivos se generan en la carpeta de red
- Se abre automáticamente la carpeta de salida

---

## 📁 Estructura del Proyecto

```
Glosaap/
├── 📁 app/                           # Código fuente principal
│   ├── 📁 api/                       # APIs externas (futuro)
│   ├── 📁 config/
│   │   ├── eps_config.py             # Configuración de EPS
│   │   └── settings.py               # Settings globales (versión, rutas)
│   ├── 📁 core/
│   │   ├── homologacion_service.py   # CRUD de homologación
│   │   ├── imap_client.py            # Cliente IMAP
│   │   ├── mix_excel_service.py      # Servicio Mix Excel
│   │   ├── mutualser_processor.py    # Procesador MUTUALSER
│   │   └── session_manager.py        # Gestión de sesiones
│   ├── 📁 service/
│   │   ├── attachment_service.py     # Servicio de adjuntos
│   │   ├── auth_service.py           # Autenticación
│   │   ├── email_service.py          # Servicio de correo
│   │   ├── 📁 processors/            # Procesadores por EPS
│   │   │   ├── base_processor.py     # Clase base
│   │   │   └── coosalud_processor.py # Procesador COOSALUD
│   │   └── 📁 web_scraper/           # Scrapers web
│   │       ├── base_scraper.py       # Scraper base
│   │       ├── familiar_scraper.py   # Scraper Familiar
│   │       └── fomag_scraper.py      # Scraper Fomag
│   └── 📁 ui/
│       ├── app.py                    # Aplicación principal
│       ├── styles.py                 # ThemeManager y estilos
│       ├── navigation.py             # Control de navegación
│       ├── 📁 components/            # Componentes reutilizables
│       │   ├── alert_dialog.py       # Diálogos de alerta
│       │   ├── date_range_picker.py  # Selector de fechas
│       │   ├── eps_card.py           # Tarjetas de EPS
│       │   └── message_row.py        # Filas de mensajes
│       ├── 📁 screens/
│       │   └── eps_screen.py         # Pantalla selección EPS
│       └── 📁 views/
│           ├── dashboard_view.py     # Dashboard principal
│           ├── login_view.py         # Vista de login
│           ├── method_selection_view.py # Selección método (correo/web)
│           ├── tools_view.py         # Menú de herramientas
│           ├── homologacion_view.py  # Gestión homologación
│           ├── homologador_manual_view.py  # Homologador manual
│           ├── mix_excel_view.py     # Herramienta Mix Excel
│           ├── web_download_view.py  # Descarga web
│           └── messages_view.py      # Vista de mensajes
├── 📁 assets/
│   ├── 📁 icons/
│   │   ├── app_logo.png              # Logo aplicación
│   │   └── app_logo.ico              # Icono para .exe
│   └── 📁 img/
│       └── 📁 eps/                   # Logos de EPS
├── 📁 temp/                          # Archivos temporales
│   ├── 📁 config/                    # Credenciales guardadas
│   └── 📁 perfil_chrome/             # Perfil de Playwright
├── 📁 tests/                         # Tests unitarios
├── build.py                          # Script de compilación
├── glosaap.spec                      # Config PyInstaller
├── main.py                           # Punto de entrada
├── release.py                        # Script para crear releases
├── updater.py                        # Actualizador independiente
└── requirements.txt                  # Dependencias
```

---

## 👨‍💻 Guía de Desarrollo

Para desarrolladores que quieran contribuir al proyecto, consulta la **[Guía de Desarrollo](docs/DEVELOPER_GUIDE.md)** que incluye:

- 🏗️ Arquitectura del proyecto
- 🎨 Sistema de temas (claro/oscuro)
- 📄 Cómo crear una nueva vista
- 🧩 Cómo crear un componente
- 🏥 Cómo crear un procesador de EPS
- ✅ Buenas prácticas
- 🧪 Testing
- 🐛 Debugging

---

## 🌓 Sistema de Temas

La aplicación soporta **tema claro y oscuro** que se aplica a toda la interfaz.

### Cómo cambiar el tema
- En el **dashboard**, usa el botón de toggle (sol/luna) en la esquina superior
- El tema se guarda automáticamente y persiste entre sesiones

### Para desarrolladores
Los componentes usan `ft.Colors.*` que se adaptan automáticamente al tema:

```python
# ✅ CORRECTO - Se adapta al tema
ft.Container(bgcolor=ft.Colors.SURFACE)
ft.Text(color=ft.Colors.ON_SURFACE)

# ❌ INCORRECTO - No se adapta
ft.Container(bgcolor="#ffffff")
ft.Text(color="#000000")
```

Ver [DEVELOPER_GUIDE.md](DEVELOPER_GUIDE.md#-sistema-de-temas) para más detalles.

---

## 🔄 Actualizaciones Automáticas

### Cómo funciona
1. Al iniciar, la app verifica si hay actualizaciones en GitHub Releases
2. Si hay una versión nueva, muestra un diálogo
3. Al aceptar, descarga el ZIP de la nueva versión
4. Ejecuta `updater.exe` que instala la actualización

### Verificar manualmente
Click en el número de versión en la esquina inferior izquierda del dashboard.

---

## ⚙️ Configuración

### `app/config/settings.py`
```python
# Versión de la aplicación
APP_VERSION = "1.3.8"

# Rutas de red
NETWORK_PATHS = {
    "homologacion_mutualser": r"\\MINERVA\Cartera\GLOSAAP\HOMOLOGADOR\mutualser_homologacion.xlsx",
    "output_mutualser": r"\\MINERVA\Cartera\GLOSAAP\MUTUALSER\OUTPUTS",
}
```

### `app/config/eps_config.py`
```python
EPS_CONFIG = [
    {
        "name": "MUTUALSER",
        "filter": "mutualser",
        "filter_type": "keyword",
        "description": "Mutual SER EPS",
        "image_path": "assets/img/eps/mutualser.png"
    },
    # ... más EPS
]
```
---

## 🛠️ Herramientas

### 📋 Gestión de Homologación
**Ubicación:** Herramientas → Gestión Homologación

- Agregar/Editar/Eliminar códigos de homologación
- Búsqueda por código o descripción
- Carga masiva desde archivo Excel
- Selector de EPS (MUTUALSER, COOSALUD)

### 🔄 Homologador Manual
**Ubicación:** Herramientas → Homologador Manual

1. Seleccionar EPS
2. Cargar archivo Excel
3. Seleccionar columna a homologar
4. Procesar → genera archivo homologado

**Ruta de salida:** `\\MINERVA\Cartera\GLOSAAP\RESULTADO DE HOMOLAGADOR MANUAL`

### 📊 Mix Excel
**Ubicación:** Herramientas → Mix Excel

Transfiere datos entre dos archivos Excel:
1. Seleccionar archivo origen y destino
2. Configurar columnas de referencia y destino
3. Establecer tolerancia de coincidencia
4. Ejecutar transferencia

---

## 🏥 Procesadores de EPS

### MUTUALSER ✅
**Estado:** Completamente implementado

| Columna Entrada | Columna Salida |
|-----------------|----------------|
| Número factura | CRNCXC |
| Código servicio | SLNSERPRO (homologado) |
| Valor glosado | CROVALOBJ |
| Concepto glosa | CRDOBSERV |
| Código glosa | CRNCONOBJ |

### COOSALUD ⏳
**Estado:** En desarrollo

---

## 🌐 Rutas de Red

| Propósito | Ruta |
|-----------|------|
| Homologación MUTUALSER | `\\MINERVA\Cartera\GLOSAAP\HOMOLOGADOR\mutualser_homologacion.xlsx` |
| Homologación COOSALUD | `\\MINERVA\Cartera\GLOSAAP\HOMOLOGADOR\coosalud_homologacion.xlsx` |
| Salida procesamiento | `\\MINERVA\Cartera\GLOSAAP\MUTUALSER\OUTPUTS\` |
| Homologador manual | `\\MINERVA\Cartera\GLOSAAP\RESULTADO DE HOMOLAGADOR MANUAL\` |

> ⚠️ **Nota:** Asegúrate de tener acceso a estas rutas de red antes de usar la aplicación.

---

## 📦 Compilación

### Generar ejecutable

```powershell
# Activar entorno virtual
.\.venv\Scripts\Activate.ps1

# Ejecutar script de build
python build.py
```

Genera:
- `release/Glosaap_vX.X.X_YYYYMMDD.zip`
- Contiene: `Glosaap.exe`, `updater.exe`, `README.txt`

### Crear release en GitHub

```powershell
# Configurar token en .env
# GITHUB_TOKEN=ghp_xxx

# Ejecutar release
python release.py
```

---

## ❓ Solución de Problemas

### Error: "No se puede conectar al servidor IMAP"
- Verificar credenciales
- Para Gmail: usar contraseña de aplicación
- Verificar servidor IMAP correcto

### Error: "Ruta de red no accesible"
- Verificar conexión VPN/red corporativa
- Verificar permisos en `\\MINERVA\`

### Pantalla negra al cambiar tema
- Actualizar Flet a versión >= 0.27.6
- Verificar que todas las vistas tengan `bgcolor=ft.Colors.SURFACE`

### La aplicación se congela
- Reducir rango de fechas de búsqueda
- Verificar conexión a internet

---

## 👥 Contribuir

1. Fork el repositorio
2. Crear rama feature (`git checkout -b feature/NuevaFuncionalidad`)
3. Seguir las [Buenas Prácticas](/docs/DEVELOPER_GUIDE.md#-buenas-prácticas)
4. Commit cambios (`git commit -m 'feat: agregar nueva funcionalidad'`)
5. Push a la rama (`git push origin feature/NuevaFuncionalidad`)
6. Crear Pull Request

### Convención de commits

- `feat:` Nueva funcionalidad
- `fix:` Corrección de bug
- `docs:` Documentación
- `style:` Formato (no afecta código)
- `refactor:` Refactorización
- `test:` Tests

---

## 📄 Licencia

Este proyecto es de uso interno corporativo.

---

<div align="center">

**Desarrollado con ❤️ para la gestión eficiente de glosas médicas**

[⬆️ Volver arriba](#-glosaap--sistema-de-gestión-de-glosas)

</div>
