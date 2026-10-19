---
name: Glosa EPS Processor
description: Crear o corregir procesadores EPS y homologación sin duplicar lógica
---

# Glosa EPS Processor

Úsalo antes de tocar `app/service/processors/`, `app/core/mutualser_processor.py` o `app/core/homologacion_service.py`.

## Workflow
1. Lee `app/service/processors/base_processor.py` completo. Respeta su Template Method (`identify_files`, `validate_files`, `extract_data`, `homologate`).
2. No crees una cuarta variante de merge: Coosalud ya tiene 4 `_prepare_glosa_merge*` casi idénticas, usa solo la vigente (`_by_id_detalle_direct`) y elimina muertas.
3. `homologate` debe retornar `pd.DataFrame` como declara la base. Si necesitas 2 hojas, compón el dict en `process_glosas`, no en `homologate`.
4. Normaliza códigos con `_normalize_code` (strip, upper, quitar ceros/prefijos) igual en Mutualser y Coosalud.
5. Formateadores únicos: `CRNCXC` como `FC0000{dígitos}`, fechas `D/M/A`, valores numéricos preservando decimales. No uses `replace('.','')` que destruye decimales.
6. `identify_files` debe emparejar TODOS los pares DETALLE+GLOSAS por número de factura, nunca solo `pairs[0]`.
7. Quita columnas internas (`_FACTURA`, `fecha_correo` cruda) antes de exportar el Excel entregado.
8. Quita `print` debug en loops; usa `app.config.settings.logger`.

## Prohibido
- Fallback al "primer xlsx" si no hay match de homologador: falla explícito.
- Concatenar `AU/TA` con `" \\\\ "`; usa `//` como el resto del sistema.
