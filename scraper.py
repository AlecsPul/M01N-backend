from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
import time

def scrape_app_names(url):
    """
    Extrae información completa de apps usando Selenium y XPath
    
    Args:
        url: URL de la página a scrapear
        
    Returns:
        Lista de diccionarios con información de apps encontradas
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
        
        print("Página cargada. Extrayendo información de apps...\n")
        
        app_data = []
        
        # Buscar todos los grid items
        grid_items = driver.find_elements(By.XPATH, "//div[contains(@class, 'grid_item')]")
        print(f"Encontrados {len(grid_items)} items\n")
        
        for i, item in enumerate(grid_items, 1):
            try:
                # Extraer nombre y link
                link_element = item.find_element(By.XPATH, ".//a[@aria-label]")
                app_name = link_element.get_attribute('aria-label')
                app_link = link_element.get_attribute('href')
                
                # Extraer imagen
                try:
                    img_element = item.find_element(By.XPATH, ".//img[contains(@class, 'productListingCard_icon')]")
                    app_image = img_element.get_attribute('src')
                except:
                    app_image = "No disponible"
                
                # Extraer descripción
                try:
                    desc_element = item.find_element(By.XPATH, ".//div[contains(@class, 'productListingCard_overview')]")
                    app_description = desc_element.text.strip()
                except:
                    app_description = "No disponible"
                
                # Extraer precio
                try:
                    price_element = item.find_element(By.XPATH, ".//div[@data-testid='pricing:srPrice']")
                    app_price = price_element.text.strip()
                except:
                    app_price = "No disponible"
                
                if app_name and app_link:
                    app_info = {
                        'nombre': app_name,
                        'link': app_link,
                        'imagen': app_image,
                        'descripcion': app_description,
                        'precio': app_price
                    }
                    app_data.append(app_info)
                    
                    print(f"  {i}. {app_name}")
                    print(f"     Link: {app_link}")
                    print(f"     Imagen: {app_image[:60]}..." if len(app_image) > 60 else f"     Imagen: {app_image}")
                    print(f"     Precio: {app_price}")
                    print(f"     Descripción: {app_description[:60]}..." if len(app_description) > 60 else f"     Descripción: {app_description}")
                    print()
                    
            except Exception as e:
                print(f"  Error al extraer datos del item {i}: {e}")
                continue
        
        return app_data
    
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
    base_url = "https://marketplace.bexio.com/en-GB/listing?page={}&locale=en-GB"
    
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
        app_data = scrape_app_names(url)
        
        # Si no se encontraron apps, terminamos
        if not app_data:
            print(f"\nNo se encontraron más apps en la página {page}. Finalizando...")
            break
        
        # Agregar las apps a la lista total
        all_apps.extend(app_data)
        print(f"\n✓ Apps acumuladas hasta ahora: {len(all_apps)}")
        
        page += 1
    
    # Mostrar resultados finales
    print("\n" + "="*60)
    print("RESUMEN FINAL")
    print("="*60)
    print(f"\nTotal de apps encontradas: {len(all_apps)}")
    print(f"Páginas scrapeadas: {page - 1}\n")
    
    # Guardar en archivo de texto
    with open('apps_encontradas.txt', 'w', encoding='utf-8') as f:
        f.write(f"Total de apps: {len(all_apps)}\n")
        f.write(f"Páginas scrapeadas: {page - 1}\n\n")
        f.write("="*80 + "\n\n")
        
        for i, app in enumerate(all_apps, 1):
            f.write(f"{i}. {app['nombre']}\n")
            f.write(f"   Link: {app['link']}\n")
            f.write(f"   Imagen: {app['imagen']}\n")
            f.write(f"   Precio: {app['precio']}\n")
            f.write(f"   Descripción: {app['descripcion']}\n")
            f.write("\n" + "-"*80 + "\n\n")
    
    # Guardar en archivo CSV
    import csv
    with open('apps_encontradas.csv', 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=['nombre', 'link', 'imagen', 'precio', 'descripcion'])
        writer.writeheader()
        writer.writerows(all_apps)
    
    print(f"✓ Resultados guardados en 'apps_encontradas.txt'")
    print(f"✓ Resultados guardados en 'apps_encontradas.csv'")


if __name__ == "__main__":
    main()
