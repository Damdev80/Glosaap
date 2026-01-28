# Changelog - Glosaap

Todos los cambios notables en este proyecto serán documentados en este archivo.

El formato está basado en [Keep a Changelog](https://keepachangelog.com/es-ES/1.0.0/).

---

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
