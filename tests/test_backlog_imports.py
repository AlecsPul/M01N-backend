"""
Quick test to verify backlog endpoint imports work correctly
"""
import asyncio


async def test_imports():
    """Test that all backlog modules import correctly"""
    print("Testing imports...")
    
    try:
        # Test schema imports
        from app.schemas.backlog import BacklogIngestRequest, BacklogIngestResponse
        print("✅ Schema imports successful")
        
        # Test route imports
        from app.api.backlog_routes import router
        print("✅ Route imports successful")
        
        # Test backlog service imports
        from app.services.backlog_matcher import find_matching_card_id
        from app.services.backlog_card_generation import generate_card_title_description
        from app.services.backlog_repository import process_incoming_request
        from app.services.backlog_similarity import evaluate_similarity
        print("✅ Backlog service imports successful")
        
        # Test schema validation
        request = BacklogIngestRequest(
            prompt_text="Test request for integration",
            comment_text="This is a test"
        )
        print(f"✅ Schema validation successful: {request}")
        
        print("\n✅ All imports and basic validation passed!")
        return True
        
    except Exception as e:
        print(f"❌ Import test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    import sys
    success = asyncio.run(test_imports())
    sys.exit(0 if success else 1)
