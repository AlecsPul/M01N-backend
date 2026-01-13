from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
import time
import csv
import json
import os

def scrape_app_tags(url, app_name):
    """
    Extrae todas las categorías e industrias de una app
    
    Args:
        url: URL de la app
        app_name: Nombre de la app
        
    Returns:
        Diccionario con categorías e industrias
    """
    driver = None
    try:
        # Configurar opciones de Chrome
        chrome_options = Options()
        chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--window-size=1920,1080')
        chrome_options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
        
        # Iniciar el navegador
        driver = webdriver.Chrome(options=chrome_options)
        
        print(f"  Navegando a: {url}")
        driver.get(url)
        
        # Esperar a que se cargue el contenido
        wait = WebDriverWait(driver, 10)
        time.sleep(2)
        
        categories = []
        industries = []
        
        # Extraer categorías
        try:
            # XPath base para categorías: /html/body/div[2]/main/div/div/div/component[1]/div/div[2]/nav/ol/li[2]/ul/li[XXX]/a/span
            # Simplificado: buscar todos los li dentro de la estructura de navegación
            category_xpath = "//component[1]//nav//ol/li[2]/ul/li/a/span"
            category_elements = driver.find_elements(By.XPATH, category_xpath)
            
            for element in category_elements:
                category_text = element.text.strip()
                if category_text:
                    categories.append(category_text)
            
            if categories:
                print(f"  ✓ Categorías encontradas: {len(categories)}")
            else:
                print(f"  ⚠️ No se encontraron categorías")
        except Exception as e:
            print(f"  ⚠️ Error extrayendo categorías: {str(e)}")
        
        # Extraer industrias
        try:
            # XPath base para industrias: /html/body/div[2]/main/div/div/div/div/pageorderablecontainer/div/div[3]/div/div[2]/div[3]/aside/div/dl/dd[1]/ul/li[XXX]/a/span
            # Simplificado: buscar todos los li dentro de la estructura de industrias
            industry_xpath = "//pageorderablecontainer//aside//dl/dd[1]/ul/li/a/span"
            industry_elements = driver.find_elements(By.XPATH, industry_xpath)
            
            for element in industry_elements:
                industry_text = element.text.strip()
                if industry_text:
                    industries.append(industry_text)
            
            if industries:
                print(f"  ✓ Industrias encontradas: {len(industries)}")
            else:
                print(f"  ⚠️ No se encontraron industrias")
        except Exception as e:
            print(f"  ⚠️ Error extrayendo industrias: {str(e)}")
        
        return {
            "app_name": app_name,
            "url": url,
            "categories": categories,
            "industries": industries
        }
        
    except Exception as e:
        print(f"  ❌ Error scrapeando {app_name}: {str(e)}")
        return None
    finally:
        if driver:
            driver.quit()


def main():
    """Función principal que lee las apps y scrappea los tags"""
    
    # Determinar la ruta al archivo de apps
    base_dir = os.path.dirname(os.path.abspath(__file__))
    project_dir = os.path.dirname(base_dir)
    data_file = os.path.join(project_dir, 'data', 'scraped', 'apps_encontradas.txt')
    
    print("=" * 80)
    print("SCRAPER DE CATEGORÍAS E INDUSTRIAS DE BEXIO MARKETPLACE")
    print("=" * 80)
    print(f"\n📖 Leyendo apps desde: {data_file}")
    
    # Leer las apps del archivo de texto
    apps = []
    try:
        with open(data_file, 'r', encoding='utf-8') as f:
            content = f.read()
            
        # Dividir por bloques
        blocks = content.split('--------------------------------------------------------------------------------')
        
        for block in blocks:
            if not block.strip():
                continue
            
            # Saltear el header
            if 'Total de apps:' in block or 'Páginas scrapeadas:' in block:
                continue
            
            lines = block.strip().split('\n')
            if len(lines) < 2:
                continue
            
            # Extraer nombre y link
            name = None
            link = None
            
            for line in lines:
                line = line.strip()
                
                # Primera línea con el nombre
                if '. ' in line and not name:
                    parts = line.split('. ', 1)
                    if len(parts) == 2:
                        name = parts[1].strip()
                
                # Link
                if line.startswith('Link:'):
                    link = line.replace('Link:', '').strip()
            
            if name and link:
                apps.append({"name": name, "link": link})
    
    except FileNotFoundError:
        print(f"❌ Error: No se encontró el archivo {data_file}")
        return
    except Exception as e:
        print(f"❌ Error leyendo el archivo: {str(e)}")
        return
    
    print(f"✅ Se encontraron {len(apps)} apps para procesar\n")
    
    # Scrappear tags de cada app
    all_tags = []
    
    for i, app in enumerate(apps, 1):
        print(f"\n[{i}/{len(apps)}] Scrapeando: {app['name']}")
        
        tags_data = scrape_app_tags(app['link'], app['name'])
        
        if tags_data:
            all_tags.append(tags_data)
        
        # Pequeña pausa entre requests
        time.sleep(1)
    
    # Guardar resultados
    output_dir = os.path.join(project_dir, 'data', 'scraped')
    
    # Guardar en JSON
    json_file = os.path.join(output_dir, 'tags_encontrados.json')
    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump(all_tags, f, ensure_ascii=False, indent=2)
    print(f"\n✅ Datos guardados en JSON: {json_file}")
    
    # Guardar en CSV
    csv_file = os.path.join(output_dir, 'tags_encontrados.csv')
    with open(csv_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['App Name', 'URL', 'Categories', 'Industries'])
        
        for tag_data in all_tags:
            writer.writerow([
                tag_data['app_name'],
                tag_data['url'],
                ', '.join(tag_data['categories']) if tag_data['categories'] else '',
                ', '.join(tag_data['industries']) if tag_data['industries'] else ''
            ])
    print(f"✅ Datos guardados en CSV: {csv_file}")
    
    # Guardar en TXT
    txt_file = os.path.join(output_dir, 'tags_encontrados.txt')
    with open(txt_file, 'w', encoding='utf-8') as f:
        f.write(f"Total de apps procesadas: {len(all_tags)}\n")
        f.write("=" * 80 + "\n\n")
        
        for i, tag_data in enumerate(all_tags, 1):
            f.write(f"{i}. {tag_data['app_name']}\n")
            f.write(f"   URL: {tag_data['url']}\n")
            
            if tag_data['categories']:
                f.write(f"   Categorías ({len(tag_data['categories'])}):\n")
                for cat in tag_data['categories']:
                    f.write(f"     - {cat}\n")
            else:
                f.write(f"   Categorías: Ninguna\n")
            
            if tag_data['industries']:
                f.write(f"   Industrias ({len(tag_data['industries'])}):\n")
                for ind in tag_data['industries']:
                    f.write(f"     - {ind}\n")
            else:
                f.write(f"   Industrias: Ninguna\n")
            
            f.write("\n" + "-" * 80 + "\n\n")
    
    print(f"✅ Datos guardados en TXT: {txt_file}")
    
    # Resumen
    total_with_categories = sum(1 for t in all_tags if t['categories'])
    total_with_industries = sum(1 for t in all_tags if t['industries'])
    
    print("\n" + "=" * 80)
    print("RESUMEN")
    print("=" * 80)
    print(f"Total de apps procesadas: {len(all_tags)}")
    print(f"Apps con categorías: {total_with_categories}")
    print(f"Apps con industrias: {total_with_industries}")
    print("=" * 80)


if __name__ == "__main__":
    main()
