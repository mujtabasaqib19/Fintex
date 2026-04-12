"""
Supabase database connection management.
"""
from functools import lru_cache
from supabase import create_client, Client
import sys
import os

# Add config to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
from config.settings import get_settings


@lru_cache()
def get_supabase_client() -> Client:
    """
    Get a cached Supabase client instance.
    Uses service key if available, otherwise anon key.
    """
    settings = get_settings()
    key = settings.supabase_service_key or settings.supabase_key
    return create_client(settings.supabase_url, key)


def get_supabase_admin_client() -> Client:
    """
    Get a Supabase client with service role key.
    Required for admin operations like creating tables.
    """
    settings = get_settings()
    if not settings.supabase_service_key:
        raise ValueError("SUPABASE_SERVICE_KEY required for admin operations")
    return create_client(settings.supabase_url, settings.supabase_service_key)
