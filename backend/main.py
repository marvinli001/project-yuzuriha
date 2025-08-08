import asyncio
import logging
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, BackgroundTasks, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict
from typing import List, Optional, Dict, Any
import uuid
import aiofiles
import openai

# 服务导入
from services.openai_service import OpenAIService
from services.milvus_service import MilvusService
from services.memory_service import MemoryService
from services.emotion_service import EmotionAnalyzer, EventClassifier
from services.time_service import TimeService
from services.d1_service import D1Service
from app.routes.chat_sessions import router as chat_sessions_router

# 新增：导入鉴权模块
from auth.api_auth import require_api_key

# 新增：导入 D1 模型
from models.d1_models import (
    ChatSession, ChatMessage, ChatSessionWithMessages,
    CreateSessionRequest, UpdateSessionRequest, AddMessageRequest,
    SessionsResponse, MessagesResponse, SessionResponse, MessageResponse,
    SearchMessagesResponse, D1StatsResponse, MigrationData, ApiResponse
)

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
d1_service = None

# 配置上传目录
UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# 允许的文件类型
ALLOWED_EXTENSIONS = {
    'image': {'png', 'jpg', 'jpeg', 'gif', 'webp'},
    'document': {'pdf', 'txt', 'doc', 'docx'},
    'audio': {'mp3', 'wav', 'ogg', 'm4a', 'flac', 'webm'}
}

# Pydantic 模型 - 保持现有的 + 添加新的
class Message(BaseModel):
    role: str
    content: str

class UploadedFile(BaseModel):
    id: str
    filename: str
    type: str
    size: int
    path: str

class ChatRequest(BaseModel):
    message: str
    history: List[Message] = []
    files: List[UploadedFile] = []  # 新增文件字段
    session_id: Optional[str] = None  # 新增：可选的会话ID

class ChatResponse(BaseModel):
    response: str
    memories: List[Dict[str, Any]] = []

class HealthResponse(BaseModel):
    model_config = ConfigDict(protected_namespaces=())
    
    status: str
    timestamp: str
    services: Dict[str, bool]
    model_info: Dict[str, str]
    timezone: str

class FileUploadResponse(BaseModel):
    files: List[UploadedFile]

class TranscriptionResponse(BaseModel):
    text: str
    success: bool

# 工具函数
def get_file_type(filename: str) -> str:
    ext = filename.lower().split('.')[-1]
    for file_type, extensions in ALLOWED_EXTENSIONS.items():
        if ext in extensions:
            return file_type
    return 'other'

@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    global openai_service, milvus_service, memory_service, emotion_analyzer, event_classifier, time_service, d1_service
    
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
        
        # 6. 配置 OpenAI (为语音转文本)
        openai.api_key = os.getenv('OPENAI_API_KEY')
        logger.info("✓ OpenAI 语音服务配置成功")
        
        # 7. 初始化 D1 服务
        d1_service = D1Service()
        if d1_service.is_enabled():
            logger.info("✓ D1 服务初始化成功")
        else:
            logger.warning("⚠ D1 服务配置不完整，将使用本地存储模式")
        
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
    description="AI聊天服务 with Enhanced Memory (Milvus Only) + File Upload + Voice",
    version="2.3.0",
    lifespan=lifespan
)

# 新增：挂载 D1 Chat 路由（chat_sessions.py）
app.include_router(chat_sessions_router)

# 配置 CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 静态文件服务 (用于文件上传)
app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")

# === 新增的文件上传路由 ===
@app.post("/api/upload", response_model=FileUploadResponse, dependencies=[require_api_key()])
async def upload_files(files: List[UploadFile] = File(...)):
    """文件上传接口"""
    uploaded_files = []
    
    for file in files:
        if file.size > 10 * 1024 * 1024:  # 10MB limit
            raise HTTPException(status_code=413, detail=f"File {file.filename} is too large")
        
        # 生成唯一文件名
        file_id = str(uuid.uuid4())
        file_ext = file.filename.split('.')[-1] if '.' in file.filename else ''
        safe_filename = f"{file_id}.{file_ext}" if file_ext else file_id
        file_path = os.path.join(UPLOAD_DIR, safe_filename)
        
        # 保存文件
        async with aiofiles.open(file_path, 'wb') as f:
            content = await file.read()
            await f.write(content)
        
        uploaded_files.append(UploadedFile(
            id=file_id,
            filename=file.filename,
            type=get_file_type(file.filename),
            size=file.size,
            path=file_path
        ))
    
    logger.info(f"上传了 {len(uploaded_files)} 个文件")
    return FileUploadResponse(files=uploaded_files)

# === 新增的语音转文本路由 ===
@app.post("/api/transcribe", response_model=TranscriptionResponse, dependencies=[require_api_key()])
async def transcribe_audio(audio: UploadFile = File(...)):
    """语音转文本接口"""
    if not audio.content_type or not audio.content_type.startswith('audio/'):
        raise HTTPException(status_code=400, detail="File must be an audio file")
    
    if audio.size > 25 * 1024 * 1024:  # 25MB limit for Whisper API
        raise HTTPException(status_code=413, detail="Audio file is too large")
    
    try:
        import tempfile
        
        # 创建临时文件
        with tempfile.NamedTemporaryFile(delete=False, suffix='.wav') as tmp_file:
            content = await audio.read()
            tmp_file.write(content)
            tmp_file.flush()
            
            # 使用 OpenAI Whisper API 进行转录
            with open(tmp_file.name, 'rb') as audio_file:
                client = openai.OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
                transcript = client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file,
                    language="zh"  # 指定中文，可根据需要调整
                )
        
        # 删除临时文件
        os.unlink(tmp_file.name)
        
        logger.info(f"语音转文本成功: {transcript.text[:50]}...")
        return TranscriptionResponse(
            text=transcript.text,
            success=True
        )
        
    except Exception as e:
        # 确保临时文件被删除
        if 'tmp_file' in locals():
            try:
                os.unlink(tmp_file.name)
            except:
                pass
        
        logger.error(f"语音转文本失败: {e}")
        raise HTTPException(status_code=500, detail=f"Transcription failed: {str(e)}")

# === 修改的聊天接口（支持文件） ===
@app.post("/api/chat", response_model=ChatResponse, dependencies=[require_api_key()])
async def enhanced_chat(request: ChatRequest, background_tasks: BackgroundTasks):
    """增强聊天接口 - 纯 Milvus 版本 + 文件支持"""
    try:
        logger.info(f"收到聊天请求: {request.message[:50]}...")
        
        # 处理附件信息
        file_context = ""
        if request.files:
            file_info = []
            for file in request.files:
                file_info.append(f"- {file.filename} ({file.type}, {file.size} bytes)")
            file_context = f"\n\n用户上传了以下附件：\n" + "\n".join(file_info)
            logger.info(f"包含 {len(request.files)} 个附件")
        
        # 1. 创建查询嵌入
        query_text = request.message + file_context
        query_embedding = await openai_service.create_embedding(query_text)
        
        # 2. 情绪分析
        user_emotion = emotion_analyzer.analyze_emotion(request.message)
        user_category, user_confidence = event_classifier.classify_event(request.message)
        
        # 3. 从 Milvus 检索相关记忆
        milvus_memories = await memory_service.retrieve_relevant_memories(
            query=query_text,  # 添加 query 参数
            query_embedding=query_embedding,
            limit=5
        )
        logger.info(f"从 Milvus 检索到 {len(milvus_memories)} 个记忆")
        
        # 4. 转换历史消息格式
        conversation_history = [
            {'role': msg.role, 'content': msg.content} 
            for msg in request.history
        ]
        
        # 5. 生成AI回复（包含文件上下文）
        enhanced_message = query_text  # 包含文件信息的消息
        response = await openai_service.generate_response(
            enhanced_message,
            memories=milvus_memories,
            conversation_history=conversation_history
        )
        
        # 6. 后台存储记忆
        background_tasks.add_task(
            store_conversation_memories,
            enhanced_message,  # 存储包含文件信息的消息
            response,
            query_embedding,
            user_emotion,
            user_category,
            user_confidence,
            request.session_id  # 传递会话ID
        )
        
        logger.info(f"聊天处理完成，生成回复长度: {len(response)}")
        
        return ChatResponse(
            response=response,
            memories=milvus_memories
        )
        
    except Exception as e:
        logger.error(f"聊天处理错误: {e}")
        raise HTTPException(status_code=500, detail=f"聊天处理失败: {str(e)}")

# 在现有的 @app.post("/api/chat") 之后添加
@app.post("/chat", response_model=ChatResponse)
async def chat_legacy(request: ChatRequest, background_tasks: BackgroundTasks):
    """兼容旧版本的聊天接口"""
    return await enhanced_chat(request, background_tasks)
# === 保持现有的其他路由 ===
async def store_conversation_memories(
    user_message: str,
    ai_response: str,
    query_embedding: List[float],
    user_emotion: Dict[str, float],
    user_category: str,
    user_confidence: float,
    session_id: str = None  # 新增：会话ID参数
):
    """存储对话记忆到 Milvus 和 D1（双写）"""
    try:
        # 1. 存储到 Milvus（原有逻辑）
        # 存储用户消息
        await milvus_service.store_memory(
            text=user_message,
            embedding=query_embedding,
            user_id="marvinli001",
            emotion_weight=user_emotion.get('emotion_weight', 0.0),
            event_category=user_category,
            interaction_type="user_message"
        )
        
        # 存储 AI 回复
        response_embedding = await openai_service.create_embedding(ai_response)
        await milvus_service.store_memory(
            text=ai_response,
            embedding=response_embedding,
            user_id="marvinli001",
            emotion_weight=0.7,  # AI回复的默认情绪权重
            event_category="response",
            interaction_type="ai_response"
        )
        
        logger.info("对话记忆存储到 Milvus 完成")
        
        # 2. 存储到 D1（新增逻辑）
        if d1_service and d1_service.is_enabled() and session_id:
            try:
                # 添加用户消息到 D1
                await d1_service.add_chat_message(session_id, "user", user_message)
                # 添加 AI 回复到 D1
                await d1_service.add_chat_message(session_id, "assistant", ai_response)
                logger.info("对话记忆存储到 D1 完成")
            except Exception as d1_error:
                logger.warning(f"D1 存储失败，但 Milvus 存储成功: {d1_error}")
        
    except Exception as e:
        logger.error(f"存储对话记忆失败: {e}")

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
            "event_classifier": event_classifier is not None,
            "d1_service": d1_service is not None and d1_service.is_enabled()
        }
        
        overall_status = "healthy" if all([
            services_status["openai"],
            services_status["milvus"],
            services_status["memory_service"],
            services_status["time_service"],
            services_status["emotion_analyzer"],
            services_status["event_classifier"]
            # D1 不是必需服务，不影响整体健康状态
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

# === 新增：D1 聊天历史 API 端点 ===

@app.get("/api/chat/sessions", response_model=SessionsResponse, dependencies=[require_api_key()])
async def get_chat_sessions(limit: int = 50):
    """获取所有聊天会话"""
    try:
        if not d1_service or not d1_service.is_enabled():
            raise HTTPException(status_code=503, detail="D1 服务不可用")
        
        sessions_data = await d1_service.get_chat_sessions(limit)
        sessions = [ChatSession(**session) for session in sessions_data]
        
        return SessionsResponse(
            sessions=sessions,
            total=len(sessions)
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取聊天会话失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取聊天会话失败: {str(e)}")

@app.post("/api/chat/sessions", response_model=SessionResponse, dependencies=[require_api_key()])
async def create_chat_session(request: CreateSessionRequest):
    """创建新的聊天会话"""
    try:
        if not d1_service or not d1_service.is_enabled():
            raise HTTPException(status_code=503, detail="D1 服务不可用")
        
        session_id = await d1_service.create_chat_session(request.title)
        session_data = await d1_service.get_chat_session(session_id)
        
        if not session_data:
            raise HTTPException(status_code=500, detail="创建会话后无法获取会话信息")
        
        session = ChatSession(**session_data)
        return SessionResponse(session=session)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"创建聊天会话失败: {e}")
        raise HTTPException(status_code=500, detail=f"创建聊天会话失败: {str(e)}")

@app.get("/api/chat/sessions/{session_id}", response_model=SessionResponse, dependencies=[require_api_key()])
async def get_chat_session(session_id: str):
    """获取特定聊天会话"""
    try:
        if not d1_service or not d1_service.is_enabled():
            raise HTTPException(status_code=503, detail="D1 服务不可用")
        
        session_data = await d1_service.get_chat_session(session_id)
        
        if not session_data:
            raise HTTPException(status_code=404, detail="会话不存在")
        
        session = ChatSession(**session_data)
        return SessionResponse(session=session)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取聊天会话失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取聊天会话失败: {str(e)}")

@app.put("/api/chat/sessions/{session_id}", response_model=SessionResponse, dependencies=[require_api_key()])
async def update_chat_session(session_id: str, request: UpdateSessionRequest):
    """更新聊天会话"""
    try:
        if not d1_service or not d1_service.is_enabled():
            raise HTTPException(status_code=503, detail="D1 服务不可用")
        
        success = await d1_service.update_chat_session(session_id, request.title)
        
        if not success:
            raise HTTPException(status_code=404, detail="会话不存在或更新失败")
        
        session_data = await d1_service.get_chat_session(session_id)
        session = ChatSession(**session_data)
        return SessionResponse(session=session)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新聊天会话失败: {e}")
        raise HTTPException(status_code=500, detail=f"更新聊天会话失败: {str(e)}")

@app.delete("/api/chat/sessions/{session_id}", response_model=ApiResponse, dependencies=[require_api_key()])
async def delete_chat_session(session_id: str):
    """删除聊天会话"""
    try:
        if not d1_service or not d1_service.is_enabled():
            raise HTTPException(status_code=503, detail="D1 服务不可用")
        
        success = await d1_service.delete_chat_session(session_id)
        
        if not success:
            raise HTTPException(status_code=404, detail="会话不存在或删除失败")
        
        return ApiResponse(
            success=True,
            message="会话删除成功"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除聊天会话失败: {e}")
        raise HTTPException(status_code=500, detail=f"删除聊天会话失败: {str(e)}")

@app.get("/api/chat/sessions/{session_id}/messages", response_model=MessagesResponse, dependencies=[require_api_key()])
async def get_chat_messages(session_id: str, limit: int = 100):
    """获取特定会话的消息"""
    try:
        if not d1_service or not d1_service.is_enabled():
            raise HTTPException(status_code=503, detail="D1 服务不可用")
        
        messages_data = await d1_service.get_chat_messages(session_id, limit)
        messages = [ChatMessage(**message) for message in messages_data]
        
        return MessagesResponse(
            messages=messages,
            total=len(messages)
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取聊天消息失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取聊天消息失败: {str(e)}")

@app.post("/api/chat/sessions/{session_id}/messages", response_model=MessageResponse, dependencies=[require_api_key()])
async def add_chat_message(session_id: str, request: AddMessageRequest):
    """添加消息到会话"""
    try:
        if not d1_service or not d1_service.is_enabled():
            raise HTTPException(status_code=503, detail="D1 服务不可用")
        
        message_id = await d1_service.add_chat_message(session_id, request.role, request.content)
        
        # 获取刚添加的消息
        messages = await d1_service.get_chat_messages(session_id, 1)
        if not messages:
            raise HTTPException(status_code=500, detail="添加消息后无法获取消息信息")
        
        # 找到刚添加的消息
        message_data = None
        for msg in messages:
            if msg["id"] == message_id:
                message_data = msg
                break
        
        if not message_data:
            raise HTTPException(status_code=500, detail="添加消息后无法找到消息")
        
        message = ChatMessage(**message_data)
        return MessageResponse(message=message)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"添加聊天消息失败: {e}")
        raise HTTPException(status_code=500, detail=f"添加聊天消息失败: {str(e)}")

@app.get("/api/chat/search", response_model=SearchMessagesResponse, dependencies=[require_api_key()])
async def search_chat_messages(q: str, limit: int = 20):
    """搜索聊天消息"""
    try:
        if not d1_service or not d1_service.is_enabled():
            raise HTTPException(status_code=503, detail="D1 服务不可用")
        
        if not q or len(q.strip()) < 2:
            raise HTTPException(status_code=400, detail="搜索查询至少需要2个字符")
        
        messages_data = await d1_service.search_messages(q.strip(), limit)
        messages = [ChatMessage(**{k: v for k, v in message.items() if k != 'session_title'}) for message in messages_data]
        
        return SearchMessagesResponse(
            messages=messages,
            query=q.strip(),
            total=len(messages)
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"搜索聊天消息失败: {e}")
        raise HTTPException(status_code=500, detail=f"搜索聊天消息失败: {str(e)}")

@app.get("/api/chat/stats", response_model=D1StatsResponse, dependencies=[require_api_key()])
async def get_d1_stats():
    """获取 D1 统计信息"""
    try:
        if not d1_service:
            return D1StatsResponse(
                enabled=False,
                session_count=0,
                message_count=0,
                database_name="未配置",
                error="D1 服务未初始化"
            )
        
        stats = await d1_service.get_stats()
        return D1StatsResponse(**stats)
    except Exception as e:
        logger.error(f"获取 D1 统计信息失败: {e}")
        return D1StatsResponse(
            enabled=False,
            session_count=0,
            message_count=0,
            database_name="未知",
            error=str(e)
        )

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
    
    d1_status = "已启用" if d1_service and d1_service.is_enabled() else "未配置"
    
    return {
        "message": "Project Yuzuriha Enhanced API",
        "version": "2.4.0",
        "status": "running",
        "current_time": time_info['current_time'],
        "memory_backend": "milvus_only",
        "storage_backend": f"milvus + d1({d1_status})",
        "supermemory_removed": True,
        "features": [
            "增强记忆系统 (纯Milvus)",
            "情绪分析",
            "事件分类", 
            "时间感知",
            "语义搜索",
            "Zilliz Cloud Milvus",
            "文件上传",
            "语音转文本",
            "Cloudflare D1 聊天历史存储"
        ]
    }

@app.post("/upload", response_model=FileUploadResponse)
async def upload_files(files: List[UploadFile] = File(...)):
    """文件上传接口"""
    try:
        uploaded_files = []
        
        for file in files:
            # 验证文件类型
            file_type = get_file_type(file.filename)
            if file_type == 'other':
                raise HTTPException(status_code=400, detail=f"不支持的文件类型: {file.filename}")
            
            # 生成唯一文件名
            file_id = str(uuid.uuid4())
            file_extension = file.filename.split('.')[-1]
            unique_filename = f"{file_id}.{file_extension}"
            file_path = os.path.join(UPLOAD_DIR, unique_filename)
            
            # 保存文件
            async with aiofiles.open(file_path, 'wb') as out_file:
                content = await file.read()
                await out_file.write(content)
            
            # 创建文件记录
            uploaded_file = UploadedFile(
                id=file_id,
                filename=file.filename,
                type=file_type,
                size=len(content),
                path=file_path
            )
            uploaded_files.append(uploaded_file)
            
            logger.info(f"文件上传成功: {file.filename} -> {unique_filename}")
        
        return FileUploadResponse(files=uploaded_files)
        
    except Exception as e:
        logger.error(f"文件上传失败: {e}")
        raise HTTPException(status_code=500, detail=f"文件上传失败: {str(e)}")

@app.post("/transcribe", response_model=TranscriptionResponse)
async def transcribe_audio(file: UploadFile = File(...)):
    """音频转文本接口"""
    try:
        # 验证是否为音频文件
        file_type = get_file_type(file.filename)
        if file_type != 'audio':
            raise HTTPException(status_code=400, detail="仅支持音频文件转录")
        
        # 创建临时文件
        import tempfile
        with tempfile.NamedTemporaryFile(delete=False, suffix=f".{file.filename.split('.')[-1]}") as tmp_file:
            content = await file.read()
            tmp_file.write(content)
            tmp_file.flush()
            
            # 调用 OpenAI Whisper API
            with open(tmp_file.name, 'rb') as audio_file:
                transcript = await openai_service.transcribe_audio(audio_file)
            
            # 清理临时文件
            os.unlink(tmp_file.name)
            
            logger.info(f"音频转录成功: {file.filename}")
            
            return TranscriptionResponse(
                text=transcript,
                success=True
            )
        
    except Exception as e:
        # 确保临时文件被删除
        if 'tmp_file' in locals():
            try:
                os.unlink(tmp_file.name)
            except:
                pass
        
        logger.error(f"语音转文本失败: {e}")
        raise HTTPException(status_code=500, detail=f"Transcription failed: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)