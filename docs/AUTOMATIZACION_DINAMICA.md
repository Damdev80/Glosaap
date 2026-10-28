# Automatización total con Dinámica (DGH) — qué necesitamos y para qué

> Documento de trabajo. Objetivo: eliminar los pasos manuales del proceso de
> glosas conectando Glosaap al sistema Dinámica Gerencial Hospitalaria (DGH).
> Complementa `PROPUESTA_REUNION.md` (migración de homologación a SQL Server).

---

## 1. El proceso hoy (lo que ya hace Glosaap)

```
Correo IMAP / Portales web (Familiar, Fomag)
   → Excel DETALLE + GLOSA por EPS
      → Homologación de códigos (Excels en \\MINERVA, a mano)
         → Consolidado + archivo de OBJECIONES (formato de cada EPS)
            → Carga MANUAL al sistema + carpetas a mano
```

Lo que sigue siendo manual: mantener homologadores, descargar y mover
archivos, validar valores contra lo facturado, redactar justificaciones,
cargar respuestas y hacer seguimiento (¿la glosa se levantó o no?).

## 2. Qué necesitamos de Dinámica

Nada de escritura: **solo lectura** (vistas SQL dedicadas, no tablas directas,
para no acoplarnos a la versión de DGH). Un login de mínimo privilegio cuyas
credenciales van en keyring, como el resto de secretos de Glosaap.

### Tabla 1 — Catálogo de servicios/procedimientos (maestro)
**Para qué:** reemplazar los homologadores Excel y validar códigos contra el
catálogo vivo.

| Campo necesario | Ejemplo | Para qué se usa |
|---|---|---|
| Código interno (prestador/facturación) | `COD_SERV_FACT`, código ERP | Clave de homologación |
| Código CUPS | `890201` | Homologación estándar |
| Código CUM (medicamentos/insumos) | `20003839-6` | Vía insumos Sanitas |
| IUM / RDA | según DGH | Vía insumos Sanitas |
| Descripción | `CONSULTA MEDICA` | `MVC EN <procedimiento>`, reportes |
| Estado (habilitado/suspendido) | bool/fecha | Alertar códigos muertos |
| Unidad, grupo/subgrupo | texto | Filtros y reportes |

Desbloquea: homologación sin Excel, validación de `COD_SERV_FACT`, y el
módulo **Evitar Glosa** (validar antes de facturar).

### Tabla 2 — Facturación emitida (encabezado + detalle)
**Para qué:** cruzar lo que la EPS glosa contra lo que realmente se facturó.

| Campo necesario | Para qué se usa |
|---|---|
| Número de factura, fecha, EPS (NIT/código) | Emparejar con DETALLE/GLOSA |
| Servicio/código + cantidad + valor unitario/total por línea | Detectar diferencias de valores y cantidades |
| Paciente, autorización, sede | Justificación automática (ver Tabla 5) |
| Estado de la factura (radicada, pagada, glosada) | Seguimiento |

Desbloquea: pre-validación automática factura vs. glosa, `CROVALOBJ` sin
digitación, detección de glosas improcedentes (cobro que sí corresponde).

### Tabla 3 — Contratos y tarifas por EPS
**Para qué:** validar glosas de tarifas sin mirar manuales en papel.

| Campo necesario | Para qué se usa |
|---|---|
| EPS + manual tarifario pactado (ISS/SOAT/propio) + vigencia | Saber contra qué comparar |
| Código servicio + tarifa pactada | Validar `VALOR GLOSADO` vs pactado |
| Reglas (descuentos, topes, paquetes) | Justificar o aceptar de entrada |

Desbloquea: **Evitar Glosa** (joya de la corona: facturar ya validado) y
respuesta automática a glosas de tarifa.

### Tabla 4 — Glosas y respuestas registradas (histórico)
**Para qué:** cerrar el ciclo (hoy nadie sabe si la glosa se levantó).

| Campo necesario | Para qué se usa |
|---|---|
| Factura + EPS + fecha radicación + valor glosado + código objeción | Emparejar con lo trabajado en Glosaap |
| Respuesta enviada (fecha, archivo/número) | Trazabilidad |
| Resultado (levantada / ratificada / parcial) + fecha | Aprender qué justificaciones ganan |

Desbloquea: tablero real (recuperación por EPS/mes), priorización por
probabilidad de éxito, y dejar de responder dos veces lo mismo.

### Tabla 5 — Autorizaciones
**Para qué:** las glosas `AU` son de las más frecuentes y las más
automatizables.

| Campo necesario | Para qué se usa |
|---|---|
| Factura/servicio + número de autorización + vigencia | Adjuntar/justificar AU sin buscar papeles |

### Tabla 6 — Terceros / EPS (maestro)
NIT, razón social y códigos por EPS. Desbloquea normalizar nombres
(Mutualser/MUTUALSER/mutualser hoy se comparan a mano en varios puntos).

## 3. Mapa: qué automatiza cada tabla

| Paso manual hoy | Se automatiza con |
|---|---|
| Mantener homologadores Excel | Tabla 1 (catálogo vivo) |
| Validar códigos y `COD_SERV_FACT` | Tabla 1 |
| Cuadrar valores factura vs. glosa | Tabla 2 |
| Justificar AU a mano | Tablas 2 + 5 |
| Responder glosas de tarifa | Tabla 3 |
| Cargar y hacer seguimiento | Tabla 4 (más conector de cargue, fase 2) |
| Prevenir antes de facturar (Evitar Glosa) | Tablas 1 + 2 + 3 |

## 4. Requisitos técnicos (para el DBA / sistemas)

1. **Vistas de lectura** sugeridas (nombres a convenir):
   `vw_glosaap_servicios`, `vw_glosaap_facturacion`,
   `vw_glosaap_tarifas`, `vw_glosaap_glosas`,
   `vw_glosaap_autorizaciones`, `vw_glosaap_terceros`.
2. Login SQL **solo-lectura** sobre esas vistas; credencial en keyring.
3. Acceso de red desde las máquinas Glosaap (misma red que `\\MINERVA`).
4. Refresco: las vistas leen en vivo; sin ETL en fase 1.
5. Glosaap guarda su estado propio (SQLite/SQL Server local según
   `PROPUESTA_REUNION.md`); **no escribe en DGH**.

## 5. Roadmap sugerido

- **Fase 1 (rápida):** Tablas 1 + 6 → homologación sin Excel + EPS normalizadas.
- **Fase 2:** Tabla 2 → cruce factura vs. glosa + valores automáticos.
- **Fase 3:** Tablas 3 + 5 → Evitar Glosa + justificación AU automática.
- **Fase 4:** Tabla 4 → tablero de recuperación y priorización.

## 6. Preguntas abiertas (para Dayana / DBA / sistemas)

1. ¿Nombres reales de tablas/columnas en su versión de DGH para mapear las vistas?
2. ¿Existe histórico de respuestas de glosas en DGH o vive en otro lado (Excel, otro sistema)?
3. ¿Las tarifas pactadas por EPS están en DGH o en contratos físicos?
4. ¿Quién autoriza el login de lectura y quién es dueño de cada dato?
5. ¿Hay política de datos personales (pacientes) que limite qué campos exponemos?
