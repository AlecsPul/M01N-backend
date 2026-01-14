"""
Test script for Comparison endpoint
Usage:
    python tests/test_comparison.py "Company A" "Company B"
    python tests/test_comparison.py --interactive
"""
import asyncio
import httpx
import sys
import json
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

BASE_URL = "http://localhost:8000"
ENDPOINT = "/api/v1/compare"


async def test_compare_applications(company_a: str, company_b: str):
    """Test the comparison endpoint"""
    url = f"{BASE_URL}{ENDPOINT}"
    
    print(f"\n🔍 Testing Comparison Endpoint")
    print(f"Company A: {company_a}")
    print(f"Company B: {company_b}")
    print(f"URL: {url}\n")
    
    payload = {
        "company_a": company_a,
        "company_b": company_b
    }
    
    async with httpx.AsyncClient(timeout=90.0) as client:
        try:
            response = await client.post(url, json=payload)
            
            print(f"Status Code: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                print("\n✅ SUCCESS - Comparison Generated:\n")
                
                # Display Company A
                print(f"{'='*60}")
                print(f"  COMPANY A: {result['company_a']['name']}")
                print(f"{'='*60}")
                print(f"\n  📌 Highlights ({len(result['company_a']['highlights'])}):")
                for i, h in enumerate(result['company_a']['highlights'], 1):
                    print(f"    {i}. {h['title']}")
                    print(f"       {h['detail']}\n")
                
                print(f"  🔗 Attributes ({len(result['company_a']['attributes'])}):")
                attrs_a = result['company_a']['attributes']
                has_count = sum(1 for a in attrs_a if a['has'])
                print(f"    Total: {len(attrs_a)} | Has: {has_count} | Missing: {len(attrs_a) - has_count}")
                
                # Display sample attributes
                sample = attrs_a[:5]
                for attr in sample:
                    status = "✓" if attr['has'] else "✗"
                    print(f"    {status} [{attr['type']}] {attr['value']}")
                if len(attrs_a) > 5:
                    print(f"    ... and {len(attrs_a) - 5} more\n")
                
                # Display Company B
                print(f"\n{'='*60}")
                print(f"  COMPANY B: {result['company_b']['name']}")
                print(f"{'='*60}")
                print(f"\n  📌 Highlights ({len(result['company_b']['highlights'])}):")
                for i, h in enumerate(result['company_b']['highlights'], 1):
                    print(f"    {i}. {h['title']}")
                    print(f"       {h['detail']}\n")
                
                print(f"  🔗 Attributes ({len(result['company_b']['attributes'])}):")
                attrs_b = result['company_b']['attributes']
                has_count = sum(1 for a in attrs_b if a['has'])
                print(f"    Total: {len(attrs_b)} | Has: {has_count} | Missing: {len(attrs_b) - has_count}")
                
                # Display sample attributes
                sample = attrs_b[:5]
                for attr in sample:
                    status = "✓" if attr['has'] else "✗"
                    print(f"    {status} [{attr['type']}] {attr['value']}")
                if len(attrs_b) > 5:
                    print(f"    ... and {len(attrs_b) - 5} more\n")
                
                # Save full JSON
                output_file = project_root / "tests" / "comparison_result.json"
                with open(output_file, "w") as f:
                    json.dump(result, f, indent=2)
                print(f"\n💾 Full JSON saved to: {output_file}\n")
                
            elif response.status_code == 400:
                print(f"\n❌ Bad Request: {response.json()['detail']}\n")
            elif response.status_code == 404:
                print(f"\n❌ Company not found: {response.json()['detail']}\n")
            elif response.status_code == 502:
                print(f"\n❌ Service error: {response.json()['detail']}\n")
            else:
                print(f"\n❌ Unexpected error: {response.text}\n")
                
        except httpx.ConnectError:
            print("\n❌ ERROR: Could not connect to server.")
            print("Make sure the FastAPI server is running:")
            print("  uvicorn app.main:app --reload\n")
        except Exception as e:
            print(f"\n❌ ERROR: {str(e)}\n")


async def interactive_mode():
    """Interactive mode to fetch available applications and test"""
    print("\n📋 Fetching available applications from database...\n")
    
    try:
        from app.core.database import AsyncSessionLocal
        from sqlalchemy import text
        
        async with AsyncSessionLocal() as db:
            # Get application names
            result = await db.execute(
                text("""
                    SELECT DISTINCT name 
                    FROM application 
                    WHERE name IS NOT NULL 
                    ORDER BY name 
                    LIMIT 20
                """)
            )
            companies = [row[0] for row in result.fetchall()]
            
            if not companies:
                print("❌ No companies found in database\n")
                return
            
            print("Available companies:")
            for i, company in enumerate(companies, 1):
                print(f"  {i}. {company}")
            
            print()
            
            # Get user selections
            choice_a = input("Enter first company number: ").strip()
            choice_b = input("Enter second company number: ").strip()
            
            try:
                index_a = int(choice_a) - 1
                index_b = int(choice_b) - 1
                
                if 0 <= index_a < len(companies) and 0 <= index_b < len(companies):
                    if index_a == index_b:
                        print("\n❌ Please select two different companies\n")
                        return
                    
                    company_a = companies[index_a]
                    company_b = companies[index_b]
                    await test_compare_applications(company_a, company_b)
                else:
                    print("❌ Invalid selection\n")
            except ValueError:
                print("❌ Invalid input\n")
                
    except ImportError as e:
        print(f"\n❌ Database import error: {str(e)}")
        print("Make sure you're running from the project root directory\n")
    except Exception as e:
        print(f"\n❌ Database error: {str(e)}\n")


def main():
    if len(sys.argv) == 1:
        print("\n❌ Usage:")
        print("  python tests/test_comparison.py 'Company A' 'Company B'")
        print("  python tests/test_comparison.py --interactive\n")
        sys.exit(1)
    
    if sys.argv[1] == "--interactive":
        asyncio.run(interactive_mode())
    elif len(sys.argv) == 3:
        company_a = sys.argv[1]
        company_b = sys.argv[2]
        asyncio.run(test_compare_applications(company_a, company_b))
    else:
        print("\n❌ Invalid arguments. Use:")
        print("  python tests/test_comparison.py 'Company A' 'Company B'")
        print("  python tests/test_comparison.py --interactive\n")
        sys.exit(1)


if __name__ == "__main__":
    main()
