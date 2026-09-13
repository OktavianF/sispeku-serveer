"""
Singleton Supabase client.

Reused across all requests to avoid the overhead of creating
a new HTTP connection on every incoming request.
"""

from supabase import create_client
from app.config import SUPABASE_URL, SUPABASE_SERVICE_KEY

supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
