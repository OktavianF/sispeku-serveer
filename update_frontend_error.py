import re

file_path = '/Users/oktaviansmac/project/KulitDetect/src/pages/ScanPage.jsx'
with open(file_path, 'r') as f:
    content = f.read()

old_catch = """    } catch (err) {
      console.error(err);
      setError(err.message || "Gagal menghubungi server AI. Pastikan backend FastAPI sudah berjalan.");
    }"""

new_catch = """    } catch (err) {
      console.error(err);
      let errorMsg = err.message || "Gagal menghubungi server AI. Pastikan backend FastAPI sudah berjalan.";
      if (errorMsg.includes("NetworkError") || errorMsg.includes("Failed to fetch")) {
        errorMsg = "Koneksi ke server terputus atau server sedang sibuk memproses antrean. Silakan coba tekan tombol analisis lagi.";
      }
      setError(errorMsg);
    }"""

content = content.replace(old_catch, new_catch)

with open(file_path, 'w') as f:
    f.write(content)
