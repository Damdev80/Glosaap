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
            "(Familiar, Fomag) con tus credenciales. Los archivos quedan "
            "listos para procesar igual que los del correo."
        ),
    },
}

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
