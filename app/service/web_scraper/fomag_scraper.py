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
            # Intentar obtener la ruta del navegador
            with sync_playwright() as p:
                browser_type = p.chromium
                # Esto forza la verificación del navegador
                executable_path = browser_type.executable_path
                
                if not os.path.exists(executable_path):
                    raise FileNotFoundError("Navegador no encontrado")
                    
                print(f"[OK] Navegador Chromium encontrado: {executable_path}")
                
        except Exception as e:
            print("")
            print("="*70)
            print("[INSTALACION REQUERIDA] Navegadores de Playwright no encontrados")
            print("="*70)
            print("")
            print("  Es necesario descargar el navegador Chromium para el scraper.")
            print("  Esto solo ocurre la primera vez que usas esta funcion.")
            print("")
            print("  Descarga: ~150 MB")
            print("  Tiempo estimado: 3-5 minutos")
            print("")
            
            try:
                # Usar el CLI de Playwright directamente con Python
                import playwright
                from playwright._impl._driver import compute_driver_executable, get_driver_env
                
                print("  [1/2] Localizando driver de Playwright...")
                
                # Obtener ruta del driver
                driver_executable = compute_driver_executable()
                env = get_driver_env()
                
                # Preparar entorno con ruta de navegadores
                full_env = os.environ.copy()
                full_env.update(env)
                
                if 'PLAYWRIGHT_BROWSERS_PATH' in full_env:
                    print(f"  Directorio destino: {full_env['PLAYWRIGHT_BROWSERS_PATH']}")
                
                print("  [2/2] Descargando e instalando Chromium...")
                print("")
                
                # Ejecutar instalacion
                process = subprocess.Popen(
                    [str(driver_executable), "install", "chromium"],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    env=full_env,
                    bufsize=1,
                    universal_newlines=True
                )
                
                # Mostrar progreso
                for line in process.stdout:
                    line = line.strip()
                    if line:
                        print(f"  {line}")
                
                process.wait()
                
                if process.returncode == 0:
                    print("")
                    print("="*70)
                    print("[OK] Navegadores instalados correctamente")
                    print("="*70)
                    print("")
                    return
                else:
                    raise Exception(f"Codigo de salida: {process.returncode}")
                    
            except Exception as install_error:
                # Si falla la instalacion automatica, mostrar instrucciones
                print("")
                print("="*70)
                print("[ERROR] instalacion de navegadores fallida. Ver instrucciones arriba????")
                print("="*70)
                print("")
                print("ERROR TECNICO:")
                print(f"  {type(install_error).__name__}: {install_error}")
                print("")
                print("SOLUCION: Instalacion manual requerida")
                print("")
                print("  Ejecuta estos comandos en PowerShell:")
                print("")
                print(f"    $env:PLAYWRIGHT_BROWSERS_PATH=\"{os.getenv('APPDATA')}\\Glosaap\\browsers\"")
                print("    pip install playwright")
                print("    playwright install chromium")
                print("")
                print("  O contacta al administrador del sistema.")
                print("")
                
                raise Exception("No se pudo instalar automaticamente. Usa instalacion manual.")
    
    def login_and_download(self, usuario: str, contraseña: str) -> dict:
        """
        Login y descarga de archivos de Fomag
        
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
                    ]
                )

                page = context.pages[0] if context.pages else context.new_page()
                print("\n" + "="*80)
                print(">>> INICIANDO SCRAPER DE FOMAG")
                print("="*80 + "\n")
                self.log("[SCRAPER] Iniciando sesion en Fomag...")

                page.goto(self.url, wait_until='domcontentloaded')
                time.sleep(2)
                
                # Verificar si hay formulario de login
                campo_usuario = page.query_selector('input[id="input-15"]')
                
                if campo_usuario:
                    self.log("[LOGIN] Formulario de login detectado, llenando credenciales...")
                    page.fill('input[id="input-15"]', usuario)
                    page.fill('input[id="input-19"]', contraseña)
                    
                    self.log("[IMPORTANTE] Si aparece CAPTCHA, resolvelo manualmente en el navegador")
                    self.log("[ESPERANDO] Esperando que completes el CAPTCHA (si existe)...")
                    
                    page.click('button[type="submit"]')
                    time.sleep(3)
                    
                    # Esperar a que termine el login
                    try:
                        page.wait_for_load_state('networkidle', timeout=60000)
                        self.log("[OK] Login completado - Sesion guardada para futuros accesos")
                    except:
                        self.log("[ADVERTENCIA] Timeout esperando respuesta del servidor")
                    
                    time.sleep(2)
                else:
                    self.log("[OK] Sesion activa encontrada - No se requiere CAPTCHA")
                
                self.log("[OK] Sesion iniciada correctamente")
                print("[OK] Sesion iniciada correctamente\n")
                
                # Navegar al menú
                print("[NAVEGACION] Navegando por menus...")
                self.log("[NAVEGACION] Navegando a Cuentas medicas...")
                page.click('.mdi-bank')
                time.sleep(0.5)
                
                self.log("[NAVEGACION] Navegando a Auditoria...")
                page.click('text=Auditoria')
                page.wait_for_load_state('networkidle')
                
                self.log("[NAVEGACION] Navegando a tabla de facturas...")
                page.click('text=Facturas objetadas prestador')
                page.wait_for_load_state('networkidle')
                
                # Clic en PENDIENTES
                self.log("[FILTRO] Seleccionando filtro PENDIENTES...")
                page.click('text=PENDIENTES')
                page.wait_for_load_state('networkidle')
                print("   [OK] Navegacion completada\n")

                # Configurar paginación (opcional, puede fallar por visibilidad)
                print("[PAGINACION] Intentando configurar paginacion...")
                self.log("[PAGINACION] Configurando paginacion a 100 registros...")
                try:
                    selections = page.query_selector_all('div.v-select__selection--comma')
                    for sel in selections:
                        texto = sel.inner_text()
                        if texto and texto.strip().isdigit() and int(texto.strip()) <= 50:
                            contenedor = page.evaluate_handle('(div) => div.closest("div.v-input__slot")', sel).as_element()
                            if contenedor:
                                contenedor.click(timeout=3000, force=True)
                                time.sleep(1)
                                page.click('text=100', timeout=2000)
                                page.wait_for_load_state('networkidle', timeout=10000)
                                time.sleep(2)
                                print("   [OK] Paginacion configurada\n")
                                break
                except:
                    print("   [ADVERTENCIA] Paginacion no disponible, usando actual\n")
                    pass
                
                # Buscar archivos Excel
                print("[DESCARGA] Iniciando descarga...")
                self.log("[DESCARGA] Iniciando descarga de archivos Excel...")
                
                # Buscar iconos Excel (usar .mdi-file-excel que funciona)
                iconos_excel = page.query_selector_all('.mdi-file-excel')
                
                if len(iconos_excel) == 0:
                    iconos_excel = page.query_selector_all('i.mdi-file-excel')
                
                total = len(iconos_excel)
                print(f"   [INFO] Archivos encontrados: {total}\n")
                self.log(f"[BUSQUEDA] Archivos encontrados: {total}")
                self.log(f"[INFO] Total de archivos encontrados: {total}")
                
                if total == 0:
                    self.log("[ADVERTENCIA] No se encontraron archivos para descargar")
                    context.close()
                    return {
                        "success": False,
                        "files": 0,
                        "message": "No se encontraron archivos Excel en la tabla"
                    }
                
                descargas_exitosas = 0
                pagina_actual = 1
                max_paginas = 50  # Límite de seguridad
                
                # Loop de paginación
                while pagina_actual <= max_paginas:
                    print(f"\n{'='*80}")
                    print(f">>> PAGINA {pagina_actual}")
                    print(f"{'='*80}\n")
                    
                    # Buscar iconos en la página actual usando el selector que funcionó
                    iconos_pagina = page.query_selector_all('.mdi-file-excel')
                    print(f"   [INFO] Archivos en esta pagina: {len(iconos_pagina)}")
                    
                    if len(iconos_pagina) == 0:
                        print("   [ADVERTENCIA] No hay mas archivos, terminando...\n")
                        break
                    
                    # Descargar todos los archivos de esta página
                    for i in range(len(iconos_pagina)):
                        try:
                            # Re-obtener iconos (el DOM puede cambiar)
                            iconos = page.query_selector_all('.mdi-file-excel')
                            
                            if i >= len(iconos):
                                continue
                            
                            # Obtener el botón padre del icono actual
                            icono_actual = iconos[i]
                            boton = page.evaluate_handle('(icono) => icono.closest("button")', icono_actual).as_element()
                            
                            if not boton:
                                continue
                            
                            # Hacer scroll y click
                            boton.scroll_into_view_if_needed()
                            time.sleep(0.3)
                            
                            with page.expect_download(timeout=20000) as download_info:
                                boton.click()
                            
                            download = download_info.value
                            nombre = download.suggested_filename or f"fomag_p{pagina_actual}_{i+1}.xlsx"
                            ruta_final = os.path.join(self.download_dir, nombre)
                            
                            # Si existe, agregar número
                            contador = 1
                            nombre_base, extension = os.path.splitext(nombre)
                            while os.path.exists(ruta_final):
                                ruta_final = os.path.join(self.download_dir, f"{nombre_base}_{contador}{extension}")
                                contador += 1
                            
                            download.save_as(ruta_final)
                            descargas_exitosas += 1
                            
                            if descargas_exitosas % 10 == 0:
                                print(f"   [OK] Descargados: {descargas_exitosas}")
                            
                            time.sleep(0.8)
                            
                        except Exception as e:
                            self.log(f"[ERROR] Error: {str(e)[:80]}")
                            continue
                    
                    # Ir a la siguiente página
                    try:
                        btn_siguiente = page.query_selector('button.v-pagination__navigation:has(i.mdi-chevron-right)')
                        
                        if not btn_siguiente:
                            btn_siguiente = page.query_selector('button[aria-label="Next page"]')
                        
                        if btn_siguiente and not btn_siguiente.get_attribute('disabled'):
                            btn_siguiente.click()
                            page.wait_for_load_state('networkidle', timeout=8000)
                            time.sleep(1.5)
                            pagina_actual += 1
                            print(f"   [>>] Pagina {pagina_actual}")
                        else:
                            print(f"\n   [OK] Ultima pagina procesada\n")
                            break
                            
                    except:
                        break
                
                print("\n" + "="*80)
                print(f">>> PROCESO COMPLETADO: {descargas_exitosas}/{total} archivos descargados")
                print(f"[UBICACION] {self.download_dir}")
                print("="*80 + "\n")
                
                self.log(f"[COMPLETADO] Proceso completado: {descargas_exitosas}/{total} archivos descargados")
                time.sleep(3)
                context.close()
                
                return {
                    "success": True,
                    "files": descargas_exitosas,
                    "message": f"Descargados {descargas_exitosas} de {total} archivos en {self.download_dir}"
                }
                
        except Exception as e:
            print(f"\n[ERROR GENERAL] {str(e)}\n")
            return {"success": False, "files": 0, "message": f"Error: {str(e)}"}
