with open('/Users/oktaviansmac/project/KulitDetect/src/pages/ScanPage.jsx', 'r') as f:
    content = f.read()

old_func = """  try {
    return await imageCompression(file, options);
  } catch (error) {
    console.error("Image compression error:", error);
    return file;
  }"""

new_func = """  try {
    const compressed = await imageCompression(file, options);
    console.log("Original size:", file.size, "Compressed size:", compressed.size);
    return compressed;
  } catch (error) {
    console.error("Image compression error:", error);
    throw new Error("Gagal mengkompres gambar di perangkat Anda. Silakan gunakan gambar yang lebih kecil.");
  }"""

content = content.replace(old_func, new_func)

with open('/Users/oktaviansmac/project/KulitDetect/src/pages/ScanPage.jsx', 'w') as f:
    f.write(content)
