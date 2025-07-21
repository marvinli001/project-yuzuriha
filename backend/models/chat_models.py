from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime

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

class MemoryResult(BaseModel):
    text: str
    score: float
    timestamp: int
    user_id: str