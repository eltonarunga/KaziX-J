"""
app/core/supabase.py
────────────────────
Two Supabase client factories:
 
  get_anon_client()     → uses ANON key.  Safe for user-scoped operations
                          (RLS enforced).  Import in route handlers.
 
  get_admin_client()    → uses SERVICE ROLE key.  Bypasses RLS entirely.
                          ONLY import in internal services / background jobs.
                          NEVER expose to browser or pass to client responses.
 
Both clients are module-level singletons (created once, reused).
"""
 
from functools import lru_cache
 
from supabase import Client, create_client
 
from app.core.config import get_settings
 
 
@lru_cache
def get_anon_client() -> Client:
    """
    Public Supabase client — respects RLS policies.
    Use for all user-facing data operations.
    """
    s = get_settings()
    return create_client(s.supabase_url, s.supabase_anon_key)
 
 
@lru_cache
def get_admin_client() -> Client:
    """
    Admin Supabase client — bypasses RLS (service role key).
    Strictly server-side only:
      - OTP verification flows
      - Background jobs
      - Admin API routes
      - Webhook handlers
    """
    s = get_settings()
    return create_client(s.supabase_url, s.supabase_service_role_key)
