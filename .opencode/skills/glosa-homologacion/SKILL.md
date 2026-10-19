---
name: Glosa Homologación
description: Fuente única de homologadores, normalización y backups con rotación
---

# Glosa Homologación

Úsalo antes de tocar `app/core/homologacion_service.py`, `app/core/homologar_observacion.py` o rutas de homologador.

## Reglas
1. Fuente única: `app/config/settings.py` (`HOMOLOGADOR_FILES`, `get_homologador_path()`). Elimina las otras dos convenciones (`HOMOLOGADOR_MUTUALSER.xlsx` en mayúsculas vs `mutualser_homologacion.xlsx`).
2. `eps_config.py` tiene duplicado `Coosalud`/`Cosalud` y EPS sin procesador con `enabled=True`. Solo `Mutualser` y `Coosalud` quedan habilitadas; resto `enabled=False`.
3. Normalización única `_normalize_code` compartida (la de Coosalud es la referencia). `homologar_observacion.py` está 90% duplicado con `MutualserProcessor`: extrae lookup común, no parches dobles.
4. Caché `_file_cache/_search_cache` con `threading.RLock`; invalida DESPUÉS de guardar con éxito, no antes.
5. `_guardar` con backup y rotación (máx 10 en `backups/`); sin backups ilimitados en `\\MINERVA`.
6. `listar` con índice/búsqueda vectorizada, no `apply(axis=1)` O(n*m).
7. Borra código muerto `homologacion_service.py:358` tras `return`.

## Rutas
- Base `\\MINERVA\Cartera\GLOSAAP`. `get_output_dir` debe buscar `f"{eps}_output"` en NETWORK_PATHS (el bug actual nunca matchea y cae a TEMP).
