"""Quick diagnostic script to check raw model outputs."""
import os
import numpy as np
from PIL import Image
import tensorflow as tf

MODEL_PATH = "./model/model.keras"
DATASET_DIR = os.path.expanduser("~/Downloads/LeatherDefectClassification")

print("Loading model...")
model = tf.keras.models.load_model(MODEL_PATH)
print(f"Input shape: {model.input_shape}")
print(f"Output shape: {model.output_shape}")
print()

def predict_image(image_path):
    img = Image.open(image_path).convert("RGB").resize((224, 224), Image.Resampling.LANCZOS)
    img_array = np.array(img, dtype=np.float32) / 255.0
    img_array = np.expand_dims(img_array, axis=0)
    prediction = model.predict(img_array, verbose=0)
    return float(prediction[0][0])

# Test on defect images
print("=" * 60)
print("DEFECT IMAGES (expected: these should be classified as DEFECT)")
print("=" * 60)
defect_dir = os.path.join(DATASET_DIR, "defect")
defect_files = sorted(os.listdir(defect_dir))[:5]
for f in defect_files:
    val = predict_image(os.path.join(defect_dir, f))
    label = "DEFECT" if val >= 0.5 else "NORMAL"
    print(f"  {f:40s} → raw={val:.4f}  →  {label}")

print()

# Test on non-defect images
print("=" * 60)
print("NON-DEFECT IMAGES (expected: these should be classified as NORMAL)")
print("=" * 60)
nondefect_dir = os.path.join(DATASET_DIR, "non_defect")
nondefect_files = sorted(os.listdir(nondefect_dir))[:5]
for f in nondefect_files:
    val = predict_image(os.path.join(nondefect_dir, f))
    label = "DEFECT" if val >= 0.5 else "NORMAL"
    print(f"  {f:40s} → raw={val:.4f}  →  {label}")

print()
print("INTERPRETATION:")
print("  If raw value ≥ 0.5 → model says DEFECT")
print("  If raw value < 0.5 → model says NORMAL")
print("  If results are INVERTED, we need to flip the logic.")
