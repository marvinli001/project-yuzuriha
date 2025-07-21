from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import os
import httpx
import asyncio
from datetime import datetime, timezone
import logging

from services.openai_service import OpenAIService
from services.milvus_service import MilvusService
from services.memory_service import MemoryService
from models.chat_models import ChatRequest, ChatResponse, Message, HealthResponse

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 创建 FastAPI 应用
app = FastAPI(
    title="Project Yuzuriha API",
    description="AI聊天助手后端服务，具备记忆能力",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS 中间件配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境中应该指定具体域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 全局服务实例
openai_service = None
milvus_service = None
memory_service = None

@app.on_event("startup")
async def startup_event():
    """应用启动时初始化服务"""
    global openai_service, milvus_service, memory_service
    
    try:
        logger.info("正在初始化服务...")
        
        # 初始化 OpenAI 服务
        openai_service = OpenAIService()
        logger.info("OpenAI 服务初始化成功")
        
        # 初始化 Milvus 服务
        milvus_service = MilvusService()
        await milvus_service.initialize()
        logger.info("Milvus 服务初始化成功")
        
        # 初始化记忆服务
        memory_service = MemoryService()
        logger.info("记忆服务初始化成功")
        
        logger.info("所有服务初始化完成")
        
    except Exception as e:
        logger.error(f"服务初始化失败: {e}")
        raise

def build_context(message: str, history: List[Message], memories: List[Dict[str, Any]] = None) -> str:
    """构建对话上下文"""
    current_time = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    
    context_parts = [
        f"当前时间: {current_time}",
        f"用户: marvinli001",
        "",
        "你是 Yuzuriha，一个拥有记忆能力的AI助手。",
        "你可以记住过往的对话内容，并使用这些记忆来提供更好的回复。",
        "请用中文回复，保持友好和有帮助的语调。",
        ""
    ]
    
    # 添加相关记忆
    if memories:
        context_parts.append("相关的历史记忆:")
        for i, memory in enumerate(memories[:3], 1):
            context_parts.append(f"{i}. {memory.get('text', '')}")
        context_parts.append("")
    
    # 添加最近的对话历史
    if history:
        context_parts.append("最近的对话:")
        for msg in history[-5:]:  # 最近5条消息
            role = "用户" if msg.role == "user" else "助手"
            context_parts.append(f"{role}: {msg.content}")
        context_parts.append("")
    
    context_parts.append(f"用户当前消息: {message}")
    
    return "\n".join(context_parts)

@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """处理聊天请求"""
    try:
        logger.info(f"收到聊天请求: {request.message[:50]}...")
        
        # 创建消息嵌入用于检索相关记忆
        query_embedding = await openai_service.create_embedding(request.message)
        
        # 从向量数据库搜索相关记忆
        memories = await milvus_service.search_memories(query_embedding, limit=3)
        
        # 构建对话上下文
        context = build_context(request.message, request.history, memories)
        
        # 生成AI回复
        response = await openai_service.generate_response(context)
        
        # 存储用户消息和AI回复到记忆系统
        user_msg_embedding = await openai_service.create_embedding(request.message)
        await milvus_service.store_memory(request.message, user_msg_embedding)
        
        ai_msg_embedding = await openai_service.create_embedding(response)
        await milvus_service.store_memory(f"AI回复: {response}", ai_msg_embedding)
        
        # 同时存储到SuperMemory（如果可用）
        if memory_service.enabled:
            event_data = {
                "user_message": request.message,
                "ai_response": response,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "user_id": "marvinli001"
            }
            await memory_service.store_event(event_data)
        
        logger.info("聊天请求处理成功")
        
        return ChatResponse(
            response=response,
            memories=[{"text": m.get("text"), "score": m.get("score")} for m in memories]
        )
        
    except Exception as e:
        logger.error(f"聊天处理错误: {e}")
        raise HTTPException(status_code=500, detail=f"处理聊天请求时发生错误: {str(e)}")

@app.get("/api/memories")
async def get_memories(limit: int = 10):
    """获取存储的记忆"""
    try:
        # 这里可以添加获取记忆的逻辑
        return {"memories": [], "count": 0}
    except Exception as e:
        logger.error(f"获取记忆错误: {e}")
        raise HTTPException(status_code=500, detail=f"获取记忆时发生错误: {str(e)}")

@app.delete("/api/memories")
async def clear_memories():
    """清空所有记忆"""
    try:
        success = await milvus_service.clear_memories()
        if memory_service.enabled:
            await memory_service.clear_all_memories()
        
        return {"success": success, "message": "记忆已清空"}
    except Exception as e:
        logger.error(f"清空记忆错误: {e}")
        raise HTTPException(status_code=500, detail=f"清空记忆时发生错误: {str(e)}")

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """健康检查"""
    try:
        services_status = {
            "openai": openai_service is not None,
            "milvus": milvus_service is not None,
            "supermemory": memory_service is not None and memory_service.enabled
        }
        
        overall_status = "healthy" if all(services_status.values()) else "unhealthy"
        
        return HealthResponse(
            status=overall_status,
            timestamp=datetime.now(timezone.utc).isoformat(),
            services=services_status
        )
    except Exception as e:
        logger.error(f"健康检查错误: {e}")
        raise HTTPException(status_code=500, detail=f"健康检查失败: {str(e)}")

@app.get("/")
async def root():
    """根路径"""
    return {
        "message": "Project Yuzuriha API",
        "version": "1.0.0",
        "status": "running"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)