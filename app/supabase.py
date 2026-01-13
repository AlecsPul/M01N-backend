"""
Supabase Client Configuration
"""
from supabase import create_client, Client
from app.config import settings

def get_supabase_client() -> Client:
    """
    Create and return Supabase client instance
    
    Usage:
        supabase = get_supabase_client()
        data = supabase.table('users').select('*').execute()
    """
    return create_client(settings.supabase_url, settings.supabase_key)


# Global Supabase client instance
supabase: Client = get_supabase_client()
