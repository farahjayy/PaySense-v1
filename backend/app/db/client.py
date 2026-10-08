"""Supabase client — created once, server-side only (service_role key)."""
from functools import lru_cache

from supabase import Client, create_client

from app import config


@lru_cache(maxsize=1)
def get_db() -> Client:
    config.validate_env()
    return create_client(config.SUPABASE_URL, config.SUPABASE_SERVICE_KEY)
