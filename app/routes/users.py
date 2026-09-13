from fastapi import APIRouter, Depends, HTTPException, status, Query

from app.auth import get_current_user, require_admin
from app.database import supabase
from app.schemas import (
    UserCreateRequest,
    UserUpdateRequest,
    UserResponse,
    MessageResponse,
)

router = APIRouter(prefix="/api/users", tags=["Users"])


def load_all_auth_users(per_page: int = 1000):
    """Load all auth users in batches to avoid per-profile lookups."""
    users = []
    page = 1

    while True:
        batch = supabase.auth.admin.list_users(page=page, per_page=per_page)
        if not batch:
            break

        users.extend(batch)

        if len(batch) < per_page:
            break

        page += 1

    return users


@router.get("/me")
async def get_current_profile(
    current_user: dict = Depends(get_current_user),
):
    """Get current user's profile."""
    result = (
        supabase.table("profiles")
        .select("id, username, full_name, role, created_at")
        .eq("id", current_user["id"])
        .single()
        .execute()
    )

    if not result.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profil tidak ditemukan.",
        )

    profile = result.data
    return UserResponse(
        id=profile["id"],
        email=current_user.get("email", ""),
        username=profile["username"],
        full_name=profile["full_name"],
        role=profile["role"],
        created_at=str(profile.get("created_at", "")),
    )


@router.get("")
async def list_users(
    page: int = Query(1, ge=1),
    limit: int = Query(5, ge=1, le=100),
    admin: dict = Depends(require_admin),
):
    """List all users with pagination. Admin only."""
    start = (page - 1) * limit
    end = start + limit - 1

    result = (
        supabase.table("profiles")
        .select("id, username, full_name, role, created_at", count="exact")
        .order("created_at", desc=False)
        .range(start, end)
        .execute()
    )

    # Get emails from auth.users via admin API in batches
    auth_users = load_all_auth_users()
    email_map = {user.id: user.email or "" for user in auth_users}

    users_data = result.data or []
    enriched = []
    for profile in users_data:
        enriched.append(
            UserResponse(
                id=profile["id"],
                email=email_map.get(profile["id"], ""),
                username=profile["username"],
                full_name=profile["full_name"],
                role=profile["role"],
                created_at=str(profile.get("created_at", "")),
            )
        )

    total_count = result.count if hasattr(result, "count") and result.count else len(enriched)
    has_more = start + limit < total_count

    return {
        "data": enriched,
        "page": page,
        "limit": limit,
        "total_count": total_count,
        "has_more": has_more
    }


@router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    req: UserCreateRequest,
    admin: dict = Depends(require_admin),
):
    """Create a new user. Admin only.

    Creates both the auth.users entry and the profiles entry.
    """
    # Create auth user via Supabase Admin API
    try:
        auth_result = supabase.auth.admin.create_user(
            {
                "email": req.email,
                "password": req.password,
                "email_confirm": True,  # Auto-confirm since admin is creating
                "app_metadata": {"role": req.role},
            }
        )
        new_user = auth_result.user
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Gagal membuat akun: {str(e)}",
        )

    # Create profile entry
    try:
        supabase.table("profiles").insert(
            {
                "id": new_user.id,
                "username": req.username,
                "full_name": req.full_name,
                "role": req.role,
            }
        ).execute()
    except Exception as e:
        # Rollback: delete the auth user if profile creation fails
        try:
            supabase.auth.admin.delete_user(new_user.id)
        except Exception:
            pass
        if "unique" in str(e).lower() or "duplicate" in str(e).lower():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Username sudah digunakan.",
            )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Gagal membuat profil: {str(e)}",
        )

    return UserResponse(
        id=new_user.id,
        email=req.email,
        username=req.username,
        full_name=req.full_name,
        role=req.role,
    )


@router.put("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: str,
    req: UserUpdateRequest,
    admin: dict = Depends(require_admin),
):
    """Update a user's profile. Admin only."""
    # Build update dict (only non-None fields)
    updates = {}
    if req.full_name is not None:
        updates["full_name"] = req.full_name
    if req.username is not None:
        updates["username"] = req.username
    if req.role is not None:
        updates["role"] = req.role

    profile = None
    if updates:
        updated = (
            supabase.table("profiles")
            .update(updates)
            .eq("id", user_id)
            .select("id, username, full_name, role, created_at")
            .execute()
        )
        profile = updated.data[0] if updated.data else None
        if not profile:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Pengguna tidak ditemukan.",
            )
    else:
        existing = (
            supabase.table("profiles")
            .select("id, username, full_name, role, created_at")
            .eq("id", user_id)
            .single()
            .execute()
        )
        if not existing.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Pengguna tidak ditemukan.",
            )
        profile = existing.data

    # Update password if provided
    if req.password:
        try:
            supabase.auth.admin.update_user_by_id(
                user_id, {"password": req.password}
            )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Gagal update password: {str(e)}",
            )

    # Fetch the updated user's actual email
    try:
        user_data = supabase.auth.admin.get_user_by_id(user_id)
        email = user_data.user.email
    except Exception:
        email = ""

    return UserResponse(
        id=profile["id"],
        email=email,
        username=profile["username"],
        full_name=profile["full_name"],
        role=profile["role"],
        created_at=str(profile.get("created_at", "")),
    )


@router.delete("/{user_id}", response_model=MessageResponse)
async def delete_user(
    user_id: str,
    admin: dict = Depends(require_admin),
):
    """Delete a user. Admin only. Cannot delete self."""
    if user_id == admin["id"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tidak bisa menghapus akun sendiri.",
        )

    # Delete from auth (cascade will remove profile)
    try:
        supabase.auth.admin.delete_user(user_id)
    except Exception as e:
        if isinstance(e, HTTPException):
            raise
        if "not found" in str(e).lower() or "does not exist" in str(e).lower():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Pengguna tidak ditemukan.",
            )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Gagal menghapus pengguna: {str(e)}",
        )

    return MessageResponse(message="Pengguna berhasil dihapus.")
