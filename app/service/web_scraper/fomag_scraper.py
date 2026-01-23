# -*- coding: utf-8 -*-
"""
Scraper para portal de Fomag (Horus)
"""
from playwright.sync_api import sync_playwright
import os
import sys
import time
import subprocess
from pathlib import Path
from .base_scraper import BaseScraper

# Configurar stdout para UTF-8 en Windows
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except:
        pass


class FomagScraper(BaseScraper):
    """Automatización para portal de Fomag (Horus)"""
    
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
                return  # Todo OK
            
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
            error_msg = str(e).lower()
            
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
    
    def login_and_download(self, usuario: str, contraseña: str) -> dict:
        """
        Login y descarga de archivos de Fomag (OPTIMIZADO)
        
        Args:
            usuario: Usuario
            contraseña: Contraseña
            
        Returns:
            dict con resultado
        """
        try:
            with sync_playwright() as p:
                context = p.chromium.launch_persistent_context(
                    self.perfil_dir,
                    headless=False,
                    accept_downloads=True,
                    viewport={'width': 1920, 'height': 1080},
                    args=[
                        '--disable-blink-features=AutomationControlled',
                        '--no-sandbox',
                        '--start-maximized',
                        '--disable-gpu',
                        '--disable-dev-shm-usage',
                    ]
                )

                page = context.pages[0] if context.pages else context.new_page()
                
                # Optimizar timeouts
                page.set_default_timeout(15000)
                page.set_default_navigation_timeout(30000)
                
                print("\n" + "="*80)
                print(">>> INICIANDO SCRAPER DE FOMAG (HORUS) - MODO TURBO")
                print(f">>> Destino: {self.download_dir}")
                print("="*80 + "\n")
                self.log("[SCRAPER] Iniciando sesion en Fomag...")

                page.goto(self.url, wait_until='domcontentloaded')
                time.sleep(1.5)
                
                # Verificar si hay formulario de login
                campo_usuario = page.query_selector('input[id="input-15"]')
                
                if campo_usuario:
                    self.log("[LOGIN] Formulario de login detectado, llenando credenciales...")
                    page.fill('input[id="input-15"]', usuario)
                    page.fill('input[id="input-19"]', contraseña)
                    
                    self.log("[IMPORTANTE] Si aparece CAPTCHA, resolvelo manualmente")
                    
                    page.click('button[type="submit"]')
                    time.sleep(2)
                    
                    try:
                        page.wait_for_load_state('networkidle', timeout=45000)
                        self.log("[OK] Login completado")
                    except:
                        pass
                    
                    time.sleep(1)
                else:
                    self.log("[OK] Sesion activa - No se requiere CAPTCHA")
                
                # Navegar al menú RAPIDO
                self.log("[NAVEGACION] Navegando a Facturas objetadas...")
                page.click('.mdi-bank')
                time.sleep(0.3)
                
                page.click('text=Auditoria')
                page.wait_for_load_state('networkidle', timeout=10000)
                
                page.click('text=Facturas objetadas prestador')
                page.wait_for_load_state('networkidle', timeout=10000)
                
                # Clic en PENDIENTES
                page.click('text=PENDIENTES')
                page.wait_for_load_state('networkidle', timeout=10000)
                time.sleep(1)

                # Configurar paginación a 100 (máximo) - Solo si hay muchos registros
                self.log("[PAGINACION] Configurando registros por página...")
                paginacion_ok = False
                try:
                    # Buscar el selector de paginación en el footer de la tabla
                    page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
                    time.sleep(0.3)
                    
                    # Buscar dentro del data-footer
                    footer = page.query_selector('div.v-data-footer')
                    if footer:
                        select_paginas = footer.query_selector('div.v-select')
                        if select_paginas:
                            select_paginas.scroll_into_view_if_needed()
                            select_paginas.click(force=True)
                            time.sleep(0.5)
                            
                            # Buscar opción 100 en el menú desplegable
                            opcion_100 = page.query_selector('div.v-list-item:has-text("100")')
                            if opcion_100:
                                opcion_100.click()
                                page.wait_for_load_state('networkidle', timeout=8000)
                                self.log("[OK] Paginacion: 100 registros")
                                paginacion_ok = True
                            else:
                                # Si no hay 100, buscar el máximo disponible
                                page.keyboard.press('Escape')
                except Exception as e:
                    print(f"    [!] Paginacion: {str(e)[:50]}")
                
                if not paginacion_ok:
                    self.log("[INFO] Usando paginacion por defecto")
                
                # Volver arriba
                page.evaluate('window.scrollTo(0, 0)')
                time.sleep(0.3)
                
                # Contar archivos Excel
                iconos_excel = page.query_selector_all('.mdi-file-excel')
                total = len(iconos_excel)
                
                print(f"[INFO] Archivos Excel encontrados en página actual: {total}")
                self.log(f"[INFO] Archivos encontrados: {total}")
                
                if total == 0:
                    self.log("[ADVERTENCIA] No se encontraron archivos para descargar")
                    context.close()
                    return {"success": False, "files": 0, "message": "No se encontraron archivos Excel"}
                
                descargas_exitosas = 0
                descargas_fallidas = 0
                pagina_actual = 1
                
                # SIN LIMITE DE PAGINAS - Descargar TODO
                while True:
                    self.log(f"[PAGINA {pagina_actual}] Procesando...")
                    
                    # Re-obtener iconos después de cada cambio de página
                    time.sleep(0.3)
                    iconos_pagina = page.query_selector_all('.mdi-file-excel')
                    cantidad_pagina = len(iconos_pagina)
                    
                    if cantidad_pagina == 0:
                        self.log("[OK] No hay más archivos")
                        break
                    
                    # Descargar TODOS los archivos de esta página
                    for i in range(cantidad_pagina):
                        try:
                            iconos = page.query_selector_all('.mdi-file-excel')
                            
                            if i >= len(iconos):
                                continue
                            
                            icono_actual = iconos[i]
                            boton = page.evaluate_handle('(icono) => icono.closest("button")', icono_actual).as_element()
                            
                            if not boton:
                                continue
                            
                            boton.scroll_into_view_if_needed()
                            
                            with page.expect_download(timeout=15000) as download_info:
                                boton.click()
                            
                            download = download_info.value
                            nombre = download.suggested_filename or f"fomag_p{pagina_actual}_{i+1}.xlsx"
                            ruta_final = os.path.join(self.download_dir, nombre)
                            
                            # Evitar duplicados
                            contador = 1
                            nombre_base, extension = os.path.splitext(nombre)
                            while os.path.exists(ruta_final):
                                ruta_final = os.path.join(self.download_dir, f"{nombre_base}_{contador}{extension}")
                                contador += 1
                            
                            download.save_as(ruta_final)
                            descargas_exitosas += 1
                            
                            # Reportar progreso cada 10 archivos
                            if descargas_exitosas % 10 == 0:
                                self.log(f"[PROGRESO] {descargas_exitosas} archivos descargados...")
                            
                            time.sleep(0.15)
                            
                        except Exception as e:
                            descargas_fallidas += 1
                            continue
                    
                    self.log(f"[PAGINA {pagina_actual}] {descargas_exitosas} descargados hasta ahora")
                    
                    # Ir a la siguiente página
                    try:
                        time.sleep(0.3)
                        
                        # Buscar botón siguiente
                        btn_siguiente = page.query_selector('button.v-pagination__navigation:has(i.mdi-chevron-right)')
                        
                        if not btn_siguiente:
                            btns_nav = page.query_selector_all('button.v-pagination__navigation')
                            if len(btns_nav) >= 2:
                                btn_siguiente = btns_nav[-1]
                        
                        if btn_siguiente:
                            disabled_attr = btn_siguiente.get_attribute('disabled')
                            clase = btn_siguiente.get_attribute('class') or ''
                            
                            es_disabled = disabled_attr is not None or 'disabled' in clase.lower()
                            
                            if es_disabled:
                                self.log("[OK] Última página alcanzada")
                                break
                            
                            # Click en siguiente
                            btn_siguiente.scroll_into_view_if_needed()
                            time.sleep(0.2)
                            btn_siguiente.click()
                            
                            # Esperar carga de nueva página
                            try:
                                page.wait_for_load_state('networkidle', timeout=10000)
                            except:
                                pass
                            
                            time.sleep(0.5)
                            pagina_actual += 1
                            self.log(f"[>>] Avanzando a página {pagina_actual}")
                        else:
                            self.log("[OK] No hay más páginas")
                            break
                            break
                            
                    except Exception as nav_error:
                        print(f"    [ERROR] Navegación: {str(nav_error)[:80]}")
                        self.log(f"[ERROR NAV] {str(nav_error)[:60]}")
                        # No hacer break inmediato, intentar una vez más
                        time.sleep(1)
                        continue
                
                # Resumen final
                print("\n" + "="*80)
                print(f">>> DESCARGA COMPLETADA")
                print(f">>> Exitosas: {descargas_exitosas} | Fallidas: {descargas_fallidas}")
                print(f">>> Ubicacion: {self.download_dir}")
                print("="*80 + "\n")
                
                self.log(f"[COMPLETADO] {descargas_exitosas} archivos descargados en: {self.download_dir}")
                time.sleep(2)
                context.close()
                
                return {
                    "success": True,
                    "files": descargas_exitosas,
                    "message": f"Descargados {descargas_exitosas} archivos en {self.download_dir}"
                }
                
        except Exception as e:
            print(f"\n[ERROR GENERAL] {str(e)}\n")
            return {"success": False, "files": 0, "message": f"Error: {str(e)}"}
