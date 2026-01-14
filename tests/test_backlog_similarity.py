"""
Test script for backlog similarity evaluation
"""
import asyncio

from app.services.backlog_similarity import evaluate_similarity, batch_evaluate_similarity


async def test_single_similarity():
    """Test single similarity evaluation"""
    print("=" * 80)
    print("TEST 1: Single Similarity Evaluation")
    print("=" * 80)
    
    test_cases = [
        {
            "name": "High similarity - Same topic (Spanish to English)",
            "incoming_prompt": "Necesito integrar Stripe con mi sistema CRM",
            "incoming_comment": "Es urgente para procesar pagos",
            "card_prompt": "Add Stripe payment integration to CRM module"
        },
        {
            "name": "Medium similarity - Related features",
            "incoming_prompt": "Need email marketing automation",
            "incoming_comment": "For sending newsletters",
            "card_prompt": "CRM with email campaign management"
        },
        {
            "name": "Low similarity - Different topics",
            "incoming_prompt": "Quiero un sistema de contabilidad",
            "incoming_comment": "Con facturación automática",
            "card_prompt": "Project management with time tracking"
        },
        {
            "name": "No comment provided",
            "incoming_prompt": "Analytics dashboard for sales data",
            "incoming_comment": "",
            "card_prompt": "Sales analytics and reporting module"
        }
    ]
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n{i}. {test_case['name']}")
        print("-" * 80)
        print(f"Incoming: {test_case['incoming_prompt']}")
        if test_case['incoming_comment']:
            print(f"Comment: {test_case['incoming_comment']}")
        print(f"Card: {test_case['card_prompt']}")
        
        try:
            similarity = await evaluate_similarity(
                test_case['incoming_prompt'],
                test_case['incoming_comment'],
                test_case['card_prompt']
            )
            print(f"✅ Similarity: {similarity}%")
        except Exception as e:
            print(f"❌ Error: {str(e)}")
        
        print()


async def test_batch_similarity():
    """Test batch similarity evaluation"""
    print("=" * 80)
    print("TEST 2: Batch Similarity Evaluation")
    print("=" * 80)
    
    incoming_prompt = "Necesito un CRM con integración de Stripe y análisis de datos"
    incoming_comment = "Para mi empresa de e-commerce"
    
    cards = [
        ("card-001", "CRM with Stripe payment integration"),
        ("card-002", "E-commerce platform with analytics"),
        ("card-003", "Data analytics dashboard for sales"),
        ("card-004", "Email marketing automation tool"),
        ("card-005", "Accounting software with invoicing"),
        ("card-006", "CRM system with payment processing and reporting")
    ]
    
    print(f"\nIncoming Request:")
    print(f"  Prompt: {incoming_prompt}")
    print(f"  Comment: {incoming_comment}")
    print(f"\nComparing against {len(cards)} backlog cards...")
    print()
    
    try:
        results = await batch_evaluate_similarity(
            incoming_prompt,
            incoming_comment,
            cards
        )
        
        print("RESULTS (sorted by similarity):")
        print("-" * 80)
        for i, (card_id, similarity) in enumerate(results, 1):
            card_text = next(text for cid, text in cards if cid == card_id)
            print(f"{i}. {card_id}: {similarity}%")
            print(f"   {card_text}")
        
        print()
        print(f"✅ Top match: {results[0][0]} with {results[0][1]}% similarity")
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")


async def test_multilingual():
    """Test with multiple languages"""
    print("=" * 80)
    print("TEST 3: Multilingual Support")
    print("=" * 80)
    
    card_prompt = "Customer relationship management with email integration"
    
    test_cases = [
        {
            "lang": "English",
            "prompt": "I need a CRM system with email features",
            "comment": ""
        },
        {
            "lang": "Spanish",
            "prompt": "Necesito un sistema CRM con email",
            "comment": "Para gestionar clientes"
        },
        {
            "lang": "German",
            "prompt": "Ich brauche ein CRM-System mit E-Mail",
            "comment": ""
        },
        {
            "lang": "French",
            "prompt": "J'ai besoin d'un système CRM avec email",
            "comment": "Pour gérer mes clients"
        }
    ]
    
    print(f"\nCard Prompt: {card_prompt}\n")
    
    for test_case in test_cases:
        print(f"{test_case['lang']}:")
        print(f"  Prompt: {test_case['prompt']}")
        if test_case['comment']:
            print(f"  Comment: {test_case['comment']}")
        
        try:
            similarity = await evaluate_similarity(
                test_case['prompt'],
                test_case['comment'],
                card_prompt
            )
            print(f"  ✅ Similarity: {similarity}%")
        except Exception as e:
            print(f"  ❌ Error: {str(e)}")
        
        print()


async def test_edge_cases():
    """Test edge cases"""
    print("=" * 80)
    print("TEST 4: Edge Cases")
    print("=" * 80)
    
    test_cases = [
        {
            "name": "Empty comment",
            "prompt": "CRM system",
            "comment": "",
            "card": "Customer relationship management"
        },
        {
            "name": "Very short texts",
            "prompt": "CRM",
            "comment": "",
            "card": "CRM"
        },
        {
            "name": "Very long texts",
            "prompt": "I need a comprehensive customer relationship management system with advanced features including email marketing automation, sales pipeline management, contact segmentation, reporting and analytics, integration with payment gateways like Stripe and PayPal, mobile app support, and customizable dashboards for tracking key performance indicators",
            "comment": "This is for a mid-size company with about 50 sales representatives who need to manage customer interactions efficiently",
            "card": "CRM with email automation and payment integration"
        },
        {
            "name": "Special characters",
            "prompt": "Need CRM @ $100/month w/ Stripe & PayPal",
            "comment": "ASAP!!!",
            "card": "CRM with payment integrations (pricing flexible)"
        }
    ]
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n{i}. {test_case['name']}")
        print("-" * 80)
        
        try:
            similarity = await evaluate_similarity(
                test_case['prompt'],
                test_case['comment'],
                test_case['card']
            )
            print(f"✅ Similarity: {similarity}%")
        except Exception as e:
            print(f"❌ Error: {str(e)}")


async def run_all_tests():
    """Run all tests"""
    print("\n" + "=" * 80)
    print("BACKLOG SIMILARITY TESTS")
    print("=" * 80)
    print()
    
    try:
        await test_single_similarity()
        await test_batch_similarity()
        await test_multilingual()
        await test_edge_cases()
        
        print("\n" + "=" * 80)
        print("ALL TESTS COMPLETED")
        print("=" * 80)
        
    except Exception as e:
        print(f"\n❌ CRITICAL ERROR: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    print("Starting backlog similarity tests...")
    print("Note: This requires OpenAI API access and may take a few seconds per test.")
    print()
    
    asyncio.run(run_all_tests())
