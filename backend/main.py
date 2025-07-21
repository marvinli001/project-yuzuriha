from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import os
import httpx
import asyncio
from datetime import datetime
import logging

from services.openai_service import OpenAIService
from services.milvus_service import MilvusService
from services.memory_service import MemoryService
from models.chat_models import ChatRequest, ChatResponse, Message

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Project Yuzuriha Backend",
    description="AI Chat Assistant with Memory",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify your frontend domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize services
openai_service = OpenAIService()
milvus_service = MilvusService()
memory_service = MemoryService()

@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    try:
        await milvus_service.initialize()
        logger.info("Services initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize services: {e}")

@app.get("/")
async def root():
    return {"message": "Project Yuzuriha Backend API", "status": "running"}

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "services": {
            "openai": await openai_service.health_check(),
            "milvus": await milvus_service.health_check(),
            "memory": await memory_service.health_check()
        }
    }

@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Main chat endpoint"""
    try:
        current_time = datetime.utcnow().isoformat()
        
        # 1. Get relevant memories from vector database
        relevant_memories = await milvus_service.search_similar(
            query=request.message,
            limit=5
        )
        
        # 2. Build context with memories and chat history
        context = await _build_context(
            message=request.message,
            history=request.history,
            memories=relevant_memories,
            current_time=current_time
        )
        
        # 3. Generate response using OpenAI
        response = await openai_service.generate_response(
            message=request.message,
            context=context
        )
        
        # 4. Store conversation in memory asynchronously
        asyncio.create_task(
            memory_service.store_conversation(
                user_message=request.message,
                assistant_response=response,
                timestamp=current_time
            )
        )
        
        # 5. Store embeddings in vector database asynchronously
        asyncio.create_task(
            milvus_service.store_conversation(
                user_message=request.message,
                assistant_response=response,
                timestamp=current_time
            )
        )
        
        return ChatResponse(
            response=response,
            memory_stored=True
        )
        
    except Exception as e:
        logger.error(f"Error in chat endpoint: {e}")
        raise HTTPException(status_code=500, detail=str(e))

async def _build_context(
    message: str,
    history: List[Message],
    memories: List[Dict[str, Any]],
    current_time: str
) -> str:
    """Build context for the AI model"""
    
    context_parts = [
        f"Current time (UTC): {current_time}",
        f"Current user: marvinli001",
        "",
        "You are Yuzuriha, an AI assistant with memory capabilities.",
        "You can remember past conversations and use that context to provide better responses.",
        ""
    ]
    
    # Add relevant memories if found
    if memories:
        context_parts.append("Relevant past memories:")
        for i, memory in enumerate(memories[:3], 1):  # Limit to top 3 memories
            context_parts.append(f"{i}. {memory.get('text', '')}")
        context_parts.append("")
    
    # Add recent conversation history
    if history:
        context_parts.append("Recent conversation:")
        for msg in history[-5:]:  # Last 5 messages
            role = "User" if msg.role == "user" else "Assistant"
            context_parts.append(f"{role}: {msg.content}")
        context_parts.append("")
    
    context_parts.append(f"Current user message: {message}")
    
    return "\n".join(context_parts)

@app.get("/api/memories")
async def get_memories(limit: int = 50):
    """Get stored memories"""
    try:
        memories = await memory_service.get_recent_memories(limit=limit)
        return {"memories": memories}
    except Exception as e:
        logger.error(f"Error getting memories: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/memories")
async def clear_memories():
    """Clear all stored memories"""
    try:
        await memory_service.clear_memories()
        await milvus_service.clear_collection()
        return {"message": "All memories cleared successfully"}
    except Exception as e:
        logger.error(f"Error clearing memories: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)