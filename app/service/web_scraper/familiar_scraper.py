"""
Scraper para portal de Familiar de Colombia
"""
from playwright.sync_api import sync_playwright
import os
import time
from .base_scraper import BaseScraper


class FamiliarScraper(BaseScraper):
    """Automatización para portal de Familiar de Colombia"""
    
    def __init__(self, download_dir: str = None, progress_callback=None):
        super().__init__(download_dir, progress_callback)
        self.url = "https://eps.familiardecolombia.com/sie/loginIps.xhtml"
        self._ensure_playwright_browsers()
    
    def _ensure_playwright_browsers(self):
        """Verifica que los navegadores de Playwright estén instalados"""
        browsers_path = os.environ.get('PLAYWRIGHT_BROWSERS_PATH', '')
        
        # Si no hay ruta configurada, configurarla
        if not browsers_path:
            appdata = os.getenv('APPDATA', os.path.expanduser('~'))
            browsers_path = os.path.join(appdata, 'Glosaap', 'browsers')
            os.environ['PLAYWRIGHT_BROWSERS_PATH'] = browsers_path
        
        # Buscar carpeta de chromium
        if browsers_path and os.path.exists(browsers_path):
            for item in os.listdir(browsers_path):
                if item.startswith('chromium') and not item.startswith('chromium_headless'):
                    print(f"[OK] Navegador Chromium encontrado")
                    return
        
        # Fallback: intentar lanzar
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                browser.close()
                return
        except Exception as e:
            print(f"[ERROR] Navegador no encontrado: {e}")
            print("  Ejecuta: playwright install chromium")
            raise
    
    def login_and_download(self, nit: str, usuario: str, contraseña: str, 
                          fecha_inicio: str = None, fecha_fin: str = None) -> dict:
        """
        Login y descarga de archivos de Familiar de Colombia
        
        Args:
            nit: NIT de la IPS
            usuario: Usuario
            contraseña: Contraseña
            fecha_inicio: Fecha inicio (formato: YYYY/MM/DD)
            fecha_fin: Fecha fin (formato: YYYY/MM/DD)
            
        Returns:
            dict con resultado
        """
        try:
            with sync_playwright() as p:
                # Navegador optimizado
                browser = p.chromium.launch(
                    headless=False,
                    args=[
                        '--disable-blink-features=AutomationControlled',
                        '--no-sandbox',
                        '--disable-dev-shm-usage',
                        '--disable-gpu',
                        '--disable-extensions',
                        '--disable-infobars',
                        '--disable-notifications',
                        '--blink-settings=imagesEnabled=false'
                    ]
                )
                
                context = browser.new_context(
                    accept_downloads=True,
                    viewport={'width': 1280, 'height': 720}
                )
                
                context.set_default_timeout(10000)
                page = context.new_page()
                
                # Bloquear recursos innecesarios
                page.route("**/*.{png,jpg,jpeg,gif,svg,ico,woff,woff2}", lambda route: route.abort())
                
                # Login
                self.log("[SCRAPER] Iniciando sesión en Familiar...")
                page.goto(self.url, wait_until='domcontentloaded')
                
                page.fill('input[name="j_idt16:j_idt20"]', nit)
                page.fill('input[name="j_idt16:j_idt24"]', usuario)
                page.fill('input[name="j_idt16:j_idt28"]', contraseña)
                
                page.click('button[type="submit"]')
                page.wait_for_load_state('networkidle')
                self.log("[OK] Login completado")

                # Navegar a Respuesta Glosa
                try:
                    self.log("[SCRAPER] Navegando a Respuesta Glosa...")
                    page.wait_for_selector('a[id="j_idt95"]', state='visible', timeout=8000)
                    
                    page.evaluate("""
                        PrimeFaces.addSubmitParam('miaHomeIps',{'j_idt95':'j_idt95'}).submit('miaHomeIps');
                    """)
                    
                    page.wait_for_load_state('networkidle')
                    self.log("[OK] Navegación completada")
                except Exception as e:
                    browser.close()
                    return {"success": False, "files": 0, "message": f"Error navegando: {str(e)}"}

                # Llenar fechas
                if fecha_inicio:
                    page.fill('input[id="j_idt92_input"]', fecha_inicio)
                if fecha_fin:
                    page.fill('input[id="j_idt97_input"]', fecha_fin)

                # Buscar
                self.log("[SEARCH] Ejecutando búsqueda...")
                page.click('button[name="cmdBuscar"]')
                page.wait_for_load_state('networkidle')
                time.sleep(2)
                
                # Obtener filas
                filas = page.query_selector_all('tbody[id="j_idt120_data"] tr')
                total_filas = len(filas)
                self.log(f"[LIST] Total de registros: {total_filas}")

                if total_filas == 0:
                    browser.close()
                    return {"success": True, "files": 0, "message": "No se encontraron registros"}

                # Detectar selector correcto
                self.log("[SEARCH] Detectando botón de descarga...")
                selector_correcto = None
                posibles_selectores = [
                    'button[id="j_idt120:0:cmd_export"]',
                    'button[id="j_idt120:0:cmdExportar"]',
                    'button[id="j_idt120:0:j_idt126"]',
                    'a[id="j_idt120:0:cmd_export"]',
                ]
                
                for sel in posibles_selectores:
                    if page.query_selector(sel):
                        selector_correcto = sel.replace(':0:', ':{i}:')
                        self.log(f"   [OK] Usando: {selector_correcto}")
                        break
                
                if not selector_correcto:
                    btn = page.query_selector('tbody[id="j_idt120_data"] tr:first-child button')
                    if btn:
                        btn_id = btn.get_attribute('id')
                        if btn_id:
                            selector_correcto = f'button[id="{btn_id}"]'.replace(':0:', ':{i}:')
                            self.log(f"   [OK] Detectado: {selector_correcto}")

                # Descargar archivos
                descargas_exitosas = 0
                
                for i in range(total_filas):
                    try:
                        selector = selector_correcto.format(i=i) if selector_correcto else f'button[id="j_idt120:{i}:cmd_export"]'
                        boton = page.query_selector(selector)
                        
                        if not boton:
                            self.log(f"[!] [{i+1}] Botón no encontrado")
                            continue
                        
                        with page.expect_download(timeout=15000) as download_info:
                            boton.click()
                        
                        download = download_info.value
                        nombre = download.suggested_filename or f"archivo_{i+1}.xlsx"
                        ruta = os.path.join(self.download_dir, nombre)
                        
                        # Evitar duplicados
                        if os.path.exists(ruta):
                            base, ext = os.path.splitext(nombre)
                            ruta = os.path.join(self.download_dir, f"{base}_{i+1}{ext}")
                        
                        download.save_as(ruta)
                        descargas_exitosas += 1
                        
                        if (i + 1) % 10 == 0 or (i + 1) == total_filas:
                            self.log(f"[SAVE] Descargados: {i+1}/{total_filas}")
                        
                    except Exception as e:
                        self.log(f"[ERROR] [{i+1}] Error: {str(e)[:50]}")

                self.log(f"[OK] Completado: {descargas_exitosas}/{total_filas} archivos")
                browser.close()
                
                return {
                    "success": True,
                    "files": descargas_exitosas,
                    "message": f"Descargados {descargas_exitosas} de {total_filas} archivos"
                }
                
        except Exception as e:
            return {"success": False, "files": 0, "message": f"Error: {str(e)}"}
