from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from typing import List, Dict, Any, Optional
import logging
from datetime import datetime
from contextlib import asynccontextmanager

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

# 全局服务实例
openai_service = None
milvus_service = None
memory_service = None
time_service = None
emotion_analyzer = None
event_classifier = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
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
        logger.info(f"✓ SuperMemory 服务初始化{'成功' if memory_service.enabled else '失败（将使用模拟模式）'}")
        
        time_service = TimeService()
        logger.info("✓ 时间服务初始化成功")
        
        emotion_analyzer = EmotionAnalyzer()
        event_classifier = EventClassifier()
        logger.info("✓ 情绪分析和事件分类服务初始化成功")
        
        logger.info("🚀 所有增强服务初始化完成")
        yield
        
    except Exception as e:
        logger.error(f"服务初始化失败: {e}")
        raise
    finally:
        logger.info("应用关闭，清理资源...")

# 创建FastAPI应用
app = FastAPI(
    title="Project Yuzuriha - Enhanced AI Chat API",
    description="基于OpenAI、Milvus和SuperMemory的增强AI聊天API",
    version="2.0.0",
    lifespan=lifespan
)

# 添加CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/api/chat", response_model=ChatResponse)
async def enhanced_chat(request: ChatRequest, background_tasks: BackgroundTasks):
    """增强的聊天处理 - 添加更好的错误处理"""
    try:
        logger.info(f"收到聊天请求: {request.message[:50]}...")
        
        # 验证输入
        if not request.message or not request.message.strip():
            raise HTTPException(status_code=400, detail="消息内容不能为空")
        
        # 1. 创建查询嵌入
        try:
            query_embedding = await openai_service.create_embedding(request.message)
        except Exception as e:
            logger.error(f"创建嵌入失败: {e}")
            query_embedding = [0.0] * 1536  # 使用默认嵌入
        
        # 2. 分析用户消息
        try:
            user_emotion = emotion_analyzer.analyze_emotion(request.message)
            user_category, user_confidence = event_classifier.classify_event(request.message)
        except Exception as e:
            logger.error(f"情绪分析失败: {e}")
            user_emotion = {'emotion_weight': 0.5}
            user_category, user_confidence = 'general', 0.5
        
        # 3. 从SuperMemory检索相关记忆
        supermemory_memories = []
        try:
            supermemory_memories = await memory_service.retrieve_relevant_memories(
                request.message, limit=3
            )
            logger.info(f"从SuperMemory检索到 {len(supermemory_memories)} 个记忆")
        except Exception as e:
            logger.warning(f"SuperMemory检索失败，继续使用Milvus: {e}")

        # 4. 从Milvus搜索向量相似的记忆
        milvus_memories = []
        try:
            milvus_memories = await milvus_service.search_memories(
                query_embedding, 
                limit=3,
                emotion_weight_threshold=0.3 if user_emotion.get('emotion_weight', 0) > 0.5 else 0.0
            )
            logger.info(f"从Milvus检索到 {len(milvus_memories)} 个记忆")
        except Exception as e:
            logger.error(f"Milvus搜索失败: {e}")
        
        # 5. 合并记忆
        all_memories = supermemory_memories + milvus_memories
        
        # 6. 转换历史消息格式
        conversation_history = []
        try:
            conversation_history = [
                {'role': msg.role, 'content': msg.content} 
                for msg in (request.history or [])
                if msg.content and msg.content.strip()
            ]
        except Exception as e:
            logger.error(f"处理历史消息失败: {e}")
        
        # 7. 生成AI回复
        try:
            response = await openai_service.generate_response(
                request.message,
                memories=all_memories,
                conversation_history=conversation_history
            )
            
            # 验证响应
            if not response or not response.strip():
                response = "抱歉，我现在无法生成回复。请稍后再试。"
                
        except Exception as e:
            logger.error(f"生成回复失败: {e}")
            response = "抱歉，发送消息时出现错误。请检查网络连接并重试。"
        
        # 8. 后台存储记忆
        try:
            background_tasks.add_task(
                store_conversation_memories,
                request.message,
                response,
                query_embedding,
                user_emotion,
                user_category,
                user_confidence
            )
        except Exception as e:
            logger.error(f"添加后台任务失败: {e}")
        
        logger.info("✓ 聊天请求处理成功")
        
        # 构建返回的记忆列表
        response_memories = []
        try:
            response_memories = [
                {
                    "text": m.get("content", ""),
                    "score": m.get("relevance_score", 0.0),
                    "source": "supermemory",
                    "timestamp": m.get("timestamp", 0)
                } for m in supermemory_memories
            ] + [
                {
                    "text": m.get("text", ""),
                    "score": m.get("score", 0.0),
                    "source": "milvus",
                    "timestamp": m.get("timestamp", 0)
                } for m in milvus_memories
            ]
        except Exception as e:
            logger.error(f"构建记忆响应失败: {e}")
            response_memories = []
        
        return ChatResponse(
            response=response,
            memories=response_memories
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 聊天处理错误: {e}")
        return ChatResponse(
            response="抱歉，处理您的请求时出现了问题。请稍后再试。",
            memories=[]
        )

async def store_conversation_memories(
    user_message: str,
    ai_response: str,
    query_embedding: List[float],
    user_emotion: Dict[str, float],
    user_category: str,
    user_confidence: float
):
    """后台任务：存储对话记忆 - 改进错误处理"""
    try:
        # 1. 存储到SuperMemory
        supermemory_success = False
        try:
            supermemory_success = await memory_service.store_conversation_memory(
                user_message, ai_response
            )
        except Exception as e:
            logger.error(f"SuperMemory存储失败: {e}")
        
        logger.info(f"SuperMemory存储: {'成功' if supermemory_success else '失败'}")
        
        # 2. 分析AI回复
        try:
            ai_emotion = emotion_analyzer.analyze_emotion(ai_response)
            ai_category, ai_confidence = event_classifier.classify_event(ai_response)
        except Exception as e:
            logger.error(f"AI回复分析失败: {e}")
            ai_emotion = {'emotion_weight': 0.5}
            ai_category, ai_confidence = 'general', 0.5
        
        # 3. 确定交互类型
        try:
            interaction_type = memory_service._determine_interaction_type(user_category, ai_category)
        except Exception as e:
            logger.error(f"确定交互类型失败: {e}")
            interaction_type = 'general_conversation'
        
        # 4. 存储用户消息到Milvus
        milvus_user_success = False
        try:
            milvus_user_success = await milvus_service.store_memory(
                text=f"用户: {user_message}",
                embedding=query_embedding,
                emotion_weight=user_emotion.get('emotion_weight', 0.5),
                event_category=user_category,
                interaction_type=interaction_type
            )
        except Exception as e:
            logger.error(f"Milvus用户消息存储失败: {e}")
        
        # 5. 为AI回复创建嵌入并存储
        milvus_ai_success = False
        try:
            ai_embedding = await openai_service.create_embedding(ai_response)
            milvus_ai_success = await milvus_service.store_memory(
                text=f"助手: {ai_response}",
                embedding=ai_embedding,
                emotion_weight=ai_emotion.get('emotion_weight', 0.5),
                event_category=ai_category,
                interaction_type=interaction_type
            )
        except Exception as e:
            logger.error(f"Milvus AI回复存储失败: {e}")
        
        logger.info(f"✓ 记忆存储完成 - SuperMemory: {'✓' if supermemory_success else '✗'}, Milvus用户: {'✓' if milvus_user_success else '✗'}, MilvusAI: {'✓' if milvus_ai_success else '✗'}")
        
    except Exception as e:
        logger.error(f"存储对话记忆时发生错误: {e}")

# 其余路由保持不变...
@app.get("/health", response_model=HealthResponse)
async def enhanced_health_check():
    """增强的健康检查"""
    try:
        time_info = time_service.get_time_context()
        model_info = openai_service.get_model_info()
        supermemory_info = memory_service.get_client_info()
        
        services_status = {
            "openai": openai_service is not None,
            "milvus": milvus_service is not None and milvus_service.client is not None,
            "supermemory": memory_service is not None and memory_service.enabled,
            "supermemory_client": supermemory_info['client_available'],
            "time_service": time_service is not None,
            "emotion_analyzer": emotion_analyzer is not None,
            "event_classifier": event_classifier is not None
        }
        
        overall_status = "healthy" if all([
            services_status["openai"],
            services_status["milvus"],
            services_status["time_service"],
            services_status["emotion_analyzer"],
            services_status["event_classifier"]
        ]) else "unhealthy"
        
        return HealthResponse(
            status=overall_status,
            timestamp=datetime.now().isoformat(),
            services=services_status,
            time_info=time_info,
            model_info=model_info,
            supermemory_info=supermemory_info
        )
    except Exception as e:
        logger.error(f"健康检查失败: {e}")
        return HealthResponse(
            status="error",
            timestamp=datetime.now().isoformat(),
            services={},
            time_info={},
            model_info={},
            supermemory_info={}
        )

@app.get("/api/memories/stats", response_model=MemoryStatsResponse)
async def get_memory_stats():
    """获取记忆统计"""
    try:
        milvus_stats = await milvus_service.get_memory_stats()
        return MemoryStatsResponse(**milvus_stats)
    except Exception as e:
        logger.error(f"获取记忆统计失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取记忆统计失败: {str(e)}")

@app.get("/")
async def root():
    """根路径"""
    return {
        "message": "Project Yuzuriha - Enhanced AI Chat API",
        "version": "2.0.0",
        "status": "running",
        "docs": "/docs"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)