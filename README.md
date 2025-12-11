# 🏥 Glosaap — Sistema de Gestión de Glosas

<div align="center">

![Glosaap Logo](assets/icons/app_logo.png)

**Sistema integral para la gestión, procesamiento y respuesta de glosas médicas**

[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Flet](https://img.shields.io/badge/Flet-0.9.0+-green.svg)](https://flet.dev/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

</div>

---

## 📋 Tabla de Contenidos

- [Descripción](#-descripción)
- [Características](#-características)
- [Requisitos](#-requisitos)
- [Instalación](#-instalación)
- [Uso](#-uso)
- [Estructura del Proyecto](#-estructura-del-proyecto)
- [Módulos Principales](#-módulos-principales)
- [Configuración](#-configuración)
- [Herramientas](#-herramientas)
- [Procesadores de EPS](#-procesadores-de-eps)
- [Rutas de Red](#-rutas-de-red)
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
- **Manejar Glosa**: Gestión y seguimiento de glosas activas
- **Responder Glosa**: Respuesta a objeciones y documentación

### 📧 Gestión de Correos
- Búsqueda de correos por palabra clave "glosa"
- Filtrado por EPS (MUTUALSER, COOSALUD, etc.)
- Filtrado por rango de fechas
- Descarga automática de adjuntos Excel
- Límite configurable (hasta 500 correos)

### 🔄 Homologación de Códigos
- Homologación automática usando archivos maestros
- Validación de códigos contra COD_SERV_FACT
- Soporte multi-EPS
- Reglas de homologación:
  1. Buscar código en `Código Servicio de la ERP`
  2. Obtener `Código producto en DGH`
  3. Validar que DGH exista en `COD_SERV_FACT`
  4. Si no existe → dejar en blanco

### 📊 Procesamiento de Archivos
- Consolidación de múltiples archivos Excel
- Generación de archivo de objeciones
- Formato de fechas configurable (D/M/A)
- Procesamiento de filas AU/TA

### 🎨 Interfaz Moderna
- Diseño limpio y minimalista
- Cards con efectos hover
- Diálogos de alerta visuales
- Indicadores de progreso
- Temas de colores personalizados

---

## 📋 Requisitos

### Software
- **Python** 3.10 o superior
- **Windows** 10/11 (para rutas de red UNC)
- Acceso a red corporativa (para rutas `\\MINERVA\...`)

### Dependencias Python
```
flet>=0.9.0
pandas>=2.0.0
openpyxl>=3.0.0
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

### 4. Verificar instalación
```powershell
python -c "import flet; import pandas; print('✅ Dependencias instaladas correctamente')"
```

---

## 💻 Uso

### Ejecutar la aplicación
```powershell
# Método recomendado (como módulo)
python -m app.ui.app

# O directamente
python main.py
```

### Flujo de trabajo típico

#### 1️⃣ **Iniciar sesión**
- Ingresar correo electrónico
- Ingresar contraseña
- El servidor IMAP se auto-detecta o puedes especificarlo
- Marcar "Recordar sesión" para auto-login futuro

#### 2️⃣ **Seleccionar acción**
- Elegir entre: Evitar, Manejar o Responder Glosa

#### 3️⃣ **Configurar búsqueda**
- Seleccionar rango de fechas (obligatorio)
- Elegir EPS a procesar

#### 4️⃣ **Procesar correos**
- Los correos se buscan automáticamente
- Los adjuntos Excel se descargan automáticamente
- Click en "Procesar [EPS]" para generar archivos

#### 5️⃣ **Revisar resultados**
- Se abre automáticamente la carpeta con los archivos generados
- Archivos generados:
  - `[EPS]_consolidado_[fecha].xlsx` - Datos consolidados
  - `Objeciones_[fecha].xlsx` - Archivo para cargar en sistema

---

## 📁 Estructura del Proyecto

```
Glosaap/
├── 📁 app/
│   ├── 📁 api/                    # APIs externas (futuro)
│   ├── 📁 config/
│   │   └── eps_config.py          # Configuración de EPS
│   ├── 📁 core/
│   │   ├── homologacion_service.py    # Servicio CRUD de homologación
│   │   ├── imap_client.py             # Cliente IMAP
│   │   ├── mix_excel_service.py       # Servicio Mix Excel
│   │   ├── mutualser_processor.py     # Procesador MUTUALSER
│   │   ├── coosalud_processor.py      # Procesador COOSALUD
│   │   └── session_manager.py         # Gestión de sesiones
│   ├── 📁 service/
│   │   ├── attachment_service.py      # Servicio de adjuntos
│   │   ├── auth_service.py            # Autenticación
│   │   └── email_service.py           # Servicio de correo
│   └── 📁 ui/
│       ├── 📁 components/
│       │   ├── alert_dialog.py        # Diálogos de alerta
│       │   ├── date_range_picker.py   # Selector de fechas
│       │   ├── eps_card.py            # Tarjetas de EPS
│       │   └── message_row.py         # Filas de mensajes
│       ├── 📁 screens/
│       │   └── eps_screen.py          # Pantalla de selección EPS
│       ├── 📁 views/
│       │   ├── dashboard_view.py      # Vista del dashboard
│       │   ├── homologacion_view.py   # Gestión de homologación
│       │   ├── homologador_manual_view.py  # Homologador manual
│       │   ├── login_view.py          # Vista de login
│       │   ├── messages_view.py       # Vista de mensajes
│       │   ├── mix_excel_view.py      # Herramienta Mix Excel
│       │   └── tools_view.py          # Menú de herramientas
│       ├── app.py                     # Aplicación principal
│       └── styles.py                  # Estilos centralizados
├── 📁 assets/
│   ├── 📁 icons/
│   │   ├── app_logo.png               # Logo de la aplicación
│   │   └── utils.png                  # Icono de utilidades
│   └── 📁 img/
│       ├── 📁 eps/
│       │   ├── mutualser.png          # Logo MUTUALSER
│       │   └── coosalud.png           # Logo COOSALUD
│       ├── evitar_glosa.png           # Icono evitar glosa
│       ├── manejar_glosa.png          # Icono manejar glosa
│       ├── responder_glosa.png        # Icono responder glosa
│       ├── homologar.png              # Icono homologación
│       ├── homologador_manual.png     # Icono homologador manual
│       └── mix_excel.png              # Icono mix excel
├── .gitignore
├── .session.json                      # Sesión guardada (auto-generado)
├── glosaap.spec                       # Configuración PyInstaller
├── main.py                            # Punto de entrada
├── README.md                          # Este archivo
└── requirements.txt                   # Dependencias
```

---

## 🔧 Módulos Principales

### 📧 `imap_client.py`
Cliente IMAP para conexión y búsqueda de correos.
- Conexión SSL a servidores IMAP
- Búsqueda por asunto y fechas
- Descarga de adjuntos Excel
- Timeout configurable (30s por defecto)

### 🔄 `mutualser_processor.py`
Procesador específico para archivos de MUTUALSER.
- Extracción de datos de glosas
- Homologación de códigos
- Generación de archivo de objeciones
- Procesamiento AU/TA

### 🏥 `homologacion_service.py`
Servicio CRUD para gestión de códigos de homologación.
- Soporte multi-EPS
- Agregar/Editar/Eliminar códigos
- Listado con filtros
- Persistencia en archivos Excel de red

### 📊 `mix_excel_service.py`
Servicio para transferir datos entre archivos Excel.
- Mapeo de columnas entre archivos
- Transferencia por coincidencia de valores
- Preservación de datos originales

---

## ⚙️ Configuración

### `app/config/eps_config.py`
Configuración de las EPS disponibles:

```python
EPS_CONFIG = [
    {
        "name": "MUTUALSER",
        "filter": "mutualser",
        "filter_type": "keyword",
        "description": "Mutual SER EPS",
        "image_path": "assets/img/eps/mutualser.png"
    },
    {
        "name": "COOSALUD",
        "filter": "coosalud",
        "filter_type": "keyword",
        "description": "Coosalud EPS",
        "image_path": "assets/img/eps/coosalud.png"
    }
]
```

### `app/ui/styles.py`
Colores y estilos centralizados:

```python
COLORS = {
    "primary": "#2563EB",        # Azul principal
    "primary_dark": "#1E40AF",   # Azul oscuro
    "success": "#10B981",        # Verde éxito
    "error": "#EF4444",          # Rojo error
    "warning": "#F59E0B",        # Amarillo advertencia
    "text_primary": "#1F2937",   # Texto principal
    "text_secondary": "#6B7280", # Texto secundario
    "bg_white": "#FFFFFF",       # Fondo blanco
    "bg_light": "#F9FAFB",       # Fondo claro
}
```

---

## 🛠️ Herramientas

### 📋 Gestión de Homologación
Ubicación: **Herramientas → Gestión Homologación**

- Agregar nuevos códigos de homologación
- Editar códigos existentes
- Eliminar códigos
- Buscar por ERP, Descripción o DGH
- Selector de EPS (MUTUALSER, COOSALUD)

### 🔄 Homologador Manual
Ubicación: **Herramientas → Homologador Manual**

Permite homologar cualquier archivo Excel:
1. Seleccionar EPS
2. Cargar archivo Excel
3. Seleccionar columna a homologar
4. Procesar → genera archivo homologado

**Ruta de salida:** `\\MINERVA\Cartera\GLOSAAP\RESULTADO DE HOMOLAGADOR MANUAL`

### 📊 Mix Excel
Ubicación: **Herramientas → Mix Excel**

Transfiere datos entre dos archivos Excel:
1. Seleccionar archivo origen
2. Seleccionar archivo destino
3. Configurar mapeo de columnas
4. Ejecutar transferencia

---

## 🏥 Procesadores de EPS

### MUTUALSER ✅
**Estado:** Completamente implementado

**Columnas procesadas:**
- Número de factura
- Número de glosa
- Tecnología (código de servicio)
- Cantidad facturada/glosada
- Valor facturado/glosado
- Concepto de glosa
- Código de glosa
- Observación
- Fecha

**Archivo de objeciones generado:**
| Columna | Descripción |
|---------|-------------|
| CDCONSEC | Consecutivo por factura |
| CDFECDOC | Fecha documento (D/M/A) |
| CRNCXC | Número factura formateado |
| CROFECOBJ | Fecha objeción |
| CROOBSERV | Observación REG GLOSA |
| CRNCONOBJ | Código de glosa |
| SLNSERPRO | Código homologado DGH |
| CROVALOBJ | Valor glosado |
| CRDOBSERV | Concepto + Observación |

### COOSALUD ⏳
**Estado:** Pendiente de implementar

---

## 🌐 Rutas de Red

La aplicación utiliza rutas de red UNC para acceder a archivos compartidos:

| Propósito | Ruta |
|-----------|------|
| Homologación MUTUALSER | `\\MINERVA\Cartera\GLOSAAP\HOMOLOGADOR\mutualser_homologacion.xlsx` |
| Homologación COOSALUD | `\\MINERVA\Cartera\GLOSAAP\HOMOLOGADOR\coosalud_homologacion.xlsx` |
| Salida procesamiento | `\\MINERVA\Cartera\GLOSAAP\MUTUALSER\OUTPUTS\` |
| Homologador manual | `\\MINERVA\Cartera\GLOSAAP\RESULTADO DE HOMOLAGADOR MANUAL\` |

> ⚠️ **Nota:** Asegúrate de tener acceso a estas rutas de red antes de usar la aplicación.

---

## 📦 Compilación

### Generar ejecutable con PyInstaller

```powershell
# Instalar PyInstaller
pip install pyinstaller

# Compilar (usando spec existente)
pyinstaller glosaap.spec

# O compilar manualmente
pyinstaller --onefile --windowed --name=Glosaap --add-data="assets;assets" main.py
```

El ejecutable se genera en `dist/Glosaap.exe`

### Opciones de compilación
- `--onefile`: Genera un único archivo .exe
- `--windowed`: Sin ventana de consola
- `--add-data`: Incluye carpeta de assets

---

## ❓ Solución de Problemas

### Error: "No se puede conectar al servidor IMAP"
- Verificar credenciales
- Verificar que el servidor IMAP esté correcto
- Para Gmail: habilitar "Acceso de apps menos seguras" o usar contraseña de aplicación

### Error: "Ruta de red no accesible"
- Verificar conexión a la red corporativa
- Verificar permisos de acceso a `\\MINERVA\`
- Ejecutar como administrador si es necesario

### Error: "No se encontró archivo de homologación"
- Verificar que exista el archivo en la ruta de red
- Verificar nombre exacto del archivo

### Los códigos no se homologan
Posibles causas:
1. El código no existe en `Código Servicio de la ERP`
2. El `Código producto en DGH` no existe en `COD_SERV_FACT`
3. El archivo de homologación está desactualizado

### La aplicación se congela durante la búsqueda
- Esperar el timeout (30 segundos)
- Reducir el rango de fechas
- Verificar conexión a internet

---

## 🔜 Próximas Funcionalidades

- [ ] Procesador COOSALUD
- [ ] Exportación a PDF
- [ ] Dashboard con estadísticas
- [ ] Notificaciones de escritorio
- [ ] Modo oscuro
- [ ] Respaldo automático de configuración
- [ ] Integración con API REST

---

## 👥 Contribuir

1. Fork el repositorio
2. Crear rama feature (`git checkout -b feature/NuevaFuncionalidad`)
3. Commit cambios (`git commit -m 'Agregar nueva funcionalidad'`)
4. Push a la rama (`git push origin feature/NuevaFuncionalidad`)
5. Crear Pull Request

---

## 📄 Licencia

Este proyecto es de uso interno corporativo.

---

## 📞 Soporte

Para reportar bugs o solicitar funcionalidades, crear un issue en el repositorio.

---

<div align="center">

**Desarrollado con ❤️ para la gestión eficiente de glosas médicas**

</div>
