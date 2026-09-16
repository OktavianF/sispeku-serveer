file_path = "/Users/oktaviansmac/project/sispeku-server/app/models/predictor.py"
with open(file_path, "r") as f:
    content = f.read()

import re
old_block = """            self.is_loaded = True
            print(f"✅ Model loaded successfully from {model_path}")"""

new_block = """            # CLEANUP to reduce base memory footprint
            del checkpoint
            import gc
            gc.collect()
            try:
                import ctypes
                ctypes.CDLL("libc.so.6").malloc_trim(0)
            except Exception:
                pass

            self.is_loaded = True
            print(f"✅ Model loaded successfully from {model_path}")"""

if old_block in content:
    content = content.replace(old_block, new_block)
    with open(file_path, "w") as f:
        f.write(content)
    print("Fixed predictor.py with GC and malloc_trim")
else:
    print("Could not find the block to replace.")
