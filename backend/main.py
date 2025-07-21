import asyncio
import logging
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, ConfigDict
from typing import List, Optional, Dict, Any

# 服务导入
from services.openai_service import OpenAIService
from services.milvus_service import MilvusService
from services.memory_service import MemoryService
from services.emotion_service import EmotionAnalyzer, EventClassifier
from services.time_service import TimeService

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 全局服务实例
openai_service = None
milvus_service = None
memory_service = None
emotion_analyzer = None
event_classifier = None
time_service = None

# Pydantic 模型 - 修复 model_info 冲突
class Message(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    message: str
    history: List[Message] = []

class ChatResponse(BaseModel):
    response: str
    memories: List[Dict[str, Any]] = []

class HealthResponse(BaseModel):
    model_config = ConfigDict(protected_namespaces=())  # 修复 Pydantic 警告
    
    status: str
    timestamp: str
    services: Dict[str, bool]
    model_info: Dict[str, str]
    timezone: str

@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    global openai_service, milvus_service, memory_service, emotion_analyzer, event_classifier, time_service
    
    try:
        logger.info("正在初始化增强服务...")
        
        # 1. 初始化 OpenAI 服务 (无需调用 initialize)
        openai_service = OpenAIService()
        logger.info("✓ OpenAI 服务初始化成功")
        
        # 2. 初始化 Milvus 服务
        milvus_service = MilvusService()
        await milvus_service.initialize()
        logger.info("✓ Milvus 服务初始化成功")
        
        # 3. 初始化记忆服务（使用新的纯 Milvus 版本）
        memory_service = MemoryService()
        memory_service.set_milvus_service(milvus_service)
        logger.info("✓ 记忆服务初始化成功")
        
        # 4. 初始化时间服务
        time_service = TimeService()
        logger.info("✓ 时间服务初始化成功")
        
        # 5. 初始化情绪分析和事件分类
        emotion_analyzer = EmotionAnalyzer()
        event_classifier = EventClassifier()
        logger.info("✓ 情绪分析和事件分类服务初始化成功")
        
        logger.info("🚀 所有服务初始化完成")
        
        yield
        
    except Exception as e:
        logger.error(f"❌ 服务初始化失败: {e}")
        raise
    finally:
        logger.info("🔄 正在关闭服务...")

# 创建 FastAPI 应用
app = FastAPI(
    title="Project Yuzuriha Enhanced API",
    description="AI聊天服务 with Enhanced Memory (Milvus Only)",
    version="2.2.0",
    lifespan=lifespan
)

# 配置 CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/api/chat", response_model=ChatResponse)
async def enhanced_chat(request: ChatRequest, background_tasks: BackgroundTasks):
    """增强聊天接口 - 纯 Milvus 版本"""
    try:
        logger.info(f"收到聊天请求: {request.message[:50]}...")
        
        # 1. 创建查询嵌入
        query_embedding = await openai_service.create_embedding(request.message)
        
        # 2. 分析用户消息
        user_emotion = emotion_analyzer.analyze_emotion(request.message)
        user_category, user_confidence = event_classifier.classify_event(request.message)
        
        # 3. 从 Milvus 检索相关记忆 - 添加 user_id 参数
        milvus_memories = await memory_service.retrieve_relevant_memories(
            query=request.message,
            query_embedding=query_embedding,
            limit=5,
            user_id="marvinli001"  # 添加这个参数
        )
        logger.info(f"从 Milvus 检索到 {len(milvus_memories)} 个记忆")
        
        # 4. 转换历史消息格式
        conversation_history = [
            {'role': msg.role, 'content': msg.content} 
            for msg in request.history
        ]
        
        # 5. 生成AI回复
        response = await openai_service.generate_response(
            request.message,
            memories=milvus_memories,
            conversation_history=conversation_history
        )
        
        # 6. 后台存储记忆
        background_tasks.add_task(
            store_conversation_memories,
            request.message,
            response,
            query_embedding,
            user_emotion,
            user_category,
            user_confidence
        )
        
        logger.info("✓ 聊天请求处理成功")
        
        return ChatResponse(
            response=response,
            memories=[
                {
                    "text": m.get("content", ""),
                    "score": m.get("relevance_score", 0.0),
                    "source": "milvus",
                    "timestamp": m.get("timestamp", 0),
                    "category": m.get("category", "general"),
                    "emotion_weight": m.get("emotion_weight", 0.0)
                } for m in milvus_memories
            ]
        )
        
    except Exception as e:
        logger.error(f"❌ 聊天处理错误: {e}")
        raise HTTPException(status_code=500, detail=f"处理聊天请求时发生错误: {str(e)}")

async def store_conversation_memories(
    user_message: str,
    ai_response: str,
    query_embedding: List[float],
    user_emotion: Dict[str, float],
    user_category: str,
    user_confidence: float
):
    """后台任务：存储对话记忆到 Milvus"""
    try:
        # 1. 分析AI回复
        ai_emotion = emotion_analyzer.analyze_emotion(ai_response)
        ai_category, ai_confidence = event_classifier.classify_event(ai_response)
        
        # 2. 确定交互类型
        interaction_type = memory_service._determine_interaction_type(user_category, ai_category)
        
        # 3. 存储用户消息到Milvus
        milvus_user_success = await milvus_service.store_memory(
            text=f"用户: {user_message}",
            embedding=query_embedding,
            emotion_weight=user_emotion.get('emotion_weight', 0.5),
            event_category=user_category,
            interaction_type=interaction_type
        )
        
        # 4. 为AI回复创建嵌入并存储
        ai_embedding = await openai_service.create_embedding(ai_response)
        milvus_ai_success = await milvus_service.store_memory(
            text=f"助手: {ai_response}",
            embedding=ai_embedding,
            emotion_weight=ai_emotion.get('emotion_weight', 0.5),
            event_category=ai_category,
            interaction_type=interaction_type
        )
        
        logger.info(f"✓ 记忆存储完成 - Milvus用户: {'✓' if milvus_user_success else '✗'}, MilvusAI: {'✓' if milvus_ai_success else '✗'}")
        
    except Exception as e:
        logger.error(f"存储对话记忆时发生错误: {e}")

@app.get("/health", response_model=HealthResponse)
async def enhanced_health_check():
    """增强的健康检查 - 移除 SuperMemory"""
    try:
        time_info = time_service.get_time_context()
        model_info = openai_service.get_model_info()
        
        services_status = {
            "openai": openai_service is not None,
            "milvus": milvus_service is not None and milvus_service.client is not None,
            "memory_service": memory_service is not None,
            "time_service": time_service is not None,
            "emotion_analyzer": emotion_analyzer is not None,
            "event_classifier": event_classifier is not None
        }
        
        overall_status = "healthy" if all([
            services_status["openai"],
            services_status["milvus"],
            services_status["memory_service"],
            services_status["time_service"],
            services_status["emotion_analyzer"],
            services_status["event_classifier"]
        ]) else "unhealthy"
        
        return HealthResponse(
            status=overall_status,
            timestamp=time_info['current_time'],
            services=services_status,
            model_info=model_info,
            timezone=time_info['timezone']
        )
    except Exception as e:
        logger.error(f"健康检查错误: {e}")
        raise HTTPException(status_code=500, detail=f"健康检查失败: {str(e)}")

@app.get("/api/stats")
async def get_memory_stats():
    """获取记忆统计信息"""
    try:
        stats = await memory_service.get_memory_stats()
        return {
            "status": "success",
            "data": stats,
            "backend": "milvus_only"
        }
    except Exception as e:
        logger.error(f"获取统计信息失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取统计信息失败: {str(e)}")

@app.get("/")
async def root():
    """根路径"""
    time_info = time_service.get_time_context()
    
    return {
        "message": "Project Yuzuriha Enhanced API",
        "version": "2.2.0",
        "status": "running",
        "current_time": time_info['current_time'],
        "memory_backend": "milvus_only",
        "supermemory_removed": True,
        "features": [
            "增强记忆系统 (纯Milvus)",
            "情绪分析",
            "事件分类", 
            "时间感知",
            "语义搜索",
            "Zilliz Cloud Milvus"
        ]
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)