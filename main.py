"""
Sispeku Backend — FastAPI + Supabase

Leather defect detection API with PyTorch EfficientNet-B0 model inference.
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import MODEL_PATH
from app.models.predictor import predictor
from app.routes import predict, history, users


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Load ML model on startup, cleanup on shutdown."""
    print("🚀 Starting Sispeku Backend...")
    predictor.load_model(MODEL_PATH)
    yield
    print("👋 Shutting down Sispeku Backend.")


app = FastAPI(
    title="Sispeku API",
    description="API untuk deteksi kecacatan kulit menggunakan model PyTorch EfficientNet-B0.",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS — allow all browser origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(predict.router)
app.include_router(history.router)
app.include_router(users.router)


@app.get("/")
async def root():
    return {
        "name": "Sispeku API",
        "version": "1.0.0",
        "model_loaded": predictor.is_loaded,
        "docs": "/docs",
    }


@app.get("/health")
async def health():
    return {"status": "healthy", "model_loaded": predictor.is_loaded}
