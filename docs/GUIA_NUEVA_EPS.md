# Guía: agregar una nueva EPS – Glosaap

Procedimiento probado (ejemplo real: Previsora Seguros SOAT, releases
0.11.29–0.11.31). Seguirlo en orden convierte una integración nueva en
trámite en vez de proyecto.

## 0. Caracterizar el correo y el adjunto (antes de codificar)

1. Asunto exacto y si el número cambia por correo
   (ej. `Registrado: Notificación agrupada 9927649` → el número varía).
2. Remitente real (`From` visto en el webmail, no el que "debería" ser).
3. Adjunto: ¿Excel o PDF? ¿Uno por correo o varios? ¿Tablas con líneas
   o texto suelto? Pide **un archivo real** de ejemplo desde el día 1.
4. Columnas de negocio: ¿cuál es la factura? ¿cuál el código a homologar?
   ¿cuál el valor objetado? ¿de dónde sale la fecha de objeción
   (normalmente, fecha de recepción del correo)?

Decisiones que salen de aquí: `subject_pattern` (substring o exacto),
`sender_filter`, `identify_files` (xlsx vs pdf) y columnas del registro.

## 1. Configuración (`app/config/eps_config.py`)

Crear clase `XxxEps(EpsInfo)` con `enabled=True` y agregarla a
`EPS_CONFIG`. Ejemplo real (Previsora):

```python
class PrevisoraEps(EpsInfo):
    def __init__(self):
        super().__init__(
            name="Previsora",
            filter_value="previsora",
            filter_type="subject_exact_pattern",  # match por substring
            subject_pattern="Registrado: Notificación agrupada",
            processor_class="PrevisoraProcessor",
            enabled=True,
            sender_filter="radicacionambulatorio@laconcepcion.org",
            homologador_file="previsora",  # clave de HOMOLOGADOR_FILES
        )
```

Ojo: `filter_type="subject_exact_pattern"` hace match por substring
(`patrón in asunto`), así que tolera `Fwd:` y números variables.
`get_search_keyword()` usa el patrón completo para el SEARCH IMAP:
si lleva tildes, `imap_client` lo envía en UTF-8 solo (soportado desde
0.11.29).

## 2. Rutas (`app/config/settings.py` + `homologacion_service.py`)

1. `NETWORK_PATHS`: agregar `xxx_output` bajo `REPOSITORIO DE RESULTADOS`.
2. `HOMOLOGADOR_FILES`: agregar `xxx` → nombre exacto del xlsx.
3. `HomologacionService.EPS_FILES / EPS_COLUMNAS / COL_HOMOLOGO /
   COL_EXTRA`: misma clave, con los nombres reales de columna del
   archivo (respeta mayúsculas del Excel del cliente).

Si la tabla de homologación aún no la pasan: el procesador debe
funcionar igual conservando el código original con warning
(ver punto 3), y la tabla se conecta después sin cambiar lógica.

## 3. Procesador (`app/service/processors/xxx_processor.py`)

Hereda de `BaseProcessor` y respeta el Template Method
(`identify_files → validate_files → extract_data → homologate`).
Reglas que rompen releases si se ignoran:

- `identify_files` retorna **TODOS** los archivos válidos, nunca solo
  el primero. Solo filtra por extensión (el PDF de Sanitas se ignora;
  el PDF de Previsora **es** el insumo).
- `homologate` retorna `pd.DataFrame` (contrato de la base). Si el
  flujo necesita 2 hojas/archivos, el dict se compone en
  `process_glosas`, no en `homologate`.
- Normaliza códigos con `_normalize_code` (strip, upper, sin `.0`).
- Factura con `_formatear_crncxc` (`FC0000{dígitos}`), fechas con
  `_formatear_fecha_dmy`, valores con `_obtener_valor_numerico`
  (nunca `replace('.','')`: destruye decimales).
- Fecha de objeción = fecha de recepción **por archivo**
  (`attachment_service.get_file_metadata(path)` → `fecha_correo`;
  fallback a `email_date` global, luego a hoy). Nunca una sola fecha
  para todo el lote si los correos son distintos.
- Quita columnas internas (`_FACTURA`, `fecha_correo`) antes de
  exportar con `_drop_internal_columns`.
- Sin `print` en loops; usa `app.config.settings.logger`.
- Nombres de salida con timestamp:
  `PREFIJO_REGISTRO_<ts>.xlsx` / `Objeciones_PREFIJO_<ts>.xlsx`.

## 4. Cableado (`email_service.py` + `app/ui/app.py`)

1. `EmailService`: `xxx_output_dir`, `xxx_processor` (vía
   `_resolve_homologador`, que tolera homologador ausente) y método
   `procesar_xxx(archivos=None, email_date=None)` con el contrato
   `{success, message, output_file, objeciones_file, path, resumen}`.
   Para PDF usa `attachment_service.get_session_pdf_files()`.
2. `app.py`: botón `Procesar XXX` en `on_eps_selected` (`process_eps_btn`
   + `.data = "xxx"`) y rama `elif eps_type == "xxx"` en
   `process_eps_files` con el mismo patrón de las demás EPS
   (cancelación, resumen, `AlertDialog.show_processing_complete`).

## 5. Vistas manuales

1. `homologador_manual_view.py`: opción en `eps_dropdown`,
   entrada en `HOMOLOGACION_PATHS` (o fallback a
   `get_homologador_path`), logo con fallback si no hay png en
   `assets/img/eps/`, y rama en `_buscar_codigo_homologado`
   (búsqueda insensible a mayúsculas si el Excel del cliente mezcla
   casos). Convención de imagen: `assets/img/eps/<eps>.png`
   (si falta, `EpsCard` usa el emoji sin romperse).
2. `homologacion_view.py`: colores y etiquetas por clave de EPS
   (agrupa bajo una sola tarjeta solo si la EPS tiene 2 tablas,
   como Sanitas Normal/Insumos).

## 6. Tests (`tests/test_xxx_processor.py`)

Mínimo exigible (espejo de `test_previsora_processor.py`):

- `identify` (filtra extensiones, retorna todos), `validate`
  (ok / faltante / vacío).
- Parseo/extracción con texto o Excel sintético (sin red, sin IMAP).
- `homologate`: factura formateada, código homologado o conservado,
  valores y observación, export sin columnas internas.
- `process_glosas`: genera los archivos con nombre esperado,
  fecha por archivo, mensaje `[OK]`.
- Wiring: rutas en settings, `get_eps_by_name`, export en
  `processors`, contrato de `email_service.procesar_xxx`.

## 7. Cierre

1. `python bump.py X.Y.Z` y completar los bullets del CHANGELOG
   (nunca dejar `(completar)`).
2. `pytest` en verde + `ruff check` limpio.
3. Commit + tag `vX.Y.Z` + push (CI publica el release).
4. Actualizar `MANUAL_USUARIO.md` si cambió el flujo del operador y
   esta guía si el procedimiento cambió.
