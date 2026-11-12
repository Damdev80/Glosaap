"""Contenido de las guías interactivas de Glosaap (sin dependencias de UI).

Todo el texto y la lógica de estado viven aquí para poder probarlos sin
Flet: `app/ui/components/guide_overlay.py` solo renderiza, y `app.py`
decide cuándo mostrar cada cosa.
"""
from __future__ import annotations

GUIDE_VERSION = "v1"
STORAGE_KEY = f"glosaap_guide_seen_{GUIDE_VERSION}"

TOUR_STEPS: list[dict[str, str]] = [
    {
        "title": "Bienvenido a Glosaap",
        "body": (
            "Glosaap busca correos con glosas, descarga los adjuntos, "
            "procesa por EPS, homologa códigos y genera el archivo de "
            "objeciones listo para montar. Esta guía te lleva por el "
            "flujo completo en 4 pasos."
        ),
    },
    {
        "title": "1. Elige EPS y fechas",
        "body": (
            "En el Dashboard pulsa Manejar Glosa, elige la EPS y selecciona "
            "el rango Desde/Hasta (ambas fechas son obligatorias). Cada EPS "
            "busca con su propio asunto y remitente."
        ),
    },
    {
        "title": "2. Correos y descarga",
        "body": (
            "La app descarga los adjuntos sola al encontrar los correos. "
            "La cinta de pasos te muestra: Buscar → Descargar → Procesar → "
            "Revisar. Si un correo no aparece, revisa el rango de fechas "
            "y que esté en INBOX."
        ),
    },
    {
        "title": "3. Procesa",
        "body": (
            "Pulsa el botón Procesar de tu EPS y espera sin cerrar la app; "
            "puedes Cancelar si tarda. Al terminar verás cuántos registros "
            "y cuántos códigos quedaron homologados."
        ),
    },
    {
        "title": "4. Revisa y pide ayuda",
        "body": (
            "Abre la carpeta del resultado desde el diálogo final. Los no "
            "homologados se agregan en Herramientas → Homologación. El "
            "botón ? de cada pantalla abre la ayuda de esa vista. Si un "
            "homologador falta, el proceso continúa igual y avisa en el "
            "resumen: no es un error que bloquee."
        ),
    },
]

HELP_BY_VIEW: dict[str, dict[str, str]] = {
    "dashboard": {
        "title": "Dashboard: ¿qué hago aquí?",
        "body": (
            "Manejar Glosa inicia el flujo (EPS → correos → procesar). "
            "Herramientas abre homologación, Mix Excel y homologador manual. "
            "Descarga Web es el método alterno sin correo. ¿Primera vez? "
            "Relanza el tour desde este diálogo."
        ),
    },
    "method_selection": {
        "title": "Método de trabajo",
        "body": (
            "Correo electrónico busca glosas en tu buzón IMAP; Descarga Web "
            "las trae desde los portales. El resto del flujo es el mismo."
        ),
    },
    "eps": {
        "title": "Selección de EPS y fechas",
        "body": (
            "Primero el rango Desde/Hasta (obligatorio), luego la tarjeta "
            "de la EPS. Sin fechas no se puede buscar. Los correos se "
            "filtran por asunto y remitente propios de cada EPS."
        ),
    },
    "messages": {
        "title": "Correos: buscar, descargar, procesar",
        "body": (
            "1) La búsqueda descarga los adjuntos sola. 2) Verifica el "
            "conteo de Excel listos. 3) Pulsa Procesar y espera el resumen. "
            "Si un PDF de Previsora no da filas, el diálogo trae la pista "
            "y queda un PREVISORA_DEBUG_*.txt en la salida. Si un "
            "homologador falta, se procesa igual conservando códigos."
        ),
        # Controles que parpadean al abrir esta ayuda (focus guiado).
        "flash": ["checklist", "process"],
    },
    "tools": {
        "title": "Herramientas",
        "body": (
            "Gestión Homologación: ver, agregar y carga masiva de códigos "
            "(Sanitas muestra sus 2 tablas agrupadas). Mix Excel: pasar "
            "datos entre Excels. Homologador manual: homologar un archivo "
            "por columna (elige primero la tabla de Sanitas si aplica)."
        ),
    },
    "homologacion": {
        "title": "Gestión de homologación",
        "body": (
            "Pestaña Individual para un código, Carga Masiva con Excel de "
            "2 columnas (3 para Sanitas Insumos: CUM, IUM RDA, producto). "
            "La tabla de verificación marca válidos, duplicados y errores "
            "antes de agregar. Todo cambio guarda backup automático."
        ),
    },
    "homologador_manual": {
        "title": "Homologador manual",
        "body": (
            "1) Elige EPS (y tabla si es Sanitas: Normal o Insumos). "
            "2) Carga el Excel. 3) Elige la columna a homologar. "
            "4) Homologar: reemplaza por el código homólogo y genera el "
            "archivo; con estructura Sanitas además genera Objeciones."
        ),
    },
    "mix_excel": {
        "title": "Mix Excel",
        "body": (
            "Transfiere columnas entre dos Excels: elige origen y destino, "
            "mapea las columnas y genera el archivo combinado. Útil para "
            "cruzar reportes antes de responder una glosa."
        ),
    },
    "web_download": {
        "title": "Descarga web",
        "body": (
            "Método alterno al correo: descarga glosas desde los portales "
            "(Familiar, Fomag) con tus credenciales. Fomag usa Cuentas "
            "médicas → Informe prestador (Trazabilidad, Excel): máx. 14 días "
            "por consulta; un rango mayor se descarga en varios tramos. El "
            "CAPTCHA se resuelve a mano. Los archivos quedan listos para "
            "procesar igual que los del correo."
        ),
    },
}

HELP_BY_EPS: dict[str, dict[str, str]] = {
    "mutualser": {
        "title": "Reglas de procesamiento: Mutualser",
        "body": (
            "• Filtro de correo: asunto \"Objeciones de glosa Factura FC\".\n"
            "• Entrada: archivos Excel/CSV (.xlsx, .xls, .xlsm, .xlsb, .csv); "
            "detecta el encabezado de detalles y descarta filas vacías o de TOTAL/SUMA.\n"
            "• Homologación: cruza Tecnología en mutualser_homologacion.xlsx "
            "(Código Servicio ERP → Código producto en DGH, validando contra COD_SERV_FACT).\n"
            "• Reglas de Objeciones: factura FC0000{dígitos} (CRNCXC), valores "
            "numéricos limpios (CROVALOBJ) y observación combinada (Concepto - Observación).\n"
            "• Fusión AU/TA y SO4801: en un mismo (factura, servicio), une glosas "
            "AU+TA en AU con \" // \" y, si existe SO4801, absorbe los demás conceptos en SO4801.\n"
            "• Salida: MUTUALSER_consolidado_<ts>.xlsx y Objeciones_<ts>.xlsx."
        ),
    },
    "coosalud": {
        "title": "Reglas de procesamiento: Coosalud",
        "body": (
            "• Filtro de correo: asunto \"Reporte Glosas y Devoluciones\".\n"
            "• Entrada: empareja 2 archivos Excel por factura "
            "(DETALLE FC{num}.xlsx + GLOSAS FC{num}.xlsx). Ignora archivos de DEVOLUCIÓN.\n"
            "• Homologación de servicios: cruza codigo_servicio de DETALLE en "
            "coosalud_homologacion.xlsx (ERP → DGH) y homologa códigos dentro de la observación.\n"
            "• Homologación de glosa (Res. 2284): transforma códigos numéricos según el "
            "1.er dígito (1→FA, 2→TA, 3→SO, 4→AU, 5→CO, 6→CL) + resto (mín. 2 dígitos) + "
            "\"01\" (ej. 203→TA0301; especial 430→AU2103).\n"
            "• Salida: COOSALUD_GLOSAS_<ts>.xlsx (hojas Detalles y Glosa) y "
            "Objeciones_<ts>.xlsx con fecha de correo por archivo."
        ),
    },
    "sanitas": {
        "title": "Reglas de procesamiento: Sanitas",
        "body": (
            "• Filtro de correo: asunto \"Referencia: Informe Glosas EPS Sanitas\" "
            "de cuentasmedicaseps@epssanitas.notify-it.com.\n"
            "• Entrada: 1 archivo .xlsx por correo (ignora PDFs adjuntos y devoluciones).\n"
            "• Homologación en 2 vías (CODIGO PROCEDIMIENTO PRESTADOR):\n"
            "  - Insumos (\"INSUMOS Y MEDICAMENTOS INTRAHOSPITALARIOS\"): cascada "
            "CUM → IUM RDA → CODIGO PRODUCTO en sanitas_homologador.xlsx.\n"
            "  - Normal (resto de filas): ERP → DGH en sanitas_homologador_2.xlsx. "
            "Sin match conserva el código original.\n"
            "• Reglas de Objeciones: CRNCONOBJ (6 caracteres) = GENERAL (1-6 → FA/TA/SO/AU/CO/CL) "
            "+ ESPECÍFICO (2 dígitos) + APLICACIÓN (2 dígitos, \"01\" si vacía). "
            "Si OBSERVACIONES viene vacía usa \"MVC EN <procedimiento>\".\n"
            "• Salida: SANITAS_GLOSAS_<ts>.xlsx y Objeciones_SANITAS_<ts>.xlsx."
        ),
    },
    "previsora": {
        "title": "Reglas de procesamiento: Previsora",
        "body": (
            "• Filtro de correo: asunto \"Registrado: Notificación agrupada\" "
            "de radicacionambulatorio@laconcepcion.org.\n"
            "• Entrada: archivos PDF de \"Liquidación de reclamaciones\" (uno o varios por correo). "
            "Extrae Nro Factura, Cant., Código, Procedimiento, %, Cobrado, Objeción (> 0), "
            "Liquidado y Observación.\n"
            "• Homologación: cruza CODIGO del PDF en Previsora_homologador.xlsx "
            "(CODIGO PREVISORA → codigo homologado). Sin match conserva el código original.\n"
            "• Reglas de Objeciones: 15 columnas estándar (CRNCXC=FC0000{dígitos}, "
            "CROFECOBJ=fecha del correo, CROVALOBJ=valor objetado, SLNSERPRO=código homologado, "
            "CRNCONOBJ vacío por origen PDF). Si un PDF no da filas, genera PREVISORA_DEBUG_<ts>.txt.\n"
            "• Salida: PREVISORA_REGISTRO_<ts>.xlsx y Objeciones_PREvisora_<ts>.xlsx."
        ),
    },
}


def get_eps_help(eps_key_or_info: str | dict | None) -> dict[str, str] | None:
    """Resuelve las reglas de procesamiento de una EPS por clave, nombre o dict."""
    if not eps_key_or_info:
        return None
    if isinstance(eps_key_or_info, dict):
        raw = str(
            eps_key_or_info.get("filter")
            or eps_key_or_info.get("key")
            or eps_key_or_info.get("name")
            or ""
        )
    else:
        raw = str(eps_key_or_info)
    key = raw.strip().lower()
    if key == "sanitas_insumos":
        key = "sanitas"
    return HELP_BY_EPS.get(key)

CHECKLIST_LABELS = ("Buscar", "Descargar", "Procesar", "Revisar")


def checklist_state(
    found_messages: int, excel_files: int, processed: bool
) -> list[dict[str, str]]:
    """Estado de la cinta de pasos de correos (puro, testeable).

    - Buscar listo si hay >=1 correo; Descargar listo si hay >=1 Excel.
    - Procesar listo si processed; Revisar listo si processed.
    - El paso "actual" es el primero no listo; si todo listo, Revisar.
    """
    found = max(0, int(found_messages or 0))
    excels = max(0, int(excel_files or 0))
    done = [found > 0, excels > 0, bool(processed), bool(processed)]
    states: list[dict[str, str]] = []
    current_assigned = False
    for i, label in enumerate(CHECKLIST_LABELS):
        if done[i]:
            state = "done"
        elif not current_assigned:
            state = "current"
            current_assigned = True
        else:
            state = "pending"
        states.append({"label": label, "state": state})
    return states


def should_show_tour(storage_get) -> bool:
    """True si el tour nunca se marcó como visto (inyectable para tests)."""
    try:
        return not storage_get(STORAGE_KEY)
    except Exception:
        return False
