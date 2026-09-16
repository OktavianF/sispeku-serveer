file_path = "/Users/oktaviansmac/project/sispeku-server/app/routes/predict.py"
with open(file_path, "r") as f:
    content = f.read()

import re
old_block = """            if img is not None:
                try:
                    img.close()
                except Exception:
                    pass
            gc.collect()"""
new_block = """            if img is not None:
                try:
                    img.close()
                except Exception:
                    pass
            gc.collect()
            
            # Force glibc to return freed memory to the OS (prevents Docker OOM kills)
            try:
                import ctypes
                ctypes.CDLL("libc.so.6").malloc_trim(0)
            except Exception:
                pass"""

if old_block in content:
    content = content.replace(old_block, new_block)
    with open(file_path, "w") as f:
        f.write(content)
    print("Fixed predict.py with malloc_trim")
else:
    print("Could not find the block to replace.")
