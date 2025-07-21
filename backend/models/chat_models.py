from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

class Message(BaseModel):
    id: str
    role: str  # "user" or "assistant"
    content: str
    timestamp: str

class ChatRequest(BaseModel):
    message: str
    history: List[Message] = []

class ChatResponse(BaseModel):
    response: str
    memory_stored: bool

class MemoryEntry(BaseModel):
    id: Optional[str] = None
    content: str
    timestamp: str
    type: str  # "conversation", "event", etc.
    metadata: dict = {}