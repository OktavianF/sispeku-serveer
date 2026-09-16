import uuid
import io
import asyncio
from datetime import datetime
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, status
from PIL import Image, UnidentifiedImageError

from app.auth import get_current_user
from app.database import supabase
from app.models.predictor import predictor
from app.schemas import PredictionResponse

router = APIRouter(prefix="/api", tags=["Prediction"])

MAX_FILE_SIZE_BYTES = 5 * 1024 * 1024
ALLOWED_MIME_TYPES = {"image/jpeg", "image/jpg", "image/png", "image/webp"}
ALLOWED_IMAGE_FORMATS = {"JPEG", "PNG", "WEBP"}
FORMAT_TO_MIME = {
    "JPEG": "image/jpeg",
    "PNG": "image/png",
    "WEBP": "image/webp",
}


def _convert_to_webp(img: Image.Image) -> bytes:
    """Convert a PIL Image to optimized WebP bytes while preserving visual quality."""
    if img.mode in ("RGBA", "LA", "P"):
        converted = img.convert("RGBA")
    else:
        converted = img.convert("RGB")

    output = io.BytesIO()
    converted.save(
        output,
        format="WEBP",
        quality=85,
        method=1,  # Lowest method reduces memory usage significantly (prevents libwebp OOM)
        optimize=False,
    )
    return output.getvalue()


@router.post("/predict", response_model=PredictionResponse)
async def predict_defect(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user),
):
    """Upload an image and get defect prediction."""
    # Validate MIME type from client metadata
    if not file.content_type or file.content_type.lower() not in ALLOWED_MIME_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Format file harus JPG, JPEG, PNG, atau WEBP.",
        )

    # Read file bytes
    image_bytes = await file.read()
    if len(image_bytes) > MAX_FILE_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ukuran file maksimal 5MB.",
        )

    # ── Single decode: validate and produce PIL.Image ──
    try:
        img = Image.open(io.BytesIO(image_bytes))
        detected_format = (img.format or "").upper()
        # Force full decode to catch truncated files early
        img.load()
    except UnidentifiedImageError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File gambar tidak valid atau rusak.",
        )

    if detected_format not in ALLOWED_IMAGE_FORMATS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Format file harus JPG, JPEG, PNG, atau WEBP.",
        )

    expected_mime = FORMAT_TO_MIME[detected_format]
    if file.content_type.lower() not in {expected_mime, "image/jpg"}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="MIME type tidak cocok dengan isi file gambar.",
        )

    # Resize if too large to prevent Out of Memory (OOM) errors and timeouts
    max_dim = 1024
    if max(img.size) > max_dim:
        # thumbnail is highly optimized and modifies the image in-place
        img.thumbnail((max_dim, max_dim), getattr(Image, "Resampling", Image).BILINEAR)

    # ── Sequential execution to prevent CPU/GIL contention and RAM spikes ──
    # 1. Run Model inference
    result = await asyncio.to_thread(predictor.predict_from_image, img)
    
    # 2. Run WebP conversion
    storage_bytes = await asyncio.to_thread(_convert_to_webp, img)

    # ── Parallel: Storage upload + DB insert ──
    user_id = current_user["id"]
    storage_filename = f"{user_id}/{uuid.uuid4()}.webp"
    scan_id = str(uuid.uuid4())
    insert_data = {
        "id": scan_id,
        "user_id": user_id,
        "filename": file.filename,
        "image_path": storage_filename,
        "is_defect": result["is_defect"],
        "defect_type": result["defect_type"],
        "confidence": result["confidence"],
        "model_version": "2.0",
    }

    image_uploaded = True
    created_at_val = datetime.utcnow().isoformat()

    def _upload():
        """Upload WebP bytes to Supabase Storage."""
        supabase.storage.from_("scan-images").upload(
            storage_filename,
            storage_bytes,
            {"content-type": "image/webp"},
        )

    def _insert():
        """Insert scan result into database."""
        return supabase.table("scan_results").insert(insert_data).execute()

    # Run upload + insert in parallel
    upload_task = asyncio.to_thread(_upload)
    insert_task = asyncio.to_thread(_insert)

    upload_exc = None
    insert_res = None
    try:
        results = await asyncio.gather(upload_task, insert_task, return_exceptions=True)

        # Check upload result
        if isinstance(results[0], Exception):
            upload_exc = results[0]
            image_uploaded = False
            print(f"⚠️ Storage upload failed: {results[0]}")

        # Check insert result
        if isinstance(results[1], Exception):
            raise results[1]
        else:
            insert_res = results[1]
            if insert_res and insert_res.data and len(insert_res.data) > 0:
                created_at_val = insert_res.data[0].get("created_at", created_at_val)

    except Exception as e:
        if not isinstance(e, HTTPException):
            print(f"❌ Database insert error: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Gagal menyimpan hasil scan: {str(e)}",
            )
        raise

    # Generate signed URL for the image (valid for 1 hour)
    image_url = ""
    if image_uploaded:
        try:
            signed = supabase.storage.from_("scan-images").create_signed_url(
                storage_filename, 3600
            )
            image_url = signed.get("signedURL", "")
        except Exception:
            image_url = ""

    return PredictionResponse(
        id=scan_id,
        filename=file.filename,
        image_url=image_url,
        is_defect=result["is_defect"],
        defect_type=result["defect_type"],
        confidence=result["confidence"],
        model_version="2.0",
        created_at=created_at_val,
        all_predictions=result.get("all_predictions"),
    )
