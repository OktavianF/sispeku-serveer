def patch():
    with open("app/routes/predict.py", "r") as f:
        content = f.read()
    
    # Replace method=6 with method=4
    content = content.replace("method=6,", "method=4,")
    
    # Add a resize step before convert
    resize_code = """
    # Resize if too large to prevent OOM
    max_dim = 1920
    if max(img.size) > max_dim:
        ratio = max_dim / max(img.size)
        new_size = (int(img.width * ratio), int(img.height * ratio))
        img = img.resize(new_size, Image.Resampling.LANCZOS)

    if img.mode in ("RGBA", "LA", "P"):"""
    
    content = content.replace('    if img.mode in ("RGBA", "LA", "P"):', resize_code)
    
    with open("app/routes/predict.py", "w") as f:
        f.write(content)

patch()
