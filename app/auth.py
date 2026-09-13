from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.database import supabase

security = HTTPBearer()

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> dict:
    """Extract current user from JWT token using Supabase SDK."""
    try:
        user_res = supabase.auth.get_user(credentials.credentials)
        user = user_res.user
        if not user:
            raise ValueError("Token tidak berisi data user.")
            
        return {
            "id": user.id,
            "email": user.email,
            "role": user.app_metadata.get("role", "authenticated"),
            "token": credentials.credentials,
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Token tidak valid: {str(e)}",
        )

async def require_admin(
    current_user: dict = Depends(get_current_user),
) -> dict:
    """Require the current user to have admin role."""
    if current_user.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Akses ditolak. Hanya admin yang dapat mengakses endpoint ini.",
        )

    current_user["db_role"] = "admin"
    return current_user
