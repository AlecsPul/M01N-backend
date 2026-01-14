"""
Test script for Provider Suggestions endpoint
Usage:
    python tests/test_provider_suggestions.py <card_id>
    python tests/test_provider_suggestions.py --interactive
"""
import asyncio
import httpx
import sys
from pathlib import Path
from uuid import UUID

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

BASE_URL = "http://localhost:8000"
ENDPOINT = "/api/v1/backlog/{card_id}/suggest-provider"


async def test_suggest_provider(card_id: str):
    """Test the suggest provider endpoint"""
    url = f"{BASE_URL}{ENDPOINT.format(card_id=card_id)}"
    
    print(f"\n🔍 Testing Provider Suggestions Endpoint")
    print(f"Card ID: {card_id}")
    print(f"URL: {url}\n")
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            response = await client.post(url)
            
            print(f"Status Code: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                print("\n✅ SUCCESS - Provider Suggestion Found:\n")
                print(f"  Card ID:         {result['card_id']}")
                print(f"  Company:         {result['company_name']}")
                print(f"  Company URL:     {result['company_url']}")
                print(f"  Marketplace URL: {result['marketplace_url']}")
                print(f"  Reasoning:       {result['reasoning_brief']}")
                print()
            elif response.status_code == 404:
                print(f"\n❌ Card not found: {response.json()['detail']}\n")
            elif response.status_code == 502:
                print(f"\n❌ Error generating suggestion: {response.json()['detail']}\n")
            else:
                print(f"\n❌ Unexpected error: {response.text}\n")
                
        except httpx.ConnectError:
            print("\n❌ ERROR: Could not connect to server.")
            print("Make sure the FastAPI server is running:")
            print("  uvicorn app.main:app --reload\n")
        except Exception as e:
            print(f"\n❌ ERROR: {str(e)}\n")


async def interactive_mode():
    """Interactive mode to fetch available cards and test"""
    print("\n📋 Fetching available backlog cards from database...\n")
    
    # Import database access
    try:
        from app.core.database import AsyncSessionLocal
        from sqlalchemy import select
        from app.models.models import Card
        
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(Card.id, Card.title, Card.description)
                .order_by(Card.created_at.desc())
                .limit(10)
            )
            cards = result.fetchall()
            
            if not cards:
                print("❌ No cards found in database\n")
                return
            
            print("Available cards:")
            for i, (card_id, title, description) in enumerate(cards, 1):
                desc_preview = description[:60] + "..." if len(description) > 60 else description
                print(f"  {i}. [{card_id}]")
                print(f"     Title: {title}")
                print(f"     Description: {desc_preview}\n")
            
            # Get user selection
            choice = input("Enter card number to test (or 'q' to quit): ").strip()
            
            if choice.lower() == 'q':
                return
            
            try:
                index = int(choice) - 1
                if 0 <= index < len(cards):
                    card_id = str(cards[index][0])
                    await test_suggest_provider(card_id)
                else:
                    print("❌ Invalid selection\n")
            except ValueError:
                print("❌ Please enter a valid number\n")
                
    except ImportError as e:
        print(f"❌ Error importing database modules: {e}")
        print("Make sure you're running from the project root with the virtual environment activated\n")
    except Exception as e:
        print(f"❌ Error: {str(e)}\n")


async def main():
    """Main entry point"""
    if len(sys.argv) > 1:
        if sys.argv[1] == "--interactive":
            await interactive_mode()
        else:
            card_id = sys.argv[1]
            # Validate UUID format
            try:
                UUID(card_id)
                await test_suggest_provider(card_id)
            except ValueError:
                print(f"\n❌ Invalid UUID format: {card_id}\n")
                print("Usage:")
                print("  python tests/test_provider_suggestions.py <card_id>")
                print("  python tests/test_provider_suggestions.py --interactive\n")
    else:
        print("\nUsage:")
        print("  python tests/test_provider_suggestions.py <card_id>")
        print("  python tests/test_provider_suggestions.py --interactive\n")


if __name__ == "__main__":
    asyncio.run(main())
