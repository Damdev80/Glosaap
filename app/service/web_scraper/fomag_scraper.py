"""
Scraper para portal de Fomag (Horus)
"""
from playwright.sync_api import sync_playwright
import os
import time
from .base_scraper import BaseScraper


class FomagScraper(BaseScraper):
    """Automatización para portal de Fomag (Horus)"""
    
    def __init__(self, download_dir: str = None, progress_callback=None, perfil_dir: str = None):
        super().__init__(download_dir, progress_callback)
        self.url = "https://horus2.horus-health.com/"
        self.perfil_dir = perfil_dir or os.path.join(
            os.path.dirname(__file__), "..", "..", "..", "temp", "perfil_chrome"
        )
        os.makedirs(self.perfil_dir, exist_ok=True)
    
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
                    args=[
                        '--disable-blink-features=AutomationControlled',
                        '--no-sandbox',
                    ]
                )

                page = context.pages[0] if context.pages else context.new_page()
                self.log("[SCRAPER] Iniciando sesión en Fomag...")

                page.goto(self.url, wait_until='domcontentloaded')
                time.sleep(2)
                
                # Verificar si hay formulario de login
                campo_usuario = page.query_selector('input[id="input-15"]')
                
                if campo_usuario:
                    self.log("🔐 Formulario de login detectado, llenando credenciales...")
                    page.fill('input[id="input-15"]', usuario)
                    page.fill('input[id="input-19"]', contraseña)
                    
                    self.log("⚠️ IMPORTANTE: Si aparece CAPTCHA, resuélvelo manualmente en el navegador")
                    self.log("⏳ Esperando que completes el CAPTCHA (si existe)...")
                    
                    page.click('button[type="submit"]')
                    time.sleep(3)
                    
                    # Esperar a que termine el login
                    try:
                        page.wait_for_load_state('networkidle', timeout=60000)
                        self.log("✅ Login completado - Sesión guardada para futuros accesos")
                    except:
                        self.log("⚠️ Timeout esperando respuesta del servidor")
                    
                    time.sleep(2)
                else:
                    self.log("✅ Sesión activa encontrada - No se requiere CAPTCHA")
                
                self.log("🟢 Sesión iniciada correctamente")
                
                # Navegar al menú
                self.log("[SCRAPER] Navegando a Cuentas médicas...")
                page.click('.mdi-bank')
                time.sleep(1)
                
                self.log("[SCRAPER] Navegando a Auditoria...")
                page.click('text=Auditoria')
                page.wait_for_load_state('networkidle')
                time.sleep(2)

                self.log("[SCRAPER] Navegando a tabla de facturas...")
                page.click('text=Facturas objetadas prestador')
                page.wait_for_load_state('networkidle')
                time.sleep(2)
                
                # Clic en PENDIENTES
                self.log("[FILTER] Seleccionando PENDIENTES...")
                page.click('text=PENDIENTES')
                page.wait_for_load_state('networkidle')
                time.sleep(2)

                # Mostrar 100 filas
                page.click('input[id="input-243"]')  
                page.wait_for_load_state('networkidle')
                time.sleep(2)
                page.click('text=100')
                page.wait_for_load_state('networkidle')
                
                # Descargar todos los Excel
                self.log("[SAVE] Iniciando descarga de archivos Excel...")
                
                botones_excel = page.query_selector_all('button.mdi-file-excel')
                total = len(botones_excel)
                self.log(f"[LIST] Total de archivos a descargar: {total}")
                
                descargas_exitosas = 0
                
                for i in range(total):
                    try:
                        # Re-obtener botones (el DOM puede cambiar)
                        botones = page.query_selector_all('button.mdi-file-excel')
                        
                        if i >= len(botones):
                            self.log(f"[!] Botón {i+1} no encontrado")
                            continue
                        
                        boton = botones[i]
                        
                        with page.expect_download(timeout=30000) as download_info:
                            boton.click()
                        
                        download = download_info.value
                        
                        nombre = download.suggested_filename or f"glosa_{i+1}.xlsx"
                        ruta_final = os.path.join(self.download_dir, nombre)
                        
                        # Si existe, agregar número
                        contador = 1
                        nombre_base, extension = os.path.splitext(nombre)
                        while os.path.exists(ruta_final):
                            ruta_final = os.path.join(self.download_dir, f"{nombre_base}_{contador}{extension}")
                            contador += 1
                        
                        download.save_as(ruta_final)
                        descargas_exitosas += 1
                        
                        if (i + 1) % 10 == 0 or (i + 1) == total:
                            self.log(f"[SAVE] Descargados: {i+1}/{total}")
                        
                        time.sleep(1)
                        
                    except Exception as e:
                        self.log(f"[ERROR] Error en descarga {i+1}: {str(e)[:50]}")
                        continue
                
                self.log(f"[OK] Completado: {descargas_exitosas}/{total} archivos")
                time.sleep(3)
                context.close()
                
                return {
                    "success": True,
                    "files": descargas_exitosas,
                    "message": f"Descargados {descargas_exitosas} de {total} archivos"
                }
                
        except Exception as e:
            return {"success": False, "files": 0, "message": f"Error: {str(e)}"}
