from pydantic import BaseModel
from typing import List, Optional, Dict, Any

class Message(BaseModel):
    id: str
    role: str  # 'user' 或 'assistant'
    content: str
    timestamp: str

class ChatRequest(BaseModel):
    message: str
    history: List[Message] = []

class ChatResponse(BaseModel):
    response: str
    memories: Optional[List[Dict[str, Any]]] = None

class HealthResponse(BaseModel):
    status: str  # 'healthy' 或 'unhealthy'
    timestamp: str
    services: Dict[str, bool]
    model_info: Optional[Dict[str, str]] = None
    timezone: Optional[str] = None

class MemoryResult(BaseModel):
    text: str
    score: float
    timestamp: int
    user_id: str
    emotion_weight: float
    event_category: str
    interaction_type: str

class MemoryStatsResponse(BaseModel):
    total_memories: int
    category_distribution: Dict[str, int]
    user_id: str
    generated_at: str

class EmotionAnalysis(BaseModel):
    positive: float
    negative: float
    neutral: float
    compound: float
    emotion_weight: float

class EventClassification(BaseModel):
    category: str
    confidence: float
    complexity: float