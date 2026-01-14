"""
Test script for Interactive Matching endpoints
Usage:
    python tests/test_interactive_match.py
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
START_ENDPOINT = "/api/v1/match/interactive/start"
CONTINUE_ENDPOINT = "/api/v1/match/interactive/continue"
FINALIZE_ENDPOINT = "/api/v1/match/interactive/finalize"


async def test_interactive_flow():
    """Test complete interactive matching flow"""
    
    print("\n" + "="*70)
    print("🚀 INTERACTIVE MATCHING TEST")
    print("="*70)
    
    async with httpx.AsyncClient(timeout=90.0) as client:
        
        # Step 1: Start session with initial prompt
        print("\n📝 STEP 1: Starting session with initial prompt...")
        print("-" * 70)
        
        initial_prompt = "I need a CRM for my small business in Switzerland"
        
        start_payload = {
            "prompt_text": initial_prompt
        }
        
        print(f"Prompt: {initial_prompt}")
        
        try:
            response = await client.post(f"{BASE_URL}{START_ENDPOINT}", json=start_payload)
            response.raise_for_status()
            result = response.json()
            
            print(f"\n✅ Status: {result['status']}")
            
            if result['status'] == 'ready':
                print("\n🎉 Session is already valid!")
                print(f"Final prompt: {result['final_prompt']}")
                return
            
            # Session needs more info
            session = result['session']
            missing = result['missing']
            question = result['question']
            
            print(f"\n❓ Question: {question}")
            print(f"\n📊 Missing:")
            print(f"   - Labels needed: {missing['labels_needed']}")
            print(f"   - Tags needed: {missing['tags_needed']}")
            print(f"   - Integrations needed: {missing['integrations_needed']}")
            print(f"\n📦 Current accumulated:")
            print(f"   - Labels: {session['accumulated']['labels']}")
            print(f"   - Tags: {session['accumulated']['tags']}")
            print(f"   - Integrations: {session['accumulated']['integrations']}")
            
            # Step 2: Continue with answers
            turn = 1
            max_turns = 5
            
            while result['status'] == 'needs_more' and turn <= max_turns:
                print(f"\n📝 STEP {turn + 1}: Answering question...")
                print("-" * 70)
                
                # Simulate user answering
                print(f"\n❓ Question: {result['question']}")
                answer = input("\n💬 Your answer (or press Enter for default): ").strip()
                
                if not answer:
                    # Provide default answers based on what's missing
                    if missing['labels_needed'] > 0:
                        answer = "I need Analytics, Sales, and Marketing Automation features"
                    elif missing['integrations_needed'] > 0:
                        answer = "Must integrate with Stripe and Shopify"
                    elif missing['tags_needed'] > 0:
                        answer = "SME, E-commerce, Switzerland"
                    else:
                        answer = "No additional requirements"
                    print(f"   Using default: {answer}")
                
                continue_payload = {
                    "session": session,
                    "answer_text": answer
                }
                
                response = await client.post(f"{BASE_URL}{CONTINUE_ENDPOINT}", json=continue_payload)
                response.raise_for_status()
                result = response.json()
                
                print(f"\n✅ Status: {result['status']}")
                
                session = result['session']
                missing = result.get('missing', {})
                
                print(f"\n📦 Current accumulated:")
                print(f"   - Labels: {session['accumulated']['labels']}")
                print(f"   - Tags: {session['accumulated']['tags']}")
                print(f"   - Integrations: {session['accumulated']['integrations']}")
                
                if result['status'] == 'ready':
                    print(f"\n🎉 Session is now valid!")
                    break
                else:
                    print(f"\n📊 Still missing:")
                    print(f"   - Labels needed: {missing['labels_needed']}")
                    print(f"   - Tags needed: {missing['tags_needed']}")
                    print(f"   - Integrations needed: {missing['integrations_needed']}")
                
                turn += 1
            
            # Step 3: Finalize and get matches
            if result['status'] == 'ready':
                print(f"\n📝 STEP {turn + 1}: Running final match...")
                print("-" * 70)
                
                finalize_payload = {
                    "session": session,
                    "top_k": 30,
                    "top_n": 10
                }
                
                response = await client.post(f"{BASE_URL}{FINALIZE_ENDPOINT}", json=finalize_payload)
                response.raise_for_status()
                result = response.json()
                
                print("\n✅ Matching complete!")
                print(f"\n📄 Final Prompt:")
                print("-" * 70)
                print(result['final_prompt'])
                print("-" * 70)
                
                if result.get('results'):
                    print(f"\n🎯 Top {len(result['results'])} Matches:")
                    print("=" * 70)
                    for i, match in enumerate(result['results'], 1):
                        print(f"\n{i}. {match['name']}")
                        print(f"   Match: {match['similarity_percent']:.1f}%")
                        print(f"   ID: {match['app_id']}")
                
                # Save full result
                output_file = project_root / "tests" / "interactive_match_result.json"
                with open(output_file, "w") as f:
                    json.dump(result, f, indent=2)
                print(f"\n💾 Full result saved to: {output_file}")
            else:
                print("\n⚠️ Max turns reached without completing requirements")
                
        except httpx.HTTPStatusError as e:
            print(f"\n❌ HTTP Error: {e.response.status_code}")
            print(f"Detail: {e.response.text}")
        except httpx.ConnectError:
            print("\n❌ ERROR: Could not connect to server.")
            print("Make sure the FastAPI server is running:")
            print("  uvicorn app.main:app --reload")
        except Exception as e:
            print(f"\n❌ ERROR: {str(e)}")


async def test_direct_valid_prompt():
    """Test with a prompt that's immediately valid"""
    
    print("\n" + "="*70)
    print("🚀 DIRECT VALID PROMPT TEST")
    print("="*70)
    
    prompt = """I need a business application with these features:
    - CRM and customer management
    - Analytics and reporting
    - Sales automation
    - Marketing automation
    - Must integrate with Stripe, Shopify, and Mailchimp
    - Tags: E-commerce, SME, Switzerland"""
    
    async with httpx.AsyncClient(timeout=90.0) as client:
        try:
            response = await client.post(
                f"{BASE_URL}{START_ENDPOINT}",
                json={"prompt_text": prompt}
            )
            response.raise_for_status()
            result = response.json()
            
            print(f"\n✅ Status: {result['status']}")
            
            if result['status'] == 'ready':
                print("\n🎉 Prompt was immediately valid!")
                print(f"\n📦 Accumulated:")
                print(f"   - Labels: {result['session']['accumulated']['labels']}")
                print(f"   - Tags: {result['session']['accumulated']['tags']}")
                print(f"   - Integrations: {result['session']['accumulated']['integrations']}")
                
                # Run finalization
                finalize_response = await client.post(
                    f"{BASE_URL}{FINALIZE_ENDPOINT}",
                    json={
                        "session": result['session'],
                        "top_k": 30,
                        "top_n": 5
                    }
                )
                finalize_response.raise_for_status()
                final = finalize_response.json()
                
                print(f"\n🎯 Top {len(final['results'])} Matches:")
                for i, match in enumerate(final['results'], 1):
                    print(f"  {i}. {match['name']} - {match['similarity_percent']:.1f}%")
            
        except Exception as e:
            print(f"\n❌ ERROR: {str(e)}")


def main():
    print("\n🧪 Interactive Matching Test Suite")
    print("="*70)
    
    choice = input("\nSelect test:\n  1. Interactive flow (with questions)\n  2. Direct valid prompt\n  3. Both\n\nChoice (1-3): ").strip()
    
    if choice == "1":
        asyncio.run(test_interactive_flow())
    elif choice == "2":
        asyncio.run(test_direct_valid_prompt())
    elif choice == "3":
        asyncio.run(test_interactive_flow())
        print("\n" + "="*70 + "\n")
        asyncio.run(test_direct_valid_prompt())
    else:
        print("Invalid choice")


if __name__ == "__main__":
    main()
