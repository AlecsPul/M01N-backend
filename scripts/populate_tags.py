"""
Database Population Script for Tags

Run this script to populate the apps_tags table with data from tags_encontrados.json
"""
import asyncio
import json
import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select
from app.core.database import AsyncSessionLocal, engine
from app.models.models import Application, AppTag


async def populate_tags():
    """Populate the apps_tags table with categories and industries"""
    
    # Determinar rutas
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    tags_file = os.path.join(base_dir, 'data', 'scraped', 'tags_encontrados.json')
    
    print("=" * 80)
    print("POBLACIÓN DE TABLA apps_tags")
    print("=" * 80)
    print(f"\n📖 Leyendo tags desde: {tags_file}")
    
    # Leer el archivo JSON
    try:
        with open(tags_file, 'r', encoding='utf-8') as f:
            tags_data = json.load(f)
    except FileNotFoundError:
        print(f"❌ Error: No se encontró el archivo {tags_file}")
        print("💡 Ejecuta primero: python scrapers/scraper_tags.py")
        return
    except Exception as e:
        print(f"❌ Error leyendo el archivo: {str(e)}")
        return
    
    print(f"✅ Se encontraron {len(tags_data)} apps con tags\n")
    
    async with AsyncSessionLocal() as session:
        # Verificar si la tabla ya tiene datos
        result = await session.execute(select(AppTag))
        existing_tags = result.scalars().all()
        
        if existing_tags:
            print(f"⚠️  La tabla apps_tags ya contiene {len(existing_tags)} registros")
            response = input("¿Deseas eliminar los datos existentes y reimportar? (y/n): ")
            if response.lower() == 'y':
                for tag in existing_tags:
                    await session.delete(tag)
                await session.commit()
                print("🗑️  Datos existentes eliminados")
            else:
                print("❌ Importación cancelada")
                return
        
        # Obtener todas las aplicaciones para mapear nombres a IDs
        result = await session.execute(select(Application))
        applications = result.scalars().all()
        
        # Crear diccionario de nombre -> id
        app_name_to_id = {app.name: app.id for app in applications}
        
        print(f"📊 Aplicaciones en la base de datos: {len(app_name_to_id)}")
        print("\n💾 Importando tags...")
        
        # Insertar tags
        imported = 0
        skipped = 0
        
        for app_data in tags_data:
            app_name = app_data['app_name']
            
            # Buscar el ID de la aplicación
            app_id = app_name_to_id.get(app_name)
            
            if not app_id:
                print(f"  ⚠️  App no encontrada en BD: {app_name}")
                skipped += 1
                continue
            
            # Insertar categorías
            for category in app_data.get('categories', []):
                if category:  # Solo si no está vacío
                    tag = AppTag(app_id=app_id, tag=category)
                    session.add(tag)
                    imported += 1
            
            # Insertar industrias
            for industry in app_data.get('industries', []):
                if industry:  # Solo si no está vacío
                    tag = AppTag(app_id=app_id, tag=industry)
                    session.add(tag)
                    imported += 1
            
            if imported % 50 == 0 and imported > 0:
                print(f"  Importados {imported} tags...")
        
        await session.commit()
        print(f"✅ Importación completada!")
        
        # Verificar importación
        result = await session.execute(select(AppTag))
        total = len(result.scalars().all())
        
        print("\n" + "=" * 80)
        print("RESUMEN")
        print("=" * 80)
        print(f"Total de tags importados: {imported}")
        print(f"Apps no encontradas: {skipped}")
        print(f"Total de tags en base de datos: {total}")
        print("=" * 80)


async def main():
    """Main function"""
    try:
        await populate_tags()
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
