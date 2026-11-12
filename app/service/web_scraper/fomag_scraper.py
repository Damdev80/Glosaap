"""
Scraper para portal de Fomag (Horus) - Informe Prestador (Cuentas médicas)
"""
import os
import re
import sys
import time
from datetime import date, datetime, timedelta

from playwright.sync_api import sync_playwright

from .base_scraper import BaseScraper, auto_install_chromium, find_system_browser

# Configurar stdout para UTF-8 en Windows
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

# El portal no admite consultas de más de 14 días (calendario, inclusivos).
MAX_DIAS_RANGO = 14
TIPO_INFORME = "Trazabilidad"
SESION_TIMEOUT_MS = 180_000     # tiempo para resolver el CAPTCHA a mano
DESCARGA_TIMEOUT_MS = 120_000   # generación del Excel en el portal

# Menú lateral: grupo "Cuentas medicas" (icono mdi-bank) y su enlace.
SELECTOR_MENU_CUENTAS = ".v-list-group__header:has(.mdi-bank)"
SELECTOR_LINK_INFORME = 'a[href="/cuentasMedicas/informePrestador"]'

_FORMATOS_FECHA = ("%Y-%m-%d", "%Y/%m/%d", "%d/%m/%Y", "%d-%m-%Y")


def parse_fecha(valor) -> date:
    """Convierte date/datetime/str (YYYY-MM-DD, YYYY/MM/DD, DD/MM/YYYY) a date."""
    if isinstance(valor, datetime):
        return valor.date()
    if isinstance(valor, date):
        return valor
    texto = str(valor or "").strip()
    for fmt in _FORMATOS_FECHA:
        try:
            return datetime.strptime(texto, fmt).date()
        except ValueError:
            continue
    raise ValueError(f"Fecha inválida: '{texto}' (usa AAAA-MM-DD o DD/MM/AAAA)")


def dividir_rango_fechas(
    desde: date, hasta: date, max_dias: int = MAX_DIAS_RANGO
) -> list[tuple[date, date]]:
    """Divide [desde, hasta] en tramos consecutivos de máximo `max_dias` días."""
    if max_dias < 1:
        raise ValueError("max_dias debe ser >= 1")
    if hasta < desde:
        raise ValueError("La fecha 'Desde' no puede ser mayor que 'Hasta'")
    tramos: list[tuple[date, date]] = []
    actual = desde
    while actual <= hasta:
        fin = min(actual + timedelta(days=max_dias - 1), hasta)
        tramos.append((actual, fin))
        actual = fin + timedelta(days=1)
    return tramos


class FomagScraper(BaseScraper):
    """Automatización para portal de Fomag (Horus): Informe Prestador"""

    def __init__(self, download_dir: str = None, progress_callback=None, perfil_dir: str = None):
        super().__init__(download_dir, progress_callback)
        self.url = "https://horus2.horus-health.com/"

        # Usar AppData para persistencia en Windows
        if perfil_dir is None:
            if sys.platform == 'win32':
                appdata = os.getenv('APPDATA')
                perfil_dir = os.path.join(appdata, 'Glosaap', 'browser_profile')
            else:
                perfil_dir = os.path.join(
                    os.path.dirname(__file__), "..", "..", "..", "temp", "perfil_chrome"
                )

        self.perfil_dir = os.path.abspath(perfil_dir)
        os.makedirs(self.perfil_dir, exist_ok=True)
        self.executable_path: str | None = None

        # Asegurar que los navegadores de Playwright estén instalados
        self._ensure_playwright_browsers()

    def _ensure_playwright_browsers(self):
        """Verifica e instala navegadores de Playwright si es necesario"""
        try:
            # Verificar si el navegador está instalado buscando en la ruta configurada
            browsers_path = os.environ.get('PLAYWRIGHT_BROWSERS_PATH', '')

            # Si no hay ruta configurada, configurarla
            if not browsers_path:
                appdata = os.getenv('APPDATA', os.path.expanduser('~'))
                browsers_path = os.path.join(appdata, 'Glosaap', 'browsers')
                os.environ['PLAYWRIGHT_BROWSERS_PATH'] = browsers_path
                print(f"[INFO] Configurando PLAYWRIGHT_BROWSERS_PATH: {browsers_path}")

            # Buscar carpeta de chromium en la ruta de browsers
            chromium_found = False
            chromium_path = ""

            if browsers_path and os.path.exists(browsers_path):
                print(f"[DEBUG] Buscando en: {browsers_path}")
                for item in os.listdir(browsers_path):
                    if item.startswith('chromium') and not item.startswith('chromium_headless'):
                        chromium_path = os.path.join(browsers_path, item)
                        if os.path.isdir(chromium_path):
                            chromium_found = True
                            print(f"[OK] Navegador Chromium encontrado en: {chromium_path}")
                            break
            else:
                print(f"[ADVERTENCIA] Ruta de browsers no existe: {browsers_path}")

            if chromium_found:
                self.executable_path = None
                return  # Todo OK

            # Si no hay Chromium de Playwright descargado, usar Chrome o Edge del sistema
            system_browser = find_system_browser()
            if system_browser:
                self.executable_path = system_browser
                print(f"[OK] Usando navegador del sistema: {system_browser}")
                return

            # Intentar descarga automática de Chromium con el driver interno
            if auto_install_chromium(getattr(self, "log", None)):
                self.executable_path = None
                print("[OK] Navegador Chromium instalado automáticamente")
                return

            # Fallback: intentar lanzar el navegador directamente
            print("[INFO] Intentando verificar Playwright directamente...")
            try:
                with sync_playwright() as p:
                    browser = p.chromium.launch(headless=True)
                    browser.close()
                    print("[OK] Navegador Chromium verificado correctamente")
                    return  # Todo OK
            except Exception as launch_error:
                print(f"[ERROR] No se pudo lanzar el navegador: {launch_error}")
                raise launch_error

        except Exception as e:
            str(e).lower()

            print("")
            print("="*70)
            print("[INSTALACION REQUERIDA] Navegadores de Playwright no encontrados")
            print("="*70)
            print("")
            print(f"  Error: {e}")
            print("")
            print("  SOLUCION RAPIDA:")
            print("")
            print("  Ejecuta estos comandos en PowerShell (como administrador):")
            print("")
            browsers_path_msg = os.environ.get('PLAYWRIGHT_BROWSERS_PATH', os.path.join(os.getenv('APPDATA', ''), 'Glosaap', 'browsers'))
            print(f"    $env:PLAYWRIGHT_BROWSERS_PATH=\"{browsers_path_msg}\"")
            print("    pip install playwright")
            print("    playwright install chromium")
            print("")
            print("="*70)
            print("")

            raise Exception(f"Navegadores no instalados: {e}")


    # ==================== NAVEGACIÓN / INFORME PRESTADOR ====================

    def _esperar_sesion(self, page, timeout_ms: int = SESION_TIMEOUT_MS):
        """Espera a que el menú principal exista (login + CAPTCHA manual resueltos)."""
        page.wait_for_selector(SELECTOR_MENU_CUENTAS, timeout=timeout_ms)

    def _abrir_informe_prestador(self, page):
        """Cuentas médicas -> Informe prestador (el grupo solo se abre si está cerrado)."""
        header = page.locator(SELECTOR_MENU_CUENTAS).first
        if (header.get_attribute("aria-expanded") or "").lower() != "true":
            header.click()
            time.sleep(0.3)
        page.click(SELECTOR_LINK_INFORME)
        page.wait_for_selector("text=Informe Cuentas Médicas", timeout=15000)

    @staticmethod
    def _campo(page, etiqueta: str):
        """Input de Vuetify ubicado por su etiqueta (los id input-NNN son dinámicos)."""
        return page.locator(f'.v-input:has(label:text-is("{etiqueta}")) input').first

    def _llenar_fecha(self, page, etiqueta: str, valor: date):
        self._campo(page, etiqueta).fill(valor.isoformat())

    def _seleccionar_tipo(self, page, tipo: str = TIPO_INFORME):
        """Abre el combo Tipo y elige la opción (por defecto Trazabilidad)."""
        self._campo(page, "Tipo").click()
        opcion = page.locator(".menuable__content__active .v-list-item").filter(
            has_text=re.compile(tipo, re.IGNORECASE)
        ).first
        opcion.wait_for(timeout=8000)
        opcion.click()

    def _limpiar_busqueda(self, page):
        try:
            page.click('button:has-text("Limpiar Busqueda")', timeout=5000)
            time.sleep(0.3)
        except Exception:
            pass

    def _nombre_libre(self, nombre: str) -> str:
        ruta = os.path.join(self.download_dir, nombre)
        base, ext = os.path.splitext(nombre)
        contador = 1
        while os.path.exists(ruta):
            ruta = os.path.join(self.download_dir, f"{base}_{contador}{ext}")
            contador += 1
        return ruta

    def _descargar_tramo(self, page, desde: date, hasta: date) -> str:
        """Aplica filtros de UN tramo (<=14 días) y descarga el Excel. Retorna la ruta."""
        self._limpiar_busqueda(page)
        self._llenar_fecha(page, "Desde", desde)
        self._llenar_fecha(page, "Hasta", hasta)
        self._seleccionar_tipo(page)

        boton = page.locator('button:has-text("Descargar en Excel")').first
        boton.wait_for(state="visible", timeout=10000)
        # El botón nace deshabilitado; se habilita al completar los filtros.
        for _ in range(20):
            if boton.is_enabled():
                break
            time.sleep(0.25)
        else:
            raise RuntimeError("El botón 'Descargar en Excel' sigue deshabilitado")

        with page.expect_download(timeout=DESCARGA_TIMEOUT_MS) as info:
            boton.click()
        descarga = info.value
        sufijo = os.path.splitext(descarga.suggested_filename or "")[1] or ".xlsx"
        nombre = f"fomag_trazabilidad_{desde:%Y%m%d}_{hasta:%Y%m%d}{sufijo}"
        ruta = self._nombre_libre(nombre)
        descarga.save_as(ruta)
        return ruta

    # ==================== FLUJO PRINCIPAL ====================

    def login_and_download(
        self,
        usuario: str,
        contraseña: str,
        fecha_desde=None,
        fecha_hasta=None,
    ) -> dict:
        """
        Login (CAPTCHA manual) y descarga del Informe Prestador de Horus.

        Flujo: Cuentas médicas -> Informe prestador -> Desde/Hasta + Tipo
        Trazabilidad -> Descargar en Excel. El portal limita cada consulta a
        14 días: un rango mayor se divide en varios tramos consecutivos.

        Args:
            usuario: Usuario de Horus
            contraseña: Contraseña de Horus
            fecha_desde: Inicio del rango (date o 'YYYY-MM-DD'/'DD/MM/YYYY').
            fecha_hasta: Fin del rango. Sin ninguna de las dos: últimos 14 días.

        Returns:
            dict con success, files, message, tramos y fallidos
        """
        try:
            if bool(fecha_desde) != bool(fecha_hasta):
                raise ValueError("Indica ambas fechas (Desde y Hasta) o ninguna")
            if fecha_desde and fecha_hasta:
                desde = parse_fecha(fecha_desde)
                hasta = parse_fecha(fecha_hasta)
            else:
                hasta = date.today()
                desde = hasta - timedelta(days=MAX_DIAS_RANGO - 1)
            tramos = dividir_rango_fechas(desde, hasta)
        except ValueError as ve:
            return {"success": False, "files": 0, "message": f"Error: {ve}",
                    "tramos": 0, "fallidos": []}

        archivos: list[str] = []
        fallidos: list[str] = []

        try:
            with sync_playwright() as p:
                launch_kwargs = {
                    "headless": False,
                    "accept_downloads": True,
                    "viewport": {'width': 1920, 'height': 1080},
                    "args": [
                        '--disable-blink-features=AutomationControlled',
                        '--no-sandbox',
                        '--start-maximized',
                        '--disable-gpu',
                        '--disable-dev-shm-usage',
                    ],
                }
                if getattr(self, "executable_path", None):
                    launch_kwargs["executable_path"] = self.executable_path
                context = p.chromium.launch_persistent_context(
                    self.perfil_dir,
                    **launch_kwargs,
                )
                try:
                    page = context.pages[0] if context.pages else context.new_page()
                    page.set_default_timeout(15000)
                    page.set_default_navigation_timeout(30000)

                    self.log("[SCRAPER] Iniciando sesion en Fomag (Horus)...")
                    page.goto(self.url, wait_until='domcontentloaded')
                    time.sleep(1.5)

                    # Login (si ya hay sesión persistente no aparece el formulario)
                    campo_usuario = page.query_selector('input[id="input-15"]')
                    if campo_usuario:
                        self.log("[LOGIN] Llenando credenciales...")
                        page.fill('input[id="input-15"]', usuario)
                        page.fill('input[id="input-19"]', contraseña)
                        self.log("[IMPORTANTE] Resuelve el CAPTCHA manualmente en el navegador "
                                 "y pulsa Ingresar; la descarga continúa sola al entrar")
                    else:
                        self.log("[OK] Sesion activa - No se requiere CAPTCHA")

                    # Espera (hasta 3 min) a que el usuario complete CAPTCHA/login.
                    self._esperar_sesion(page)
                    self.log("[OK] Sesion iniciada")

                    self.log("[NAVEGACION] Cuentas medicas -> Informe prestador")
                    self._abrir_informe_prestador(page)

                    total = len(tramos)
                    self.log(f"[INFO] Rango {desde:%d/%m/%Y} - {hasta:%d/%m/%Y}: "
                             f"{total} consulta(s) de máx. {MAX_DIAS_RANGO} días")

                    for i, (t_desde, t_hasta) in enumerate(tramos, start=1):
                        etiqueta = f"{t_desde:%d/%m/%Y} - {t_hasta:%d/%m/%Y}"
                        self.log(f"[TRAMO {i}/{total}] Descargando {etiqueta}...")
                        try:
                            ruta = self._descargar_tramo(page, t_desde, t_hasta)
                            archivos.append(ruta)
                            self.log(f"[OK] TRAMO {i}/{total}: {os.path.basename(ruta)}")
                        except Exception as tramo_error:
                            fallidos.append(etiqueta)
                            self.log(f"[ADVERTENCIA] TRAMO {i}/{total} ({etiqueta}) sin descarga: "
                                     f"{str(tramo_error)[:80]}")
                            continue
                finally:
                    time.sleep(1)
                    context.close()
        except Exception as e:
            return {"success": False, "files": len(archivos), "message": f"Error: {str(e)}",
                    "tramos": len(tramos), "fallidos": fallidos}

        if not archivos:
            return {
                "success": False,
                "files": 0,
                "message": "No se descargó ningún archivo (sin datos en el rango o filtros no aplicados)",
                "tramos": len(tramos),
                "fallidos": fallidos,
            }

        mensaje = f"Descargados {len(archivos)} de {len(tramos)} archivo(s) en {self.download_dir}"
        if fallidos:
            mensaje += f" | Sin descarga: {', '.join(fallidos)}"
        self.log(f"[COMPLETADO] {mensaje}")
        return {
            "success": True,
            "files": len(archivos),
            "message": mensaje,
            "tramos": len(tramos),
            "fallidos": fallidos,
        }
