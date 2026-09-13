from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime


# ── Auth / User ──

class LoginRequest(BaseModel):
    email: str
    password: str


class UserCreateRequest(BaseModel):
    email: str
    password: str
    full_name: str
    username: str
    role: str = "pekerja"


class UserUpdateRequest(BaseModel):
    full_name: Optional[str] = None
    username: Optional[str] = None
    role: Optional[str] = None
    password: Optional[str] = None


class UserResponse(BaseModel):
    id: str
    email: str
    username: str
    full_name: str
    role: str
    created_at: Optional[str] = None


# ── Prediction ──

class PredictionResponse(BaseModel):
    id: str
    filename: str
    image_url: str
    is_defect: bool
    defect_type: str
    confidence: float
    model_version: str
    created_at: str
    all_predictions: Optional[dict] = None


# ── History / Stats ──

class ScanHistoryItem(BaseModel):
    id: str
    filename: str
    image_path: str
    is_defect: bool
    defect_type: str
    confidence: float
    created_at: str
    user_id: str
    worker_name: Optional[str] = None


class StatsResponse(BaseModel):
    total_scans: int
    total_defects: int
    total_normal: int
    defect_rate: float


class MessageResponse(BaseModel):
    message: str
