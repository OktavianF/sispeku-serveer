"""
Skin defect predictor using PyTorch EfficientNet-B0 model.

Based on the professor's Kaggle notebook comparing EfficientNet-B0, MobileNetV3-Small,
and ResNet18 on the Manding Leather Dataset.
Best model: EfficientNet-B0 (F1 Defect: 89.66%, Accuracy: 86.36%)
2 classes: Defect, Normal
"""

import os
import io
import random
import numpy as np
from PIL import Image

from app.config import DEFECT_CLASSES, MODEL_INPUT_SIZE, IMAGENET_MEAN, IMAGENET_STD

# Try to import PyTorch; if not available, use dummy mode
try:
    import torch
    import torch.nn as nn
    from torchvision.models import efficientnet_b0
    from torchvision import transforms
    TORCH_AVAILABLE = True
    
    # CRITICAL FIX for Cloud Deployments (FastAPI Cloud, Heroku, Railway, etc.)
    # Limit PyTorch to 1 CPU thread to prevent massive memory spikes (OOM Kills)
    # caused by PyTorch allocating buffers for all available virtual CPU cores.
    os.environ["OMP_NUM_THREADS"] = "1"
    os.environ["MKL_NUM_THREADS"] = "1"
    torch.set_num_threads(1)
except ImportError:
    TORCH_AVAILABLE = False
    print("⚠️  PyTorch not installed. Running in DUMMY prediction mode.")


class SkinDefectPredictor:
    def __init__(self):
        self.model = None
        self.classes = DEFECT_CLASSES
        self.input_size = MODEL_INPUT_SIZE
        self.is_loaded = False
        self.device = None
        self.transform = None

    def load_model(self, model_path: str) -> bool:
        """Load the PyTorch EfficientNet-B0 model from a .pkl checkpoint."""
        if not TORCH_AVAILABLE:
            print("⚠️  PyTorch not available. Using dummy predictions.")
            return False

        if not os.path.exists(model_path):
            print(f"⚠️  Model file not found at {model_path}. Using dummy predictions.")
            return False

        try:
            import pickle

            self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

            # Load checkpoint (saved with pickle.dump, not torch.save)
            with open(model_path, "rb") as f:
                checkpoint = pickle.load(f)

            # Read metadata from checkpoint
            class_names = checkpoint.get("class_names", DEFECT_CLASSES)
            self.classes = class_names
            num_classes = len(self.classes)

            img_size = checkpoint.get("img_size", MODEL_INPUT_SIZE[0])
            self.input_size = (img_size, img_size)

            # Rebuild model architecture (matching the notebook's build_model function)
            model = efficientnet_b0(weights=None)
            in_features = model.classifier[1].in_features
            model.classifier = nn.Sequential(
                nn.Dropout(p=0.40),
                nn.Linear(in_features, num_classes),
            )

            # Load trained weights
            model.load_state_dict(checkpoint["model_state_dict"])
            model.to(self.device)
            model.eval()

            self.model = model

            # Build preprocessing pipeline (matching notebook cell #6: val_test_transform)
            self.transform = transforms.Compose([
                transforms.Resize(256),
                transforms.CenterCrop(self.input_size[0]),
                transforms.ToTensor(),
                transforms.Normalize(IMAGENET_MEAN, IMAGENET_STD),
            ])

            # CLEANUP to reduce base memory footprint
            del checkpoint
            import gc
            gc.collect()
            try:
                import ctypes
                ctypes.CDLL("libc.so.6").malloc_trim(0)
            except Exception:
                pass

            self.is_loaded = True
            print(f"✅ Model loaded successfully from {model_path}")
            print(f"   Device: {self.device}")
            print(f"   Architecture: {checkpoint.get('display_name', checkpoint.get('model_name', 'unknown'))}")
            print(f"   Classes: {self.classes}")
            print(f"   Input size: {self.input_size}")
            print(f"   Best val loss: {checkpoint.get('best_val_loss', 'N/A')}")
            print(f"   Test accuracy: {checkpoint.get('test_accuracy', 'N/A')}")
            print(f"   F1 Defect: {checkpoint.get('selection_metric_value', 'N/A')}")

            return True
        except Exception as e:
            print(f"❌ Failed to load model: {e}")
            import traceback
            traceback.print_exc()
            return False

    def preprocess_image(self, image_bytes: bytes) -> "torch.Tensor":
        """Preprocess image for model input.

        Uses the same pipeline as the notebook's val_test_transform:
        - Resize to 256px (shortest side)
        - CenterCrop to 224x224
        - ToTensor (converts to [0,1] float)
        - Normalize with ImageNet mean/std
        - Add batch dimension
        """
        image = Image.open(io.BytesIO(image_bytes))
        image = image.convert("RGB")
        tensor = self.transform(image)
        tensor = tensor.unsqueeze(0)  # Add batch dim: [1, 3, 224, 224]
        return tensor.to(self.device)

    def predict(self, image_bytes: bytes) -> dict:
        """Run prediction on raw image bytes (convenience wrapper).

        Decodes bytes to PIL.Image, then delegates to predict_from_image().
        Prefer predict_from_image() when a PIL.Image is already available.
        """
        if not self.is_loaded or self.model is None:
            return self._dummy_predict()

        try:
            image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
            return self.predict_from_image(image)
        except Exception as e:
            print(f"❌ Prediction error: {e}")
            import traceback
            traceback.print_exc()
            return self._dummy_predict()

    def predict_from_image(self, image: "Image.Image") -> dict:
        """Run prediction on a PIL.Image object.

        Binary classification: Defect (index 0) vs Normal (index 1)

        Args:
            image: A PIL.Image already in RGB mode.

        Returns:
            dict with keys:
                is_defect (bool): True if defect detected
                defect_type (str): "Cacat Terdeteksi" or "Tidak Ada"
                confidence (float): Confidence percentage (0-100)
                all_predictions (dict): All class probabilities
        """
        if not self.is_loaded or self.model is None:
            return self._dummy_predict()

        try:
            rgb_image = image.convert("RGB") if image.mode != "RGB" else image
            try:
                tensor = self.transform(rgb_image).unsqueeze(0).to(self.device)
            finally:
                if rgb_image is not image:
                    rgb_image.close()

            with torch.no_grad():
                outputs = self.model(tensor)
                probabilities = torch.softmax(outputs, dim=1)[0]

            probs_np = probabilities.cpu().numpy()

            # Class indices: 0 = Defect, 1 = Normal
            predicted_idx = int(np.argmax(probs_np))
            confidence = float(probs_np[predicted_idx]) * 100

            is_defect = predicted_idx == 0  # Defect is index 0

            if is_defect:
                defect_type = "Cacat Terdeteksi"
            else:
                defect_type = "Tidak Ada"

            all_preds = {
                self.classes[i]: round(float(probs_np[i]) * 100, 2)
                for i in range(len(self.classes))
            }

            return {
                "is_defect": is_defect,
                "defect_type": defect_type,
                "confidence": round(confidence, 2),
                "all_predictions": all_preds,
            }
        except Exception as e:
            print(f"❌ Prediction error: {e}")
            import traceback
            traceback.print_exc()
            return self._dummy_predict()

    def _dummy_predict(self) -> dict:
        """Generate dummy prediction when model is not available."""
        is_defect = random.random() > 0.5
        if is_defect:
            defect_type = "Cacat Terdeteksi"
            confidence = round(random.uniform(70, 98), 2)
        else:
            defect_type = "Tidak Ada"
            confidence = round(random.uniform(85, 99), 2)

        return {
            "is_defect": is_defect,
            "defect_type": defect_type,
            "confidence": confidence,
            "all_predictions": {"dummy": True},
        }


# Singleton instance
predictor = SkinDefectPredictor()
