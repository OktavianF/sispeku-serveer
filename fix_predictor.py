file_path = "/Users/oktaviansmac/project/sispeku-server/app/models/predictor.py"
with open(file_path, "r") as f:
    content = f.read()

import re
old_block = """        try:
            rgb_image = image.convert("RGB") if image.mode != "RGB" else image
            tensor = self.transform(rgb_image).unsqueeze(0).to(self.device)

            with torch.no_grad():
                outputs = self.model(tensor)"""
new_block = """        try:
            rgb_image = image.convert("RGB") if image.mode != "RGB" else image
            try:
                tensor = self.transform(rgb_image).unsqueeze(0).to(self.device)
            finally:
                if rgb_image is not image:
                    rgb_image.close()

            with torch.no_grad():
                outputs = self.model(tensor)"""

if old_block in content:
    content = content.replace(old_block, new_block)
    with open(file_path, "w") as f:
        f.write(content)
    print("Fixed predictor.py")
else:
    print("Old block not found in predictor.py")

