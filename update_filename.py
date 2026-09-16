import re

file_path = '/Users/oktaviansmac/project/KulitDetect/src/pages/ScanPage.jsx'
with open(file_path, 'r') as f:
    content = f.read()

old_code = """    const compressed = await imageCompression(file, options);
    console.log("Original size:", file.size, "Compressed size:", compressed.size);
    return compressed;"""

new_code = """    const compressed = await imageCompression(file, options);
    console.log("Original size:", file.size, "Compressed size:", compressed.size);
    // Ensure the original filename is preserved
    return new File([compressed], file.name || "image.jpg", { type: compressed.type });"""

if old_code in content:
    content = content.replace(old_code, new_code)
    with open(file_path, 'w') as f:
        f.write(content)
    print("Updated successfully.")
else:
    print("Old code not found.")
