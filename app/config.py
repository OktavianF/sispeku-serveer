import os
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY", "")
SUPABASE_JWT_SECRET = os.getenv("SUPABASE_JWT_SECRET", "")
MODEL_PATH = os.getenv("MODEL_PATH", "./model/model.pkl")

# Defect class labels matching the professor's notebook
# Binary classification: Defect (index 0), Normal (index 1)
DEFECT_CLASSES = [
    "Defect",
    "Normal",
]

# Model input config
MODEL_INPUT_SIZE = (224, 224)

# ImageNet normalization constants (used by torchvision pretrained models)
IMAGENET_MEAN = [0.485, 0.456, 0.406]
IMAGENET_STD = [0.229, 0.224, 0.225]
