"""
Cloudflare D1 相关的数据模型
"""

from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime


class ChatSession(BaseModel):
    """聊天会话模型"""
    id: str
    title: str
    created_at: int  # 毫秒时间戳
    updated_at: int  # 毫秒时间戳


class ChatMessage(BaseModel):
    """聊天消息模型"""
    id: str
    session_id: str
    role: str = Field(..., pattern="^(user|assistant)$")
    content: str
    timestamp: int  # 毫秒时间戳


class ChatSessionWithMessages(BaseModel):
    """包含消息的聊天会话模型"""
    id: str
    title: str
    created_at: int
    updated_at: int
    messages: List[ChatMessage] = []


class CreateSessionRequest(BaseModel):
    """创建会话请求模型"""
    title: str = Field(..., min_length=1, max_length=200)


class UpdateSessionRequest(BaseModel):
    """更新会话请求模型"""
    title: Optional[str] = Field(None, min_length=1, max_length=200)


class AddMessageRequest(BaseModel):
    """添加消息请求模型"""
    role: str = Field(..., pattern="^(user|assistant)$")
    content: str = Field(..., min_length=1)


class SessionsResponse(BaseModel):
    """会话列表响应模型"""
    sessions: List[ChatSession]
    total: int


class MessagesResponse(BaseModel):
    """消息列表响应模型"""
    messages: List[ChatMessage]
    total: int


class SessionResponse(BaseModel):
    """单个会话响应模型"""
    session: ChatSession


class MessageResponse(BaseModel):
    """单个消息响应模型"""
    message: ChatMessage


class SearchMessagesResponse(BaseModel):
    """搜索消息响应模型"""
    messages: List[ChatMessage]
    query: str
    total: int


class D1StatsResponse(BaseModel):
    """D1 统计信息响应模型"""
    enabled: bool
    session_count: int
    message_count: int
    database_name: str
    error: Optional[str] = None


class MigrationData(BaseModel):
    """迁移数据模型（从 localStorage 导入）"""
    sessions: List[dict]  # 来自前端的原始数据


class ApiResponse(BaseModel):
    """通用 API 响应模型"""
    success: bool
    message: str
    data: Optional[dict] = None