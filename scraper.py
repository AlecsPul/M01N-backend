from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
import time

def scrape_app_names(url):
    """
    Extrae los nombres de apps usando Selenium y XPath
    
    Args:
        url: URL de la página a scrapear
        
    Returns:
        Lista de nombres de apps encontradas
    """
    driver = None
    try:
        print("Configurando Selenium...")
        
        # Configurar opciones de Chrome
        chrome_options = Options()
        chrome_options.add_argument('--headless')  # Ejecutar sin ventana visible
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--window-size=1920,1080')
        chrome_options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
        
        # Iniciar el navegador
        print("Iniciando navegador Chrome...")
        driver = webdriver.Chrome(options=chrome_options)
        
        # Navegar a la URL
        print(f"Navegando a: {url}")
        driver.get(url)
        
        # Esperar a que se cargue el contenido
        print("Esperando a que se cargue el contenido...")
        wait = WebDriverWait(driver, 15)
        
        # Esperar a que aparezcan los elementos con la clase grid_item
        wait.until(EC.presence_of_element_located((By.CLASS_NAME, "grid_item")))
        
        # Esperar un poco más para asegurar que todo el JavaScript se ejecute
        time.sleep(2)
        
        print("Página cargada. Extrayendo nombres de apps...\n")
        
        app_names = []
        
        # Buscar todos los enlaces con aria-label en los grid items
        # XPath para encontrar todos los enlaces con aria-label dentro de grid_item
        xpath = "//div[contains(@class, 'grid_item')]//a[@aria-label]"
        
        links = driver.find_elements(By.XPATH, xpath)
        print(f"Encontrados {len(links)} enlaces\n")
        
        for i, link in enumerate(links, 1):
            try:
                app_name = link.get_attribute('aria-label')
                if app_name:
                    app_names.append(app_name)
                    print(f"  {i}. {app_name}")
            except Exception as e:
                print(f"  Error al extraer nombre del enlace {i}: {e}")
                continue
        
        return app_names
    
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return []
    
    finally:
        # Cerrar el navegador
        if driver:
            print("\nCerrando navegador...")
            driver.quit()


def main():
    # Configurar la URL base (sin filtro de categoría)
    base_url = "https://marketplace.bexio.com/de-CH/listing?page={}&locale=de-CH"
    
    all_apps = []
    page = 1
    max_pages = 50  # Límite de seguridad aumentado
    
    print("="*60)
    print("SCRAPEANDO TODAS LAS APPS DEL MARKETPLACE")
    print("="*60)
    
    while page <= max_pages:
        url = base_url.format(page)
        print(f"\n{'='*60}")
        print(f"PÁGINA {page}")
        print(f"{'='*60}")
        
        # Ejecutar el scraper para esta página
        app_names = scrape_app_names(url)
        
        # Si no se encontraron apps, terminamos
        if not app_names:
            print(f"\nNo se encontraron más apps en la página {page}. Finalizando...")
            break
        
        # Agregar las apps a la lista total
        all_apps.extend(app_names)
        print(f"\n✓ Apps acumuladas hasta ahora: {len(all_apps)}")
        
        page += 1
    
    # Mostrar resultados finales
    print("\n" + "="*60)
    print("RESUMEN FINAL")
    print("="*60)
    print(f"\nTotal de apps encontradas: {len(all_apps)}")
    print(f"Páginas scrapeadas: {page - 1}\n")
    
    print("Lista completa de apps:\n")
    for i, name in enumerate(all_apps, 1):
        print(f"{i}. {name}")
    
    # Guardar en archivo
    with open('apps_encontradas.txt', 'w', encoding='utf-8') as f:
        f.write(f"Total de apps: {len(all_apps)}\n")
        f.write(f"Páginas scrapeadas: {page - 1}\n\n")
        for i, name in enumerate(all_apps, 1):
            f.write(f"{i}. {name}\n")
    
    print(f"\n✓ Resultados guardados en 'apps_encontradas.txt'")


if __name__ == "__main__":
    main()
