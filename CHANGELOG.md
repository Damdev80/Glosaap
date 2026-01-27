# Changelog - Glosaap

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
