file_path = "/Users/oktaviansmac/project/sispeku-server/app/routes/predict.py"
with open(file_path, "r") as f:
    content = f.read()

# We need to replace the entire block inside prediction_lock
import re
match = re.search(r'(    async with prediction_lock:.*?    # ── Parallel: Storage upload \+ DB insert ──)', content, re.DOTALL)
if match:
    old_block = match.group(1)
    new_block = """    async with prediction_lock:
        img = None
        try:
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
            if img.size and max(img.size) > max_dim:
                # thumbnail is highly optimized and modifies the image in-place
                img.thumbnail((max_dim, max_dim), getattr(Image, "Resampling", Image).BILINEAR)

            # ── Sequential execution to prevent CPU/GIL contention and RAM spikes ──
            # 1. Run Model inference
            result = await asyncio.to_thread(predictor.predict_from_image, img)
            
            # 2. Run WebP conversion
            storage_bytes = await asyncio.to_thread(_convert_to_webp, img)
        finally:
            # ── GUARANTEED CLEANUP ──
            # Explicitly close the image and force garbage collection to prevent memory leaks
            if img is not None:
                try:
                    img.close()
                except Exception:
                    pass
            gc.collect()

    # ── Parallel: Storage upload + DB insert ──"""
    content = content.replace(old_block, new_block)
    with open(file_path, "w") as f:
        f.write(content)
    print("Fixed.")
else:
    print("Could not find the block to replace.")
