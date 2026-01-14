"""
Test script for matching endpoint
"""
import asyncio
import httpx
import json


async def test_matching_endpoint():
    """Test the matching endpoint with various inputs"""
    
    base_url = "http://localhost:8000"
    
    # Test cases
    test_cases = [
        {
            "name": "CRM with Stripe",
            "buyer_prompt": "Necesito un sistema CRM que se integre con Stripe. Sería bueno tener analytics. Mi presupuesto es 100 CHF al mes.",
            "top_k": 30,
            "top_n": 10
        },
        {
            "name": "E-commerce solution",
            "buyer_prompt": "Quiero una tienda online con pasarela de pagos y gestión de inventario",
            "top_k": 30,
            "top_n": 5
        },
        {
            "name": "Accounting software",
            "buyer_prompt": "Busco software de contabilidad con facturación automática para mi PYME",
            "top_k": 30,
            "top_n": 10
        },
        {
            "name": "Marketing tool with automation",
            "buyer_prompt": "Necesito una herramienta de marketing con automatización de email y preferiblemente que se integre con Mailchimp",
            "top_k": 30,
            "top_n": 10
        }
    ]
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        for test_case in test_cases:
            print("=" * 80)
            print(f"TEST: {test_case['name']}")
            print("=" * 80)
            print(f"Input: {test_case['buyer_prompt']}\n")
            
            try:
                response = await client.post(
                    f"{base_url}/api/v1/matching/match",
                    json={
                        "buyer_prompt": test_case["buyer_prompt"],
                        "top_k": test_case["top_k"],
                        "top_n": test_case["top_n"]
                    }
                )
                
                if response.status_code == 200:
                    data = response.json()
                    
                    print("PARSED REQUIREMENTS:")
                    print(f"  Labels (must): {data['buyer_struct']['labels_must']}")
                    print(f"  Labels (nice): {data['buyer_struct']['labels_nice']}")
                    print(f"  Tags (must): {data['buyer_struct'].get('tag_must', [])}")
                    print(f"  Tags (nice): {data['buyer_struct'].get('tag_nice', [])}")
                    print(f"  Integrations (required): {data['buyer_struct']['integration_required']}")
                    print(f"  Integrations (nice): {data['buyer_struct']['integration_nice']}")
                    print(f"  Price max: {data['buyer_struct']['constraints']['price_max']}")
                    print()
                    
                    print(f"TOP {len(data['results'])} MATCHES:")
                    for i, result in enumerate(data['results'], 1):
                        print(f"  {i}. {result['name']}")
                        print(f"     Similarity: {result['similarity_percent']}%")
                        print(f"     App ID: {result['app_id']}")
                    
                    print()
                else:
                    print(f"ERROR: {response.status_code}")
                    print(response.text)
            
            except Exception as e:
                print(f"ERROR: {str(e)}")
            
            print()


if __name__ == "__main__":
    print("Starting matching endpoint tests...")
    print("Make sure the server is running: uvicorn app.main:app --reload")
    print()
    
    asyncio.run(test_matching_endpoint())
