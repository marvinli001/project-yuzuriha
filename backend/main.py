from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from typing import List, Dict, Any, Optional
import logging
from datetime import datetime

from services.openai_service import OpenAIService
from services.milvus_service import MilvusService
from services.memory_service import MemoryService
from services.time_service import TimeService
from services.emotion_service import EmotionAnalyzer, EventClassifier
from models.chat_models import ChatRequest, ChatResponse, Message, HealthResponse, MemoryStatsResponse

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 创建 FastAPI 应用
app = FastAPI(
    title="Project Yuzuriha API",
    description="AI聊天助手后端服务，具备增强记忆能力、情绪分析和时间感知",
    version="2.0.0",
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
time_service = None
emotion_analyzer = None
event_classifier = None

@app.on_event("startup")
async def startup_event():
    """应用启动时初始化服务"""
    global openai_service, milvus_service, memory_service, time_service, emotion_analyzer, event_classifier
    
    try:
        logger.info("正在初始化增强服务...")
        
        # 初始化核心服务
        openai_service = OpenAIService()
        logger.info("✓ OpenAI 服务初始化成功")
        
        milvus_service = MilvusService()
        await milvus_service.initialize()
        logger.info("✓ Milvus 服务初始化成功")
        
        memory_service = MemoryService()
        logger.info("✓ 记忆服务初始化成功")
        
        time_service = TimeService()
        logger.info("✓ 时间服务初始化成功")
        
        emotion_analyzer = EmotionAnalyzer()
        event_classifier = EventClassifier()
        logger.info("✓ 情绪分析和事件分类服务初始化成功")
        
        logger.info("🚀 所有增强服务初始化完成")
        
    except Exception as e:
        logger.error(f"❌ 服务初始化失败: {e}")
        raise

@app.post("/api/chat", response_model=ChatResponse)
async def enhanced_chat(request: ChatRequest, background_tasks: BackgroundTasks):
    """增强的聊天处理"""
    try:
        logger.info(f"收到聊天请求: {request.message[:50]}...")
        
        # 1. 创建查询嵌入
        query_embedding = await openai_service.create_embedding(request.message)
        
        # 2. 分析用户消息
        user_emotion = emotion_analyzer.analyze_emotion(request.message)
        user_category, user_confidence = event_classifier.classify_event(request.message)
        
        # 3. 从SuperMemory检索相关记忆
        supermemory_memories = await memory_service.retrieve_relevant_memories(
            request.message, limit=3
        )
        
        # 4. 从Milvus搜索向量相似的记忆
        milvus_memories = await milvus_service.search_memories(
            query_embedding, 
            limit=3,
            emotion_weight_threshold=0.3 if user_emotion['emotion_weight'] > 0.5 else 0.0
        )
        
        # 5. 合并记忆
        all_memories = supermemory_memories + milvus_memories
        
        # 6. 转换历史消息格式
        conversation_history = [
            {'role': msg.role, 'content': msg.content} 
            for msg in request.history
        ]
        
        # 7. 生成AI回复
        response = await openai_service.generate_response(
            request.message,
            memories=all_memories,
            conversation_history=conversation_history
        )
        
        # 8. 后台存储记忆
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
                    "source": "supermemory"
                } for m in supermemory_memories
            ] + [
                {
                    "text": m.get("text", ""),
                    "score": m.get("score", 0.0),
                    "source": "milvus"
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
    """后台任务：存储对话记忆"""
    try:
        # 1. 存储到SuperMemory
        await memory_service.store_conversation_memory(user_message, ai_response)
        
        # 2. 分析AI回复
        ai_emotion = emotion_analyzer.analyze_emotion(ai_response)
        ai_category, ai_confidence = event_classifier.classify_event(ai_response)
        
        # 3. 确定交互类型
        interaction_type = memory_service._determine_interaction_type(user_category, ai_category)
        
        # 4. 存储用户消息到Milvus
        await milvus_service.store_memory(
            text=f"用户: {user_message}",
            embedding=query_embedding,
            emotion_weight=user_emotion['emotion_weight'],
            event_category=user_category,
            interaction_type=interaction_type
        )
        
        # 5. 为AI回复创建嵌入并存储
        ai_embedding = await openai_service.create_embedding(ai_response)
        await milvus_service.store_memory(
            text=f"助手: {ai_response}",
            embedding=ai_embedding,
            emotion_weight=ai_emotion['emotion_weight'],
            event_category=ai_category,
            interaction_type=interaction_type
        )
        
        logger.info("✓ 对话记忆存储完成")
        
    except Exception as e:
        logger.error(f"❌ 存储对话记忆失败: {e}")

@app.get("/api/memories/stats", response_model=MemoryStatsResponse)
async def get_memory_statistics(user_id: str = "marvinli001"):
    """获取记忆统计信息"""
    try:
        stats = await milvus_service.get_memory_stats(user_id)
        time_info = time_service.get_time_context()
        
        return MemoryStatsResponse(
            total_memories=stats['total_memories'],
            category_distribution=stats['category_distribution'],
            user_id=stats['user_id'],
            generated_at=time_info['current_time']
        )
    except Exception as e:
        logger.error(f"获取记忆统计错误: {e}")
        raise HTTPException(status_code=500, detail=f"获取统计信息时发生错误: {str(e)}")

@app.get("/api/memories/category/{category}")
async def get_memories_by_category(category: str, user_id: str = "marvinli001", limit: int = 10):
    """根据类别获取记忆"""
    try:
        memories = await milvus_service.get_memories_by_category(category, user_id, limit)
        return {"memories": memories, "count": len(memories), "category": category}
    except Exception as e:
        logger.error(f"按类别获取记忆错误: {e}")
        raise HTTPException(status_code=500, detail=f"获取记忆时发生错误: {str(e)}")

@app.delete("/api/memories/clear")
async def clear_all_memories(user_id: str = "marvinli001"):
    """清空所有记忆"""
    try:
        # 清空Milvus记忆
        milvus_success = await milvus_service.clear_memories(user_id)
        
        # 清空SuperMemory记忆
        supermemory_success = await memory_service.clear_all_memories(user_id)
        
        return {
            "success": milvus_success and supermemory_success,
            "message": "记忆已清空",
            "milvus_cleared": milvus_success,
            "supermemory_cleared": supermemory_success
        }
    except Exception as e:
        logger.error(f"清空记忆错误: {e}")
        raise HTTPException(status_code=500, detail=f"清空记忆时发生错误: {str(e)}")

@app.get("/health", response_model=HealthResponse)
async def enhanced_health_check():
    """增强的健康检查"""
    try:
        time_info = time_service.get_time_context()
        model_info = openai_service.get_model_info()
        
        services_status = {
            "openai": openai_service is not None,
            "milvus": milvus_service is not None and milvus_service.client is not None,
            "supermemory": memory_service is not None and memory_service.enabled,
            "time_service": time_service is not None,
            "emotion_analyzer": emotion_analyzer is not None,
            "event_classifier": event_classifier is not None
        }
        
        overall_status = "healthy" if all(services_status.values()) else "unhealthy"
        
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

@app.get("/")
async def root():
    """根路径"""
    time_info = time_service.get_time_context()
    return {
        "message": "Project Yuzuriha Enhanced API",
        "version": "2.0.0",
        "status": "running",
        "current_time": time_info['current_time'],
        "features": [
            "增强记忆系统",
            "情绪分析",
            "事件分类",
            "时间感知",
            "多源记忆检索"
        ]
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)