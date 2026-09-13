from fastapi import APIRouter, Depends, Query, HTTPException, status
from typing import Optional

from app.auth import get_current_user, require_admin
from app.database import supabase
from app.schemas import StatsResponse

router = APIRouter(prefix="/api", tags=["History"])


def get_scan_stats(user_id: Optional[str]):
    """Fetch scan statistics from a SQL function instead of loading all rows."""
    result = supabase.rpc(
        "get_scan_stats",
        {"p_user_id": user_id},
    ).execute()

    rows = result.data or []
    if not rows:
        return StatsResponse(
            total_scans=0,
            total_defects=0,
            total_normal=0,
            defect_rate=0,
        )

    stats = rows[0]
    return StatsResponse(
        total_scans=stats.get("total_scans", 0),
        total_defects=stats.get("total_defects", 0),
        total_normal=stats.get("total_normal", 0),
        defect_rate=stats.get("defect_rate", 0),
    )


def get_history_page(
    user_id: str,
    is_admin: bool,
    filter_value: str,
    page: int,
    limit: int,
    worker_id: Optional[str],
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
):
    """Fetch a paginated history page from SQL instead of issuing multiple queries."""
    offset = (page - 1) * limit
    result = supabase.rpc(
        "get_history_page",
        {
            "p_user_id": user_id,
            "p_is_admin": is_admin,
            "p_filter": filter_value,
            "p_offset": offset,
            "p_limit": limit,
            "p_worker_id": worker_id,
            "p_start_date": start_date,
            "p_end_date": end_date,
        },
    ).execute()

    count_result = supabase.rpc(
        "get_history_count",
        {
            "p_user_id": user_id,
            "p_is_admin": is_admin,
            "p_filter": filter_value,
            "p_worker_id": worker_id,
            "p_start_date": start_date,
            "p_end_date": end_date,
        },
    ).execute()

    total_count = count_result.data if count_result.data else 0
    import math
    total_pages = math.ceil(total_count / limit) if total_count > 0 else 1

    return {
        "data": result.data or [],
        "page": page,
        "limit": limit,
        "total_count": total_count,
        "total_pages": total_pages,
    }


@router.get("/history")
async def get_history(
    filter: str = Query("all", pattern="^(all|ok|defect)$"),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    worker_id: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    current_user: dict = Depends(get_current_user),
):
    """Get scan history.

    - Workers see only their own scans.
    - Admins see all scans (optionally filter by worker_id).
    - Can filter by date range.
    """
    is_admin = current_user.get("role") == "admin"

    # If only one date is provided (e.g. start_date=2024-05-15, end_date=2024-05-15)
    # Ensure end_date covers the whole day
    if start_date and not end_date:
        end_date = start_date
    
    if end_date and len(end_date) <= 10:
        end_date = f"{end_date}T23:59:59Z"

    if start_date and len(start_date) <= 10:
        start_date = f"{start_date}T00:00:00Z"

    return get_history_page(
        user_id=current_user["id"],
        is_admin=is_admin,
        filter_value=filter,
        page=page,
        limit=limit,
        worker_id=worker_id,
        start_date=start_date,
        end_date=end_date,
    )


@router.get("/history/{scan_id}")
async def get_scan_detail(
    scan_id: str,
    current_user: dict = Depends(get_current_user),
):
    """Get detail of a specific scan result."""
    result = (
        supabase.table("scan_results")
        .select("id, filename, image_path, is_defect, defect_type, confidence, created_at, user_id")
        .eq("id", scan_id)
        .single()
        .execute()
    )

    if not result.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Scan result tidak ditemukan.",
        )

    scan = result.data

    # Check access: workers can only see own scans
    is_admin = current_user.get("role") == "admin"

    if not is_admin and scan["user_id"] != current_user["id"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Anda tidak memiliki akses ke scan ini.",
        )

    # Generate signed URL for image
    try:
        signed = supabase.storage.from_("scan-images").create_signed_url(
            scan["image_path"], 3600
        )
        scan["image_url"] = signed.get("signedURL", "")
    except Exception:
        scan["image_url"] = ""

    return scan


@router.get("/stats", response_model=StatsResponse)
async def get_stats(
    current_user: dict = Depends(get_current_user),
):
    """Get scan statistics.

    - Workers: personal stats.
    - Admins: global stats.
    """
    is_admin = current_user.get("role") == "admin"

    user_id = None if is_admin else current_user["id"]
    return get_scan_stats(user_id)
