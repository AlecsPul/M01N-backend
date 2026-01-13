from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
import time
import csv
import json

def scrape_app_features(url, app_name):
    """
    Extrae todas las features de una app
    
    Args:
        url: URL de la app
        app_name: Nombre de la app
        
    Returns:
        Diccionario con información de features
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
        
        # Construir URL de features
        features_url = url.rstrip('/') + '/features'
        
        print(f"  Navegando a: {features_url}")
        driver.get(features_url)
        
        # Esperar a que se cargue el contenido
        wait = WebDriverWait(driver, 10)
        
        try:
            # Esperar a que aparezca el componente de features
            wait.until(EC.presence_of_element_located((By.TAG_NAME, "component")))
            time.sleep(1)
        except:
            print(f"  ⚠️ No se encontró contenido de features")
            return None
        
        # Buscar todos los divs dentro de component[1]/section
        # XPath base: /html/body/div[2]/main/div/div/div/div/component[1]/section/div[XXX]
        base_xpath = "//component[1]/section/div"
        
        try:
            feature_divs = driver.find_elements(By.XPATH, base_xpath)
            
            if not feature_divs:
                print(f"  ⚠️ No se encontraron divs de features")
                return None
            
            print(f"  ✓ Encontrados {len(feature_divs)} secciones de features")
            
            all_features_text = []
            
            # Extraer todo el texto de cada div
            for i, div in enumerate(feature_divs, 1):
                try:
                    # Obtener todo el texto del div y sus subdivisiones
                    text = div.text.strip()
                    if text:
                        all_features_text.append(text)
                        print(f"    - Sección {i}: {len(text)} caracteres")
                except Exception as e:
                    print(f"    ⚠️ Error en sección {i}: {e}")
                    continue
            
            if not all_features_text:
                print(f"  ⚠️ No se extrajo texto de las features")
                return None
            
            # Combinar todo el texto
            combined_text = "\n\n".join(all_features_text)
            
            return {
                'nombre': app_name,
                'url': url,
                'features_url': features_url,
                'num_secciones': len(all_features_text),
                'features_text': combined_text
            }
            
        except Exception as e:
            print(f"  ❌ Error al extraer features: {e}")
            return None
    
    except Exception as e:
        print(f"  ❌ Error general: {e}")
        return None
    
    finally:
        if driver:
            driver.quit()


def main():
    print("="*60)
    print("SCRAPER DE FEATURES DE APPS")
    print("="*60)
    
    # Leer el CSV del primer scraper
    apps = []
    try:
        with open('apps_encontradas.csv', 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            apps = list(reader)
        print(f"\n✓ Cargadas {len(apps)} apps del archivo CSV\n")
    except FileNotFoundError:
        print("❌ Error: No se encontró 'apps_encontradas.csv'")
        print("   Ejecuta primero el scraper principal (scraper.py)")
        return
    
    all_features = []
    total = len(apps)
    
    print("="*60)
    print(f"INICIANDO SCRAPING DE FEATURES ({total} apps)")
    print("="*60 + "\n")
    
    for i, app in enumerate(apps, 1):
        app_name = app['nombre']
        app_link = app['link']
        
        print(f"[{i}/{total}] {app_name}")
        
        features = scrape_app_features(app_link, app_name)
        
        if features:
            all_features.append(features)
            print(f"  ✓ Features extraídas exitosamente")
        else:
            print(f"  ⚠️ No se pudieron extraer features")
        
        print()
        
        # Pequeña pausa entre requests
        time.sleep(1)
    
    # Guardar resultados
    print("\n" + "="*60)
    print("GUARDANDO RESULTADOS")
    print("="*60)
    
    # Guardar en archivo de texto
    with open('features_encontradas.txt', 'w', encoding='utf-8') as f:
        f.write(f"Total de apps con features: {len(all_features)}\n")
        f.write(f"Total de apps procesadas: {total}\n\n")
        f.write("="*80 + "\n\n")
        
        for i, feature_data in enumerate(all_features, 1):
            f.write(f"{i}. {feature_data['nombre']}\n")
            f.write(f"   URL: {feature_data['features_url']}\n")
            f.write(f"   Secciones encontradas: {feature_data['num_secciones']}\n")
            f.write(f"\n   FEATURES:\n")
            f.write("   " + "-"*76 + "\n")
            # Indentar el texto de features
            features_text = feature_data['features_text'].replace('\n', '\n   ')
            f.write(f"   {features_text}\n")
            f.write("\n" + "="*80 + "\n\n")
    
    # Guardar en JSON para fácil procesamiento
    with open('features_encontradas.json', 'w', encoding='utf-8') as f:
        json.dump(all_features, f, ensure_ascii=False, indent=2)
    
    # Guardar en CSV
    if all_features:
        with open('features_encontradas.csv', 'w', encoding='utf-8', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=['nombre', 'url', 'features_url', 'num_secciones', 'features_text'])
            writer.writeheader()
            writer.writerows(all_features)
    
    print(f"\n✓ Resultados guardados en:")
    print(f"  - features_encontradas.txt (formato legible)")
    print(f"  - features_encontradas.json (formato estructurado)")
    print(f"  - features_encontradas.csv (formato tabla)")
    print(f"\n✓ Apps con features extraídas: {len(all_features)}/{total}")


if __name__ == "__main__":
    main()
