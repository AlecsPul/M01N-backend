"""
Database Population Script

Run this script to populate the applications table with data from apps_encontradas.txt
"""
import asyncio
import re
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select
from app.core.database import AsyncSessionLocal, engine
from app.models.models import Application


def parse_apps_file(file_path: str) -> list[dict]:
    """Parse apps_encontradas.txt and extract app data"""
    apps = []
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Split by the separator line
    app_blocks = content.split('--------------------------------------------------------------------------------')
    
    for block in app_blocks:
        if not block.strip():
            continue
            
        # Skip header
        if 'Total de apps:' in block or 'Páginas scrapeadas:' in block:
            continue
        
        lines = block.strip().split('\n')
        if len(lines) < 2:
            continue
        
        app_data = {}
        
        # Extract name (first line, format: "1. TRESIO")
        first_line = lines[0].strip()
        name_match = re.match(r'^\d+\.\s+(.+)$', first_line)
        if name_match:
            app_data['name'] = name_match.group(1).strip()
        else:
            continue
        
        # Extract other fields
        for line in lines[1:]:
            line = line.strip()
            if line.startswith('Link:'):
                app_data['link'] = line.replace('Link:', '').strip()
            elif line.startswith('Imagen:'):
                app_data['image'] = line.replace('Imagen:', '').strip()
            elif line.startswith('Precio:'):
                app_data['price'] = line.replace('Precio:', '').strip()
            elif line.startswith('Descripción:'):
                app_data['short_description'] = line.replace('Descripción:', '').strip()
        
        # Only add if we have the required fields
        if 'name' in app_data and 'link' in app_data:
            apps.append(app_data)
    
    return apps


async def populate_applications():
    """Populate the applications table with scraped data"""
    print("📖 Reading apps_encontradas.txt...")
    apps = parse_apps_file('Scrapper/apps_encontradas.txt')
    print(f"✅ Found {len(apps)} apps to import")
    
    async with AsyncSessionLocal() as session:
        # Check if table already has data
        result = await session.execute(select(Application))
        existing_apps = result.scalars().all()
        
        if existing_apps:
            print(f"⚠️  Table already contains {len(existing_apps)} applications")
            response = input("Do you want to delete existing data and reimport? (y/n): ")
            if response.lower() == 'y':
                for app in existing_apps:
                    await session.delete(app)
                await session.commit()
                print("🗑️  Existing data deleted")
            else:
                print("❌ Import cancelled")
                return
        
        # Insert new applications
        print("💾 Importing applications...")
        imported = 0
        for app_data in apps:
            app = Application(
                name=app_data.get('name'),
                short_description=app_data.get('short_description'),
                link=app_data.get('link'),
                image=app_data.get('image'),
                price=app_data.get('price')
            )
            session.add(app)
            imported += 1
            
            if imported % 10 == 0:
                print(f"  Imported {imported}/{len(apps)} apps...")
        
        await session.commit()
        print(f"✅ Successfully imported {imported} applications!")
        
        # Verify import
        result = await session.execute(select(Application))
        total = len(result.scalars().all())
        print(f"📊 Total applications in database: {total}")


async def main():
    """Main function"""
    try:
        await populate_applications()
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
