from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
import time
import csv
import json
import re


def scrape_app_ratings(url):
    """
    Extrae los ratings de todas las apps del marketplace
    
    Args:
        url: URL de la página del marketplace
        
    Returns:
        Lista de diccionarios con información de apps y sus ratings
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
        
        # Esperar a que aparezcan los elementos
        wait.until(EC.presence_of_element_located((By.CLASS_NAME, "grid_item")))
        
        # Esperar un poco más para asegurar que todo el JavaScript se ejecute
        time.sleep(2)
        
        print("Página cargada. Extrayendo ratings...\n")
        
        app_ratings = []
        
        # Buscar todos los divs usando el XPath absoluto
        # XPath base: /html/body/div[2]/main/div/div/div/div/div/div[2]/component/div/div[1]/div[XXX]
        grid_divs = driver.find_elements(By.XPATH, "/html/body/div[2]/main/div/div/div/div/div/div[2]/component/div/div[1]/div")
        print(f"Encontrados {len(grid_divs)} divs contenedores\n")
        
        for i, grid_div in enumerate(grid_divs, 1):
            try:
                # Extraer nombre de la app
                try:
                    name_element = grid_div.find_element(By.XPATH, ".//a[@aria-label]")
                    app_name = name_element.get_attribute('aria-label')
                    app_link = name_element.get_attribute('href')
                except:
                    app_name = f"App {i}"
                    app_link = "No disponible"
                
                # Extraer rating usando el XPath absoluto completo
                # XPath completo: /html/body/div[2]/main/div/div/div/div/div/div[2]/component/div/div[1]/div[XXX]/article/div/div[2]/div[2]/div/div
                # XPath relativo desde grid_div: ./article/div/div[2]/div[2]/div/div
                try:
                    rating_element = grid_div.find_element(By.XPATH, "./article/div/div[2]/div[2]/div/div")
                    style_attribute = rating_element.get_attribute('style')
                    
                    # Extraer el número del rating del style
                    # Formato: --rating-fullstars: 2;
                    rating = None
                    if style_attribute:
                        match = re.search(r'--rating-fullstars:\s*(\d+(?:\.\d+)?)', style_attribute)
                        if match:
                            rating = float(match.group(1))
                    
                    if rating is None:
                        rating = "No disponible"
                    
                except Exception as e:
                    rating = "No disponible"
                    print(f"  ⚠️ No se pudo extraer rating para {app_name}: {e}")
                
                # Guardar información
                app_info = {
                    'nombre': app_name,
                    'link': app_link,
                    'rating': rating
                }
                app_ratings.append(app_info)
                
                print(f"  {i}. {app_name}")
                print(f"     Rating: {rating}")
                print(f"     Link: {app_link}")
                print()
                
            except Exception as e:
                print(f"  Error al extraer datos del artículo {i}: {e}")
                continue
        
        return app_ratings
    
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
    # Configurar la URL base
    base_url = "https://marketplace.bexio.com/en-GB/listing?order=RATING&page={}&locale=en-GB"
    
    all_ratings = []
    page = 1
    max_pages = 50  # Límite de seguridad
    
    print("="*60)
    print("SCRAPEANDO RATINGS DE APPS DEL MARKETPLACE")
    print("="*60)
    
    while page <= max_pages:
        url = base_url.format(page)
        print(f"\n{'='*60}")
        print(f"PÁGINA {page}")
        print(f"{'='*60}")
        
        # Ejecutar el scraper para esta página
        ratings_data = scrape_app_ratings(url)
        
        # Si no se encontraron apps, terminamos
        if not ratings_data:
            print(f"\nNo se encontraron más apps en la página {page}. Finalizando...")
            break
        
        # Agregar las apps a la lista total
        all_ratings.extend(ratings_data)
        print(f"\n✓ Apps con ratings acumuladas hasta ahora: {len(all_ratings)}")
        
        page += 1
    
    # Mostrar resultados finales
    print("\n" + "="*60)
    print("RESUMEN FINAL")
    print("="*60)
    print(f"\nTotal de apps con ratings: {len(all_ratings)}")
    print(f"Páginas scrapeadas: {page - 1}")
    
    # Calcular estadísticas de ratings
    ratings_with_value = [app['rating'] for app in all_ratings if isinstance(app['rating'], (int, float))]
    if ratings_with_value:
        avg_rating = sum(ratings_with_value) / len(ratings_with_value)
        print(f"Rating promedio: {avg_rating:.2f}")
        print(f"Apps con rating: {len(ratings_with_value)}")
        print(f"Apps sin rating: {len(all_ratings) - len(ratings_with_value)}")
    
    print()
    
    # Guardar en archivo de texto
    output_dir = 'data/scraped/'
    import os
    os.makedirs(output_dir, exist_ok=True)
    
    with open(f'{output_dir}ratings_encontrados.txt', 'w', encoding='utf-8') as f:
        f.write(f"Total de apps: {len(all_ratings)}\n")
        f.write(f"Páginas scrapeadas: {page - 1}\n")
        if ratings_with_value:
            f.write(f"Rating promedio: {avg_rating:.2f}\n")
            f.write(f"Apps con rating: {len(ratings_with_value)}\n")
            f.write(f"Apps sin rating: {len(all_ratings) - len(ratings_with_value)}\n")
        f.write("\n" + "="*80 + "\n\n")
        
        for i, app in enumerate(all_ratings, 1):
            f.write(f"{i}. {app['nombre']}\n")
            f.write(f"   Rating: {app['rating']}\n")
            f.write(f"   Link: {app['link']}\n")
            f.write("\n" + "-"*80 + "\n\n")
    
    # Guardar en archivo CSV
    with open(f'{output_dir}ratings_encontrados.csv', 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=['nombre', 'rating', 'link'])
        writer.writeheader()
        writer.writerows(all_ratings)
    
    # Guardar en archivo JSON
    with open(f'{output_dir}ratings_encontrados.json', 'w', encoding='utf-8') as f:
        json.dump(all_ratings, f, ensure_ascii=False, indent=2)
    
    print(f"✓ Resultados guardados en '{output_dir}ratings_encontrados.txt'")
    print(f"✓ Resultados guardados en '{output_dir}ratings_encontrados.csv'")
    print(f"✓ Resultados guardados en '{output_dir}ratings_encontrados.json'")


if __name__ == "__main__":
    main()
