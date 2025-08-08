from fastapi import APIRouter, HTTPException, Depends
from typing import Optional, List, Dict, Any
import time
import logging

from auth.api_auth import require_api_key
from services.d1_service import D1Service
from models.d1_models import (
    ChatSession,
    ChatMessage,
    CreateSessionRequest,
    UpdateSessionRequest,
    AddMessageRequest,
    SessionsResponse,
    MessagesResponse,
    SessionResponse,
    MessageResponse,
    ApiResponse,
)

logger = logging.getLogger(__name__)
router = APIRouter(
    prefix="/api/chat",
    tags=["D1 Chat"],
    dependencies=[Depends(require_api_key)],  # 修改这里：移除括号
)

d1_service = D1Service()


def ensure_d1_enabled():
    if not d1_service or not d1_service.is_enabled():
        raise HTTPException(status_code=503, detail="D1 服务不可用")


@router.get("/sessions", response_model=SessionsResponse)
async def get_chat_sessions(limit: int = 50):
    """获取所有聊天会话"""
    ensure_d1_enabled()
    try:
        sessions_data = await d1_service.get_chat_sessions(limit)
        sessions = [ChatSession(**s) for s in sessions_data]
        return SessionsResponse(sessions=sessions, total=len(sessions))
    except Exception as e:
        logger.error(f"获取聊天会话失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取聊天会话失败: {str(e)}")


@router.post("/sessions", response_model=SessionResponse)
async def create_chat_session(request: CreateSessionRequest):
    """创建新的聊天会话"""
    ensure_d1_enabled()
    try:
        session_id = await d1_service.create_chat_session(request.title)
        session_data = await d1_service.get_chat_session(session_id)
        if not session_data:
            raise HTTPException(status_code=500, detail="创建会话后无法获取会话信息")
        return SessionResponse(session=ChatSession(**session_data))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"创建聊天会话失败: {e}")
        raise HTTPException(status_code=500, detail=f"创建聊天会话失败: {str(e)}")


@router.get("/sessions/{session_id}", response_model=SessionResponse)
async def get_chat_session(session_id: str):
    """获取特定聊天会话"""
    ensure_d1_enabled()
    try:
        session_data = await d1_service.get_chat_session(session_id)
        if not session_data:
            raise HTTPException(status_code=404, detail="会话不存在")
        return SessionResponse(session=ChatSession(**session_data))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取聊天会话失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取聊天会话失败: {str(e)}")


@router.put("/sessions/{session_id}", response_model=SessionResponse)
async def update_chat_session(session_id: str, request: UpdateSessionRequest):
    """更新聊天会话（标题）"""
    ensure_d1_enabled()
    try:
        # 先检查会话是否存在，避免 ChatSession(**None) 报错
        existing = await d1_service.get_chat_session(session_id)
        if not existing:
            raise HTTPException(status_code=404, detail="会话不存在")

        ok = await d1_service.update_chat_session(session_id, request.title)
        if not ok:
            raise HTTPException(status_code=400, detail="更新聊天会话失败")

        # 更新后再查询一次并返回
        updated = await d1_service.get_chat_session(session_id)
        if not updated:
            # 理论上不会发生，如发生则视为 404
            raise HTTPException(status_code=404, detail="会话不存在")
        return SessionResponse(session=ChatSession(**updated))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新聊天会话失败: {e}")
        raise HTTPException(status_code=500, detail=f"更新聊天会话失败: {str(e)}")


@router.delete("/sessions/{session_id}", response_model=ApiResponse)
async def delete_chat_session(session_id: str):
    """删除聊天会话（及其所有消息）"""
    ensure_d1_enabled()
    try:
        ok = await d1_service.delete_chat_session(session_id)
        if not ok:
            # 如果要区分"会话不存在"，也可以先查一次再删
            raise HTTPException(status_code=400, detail="删除聊天会话失败")
        return ApiResponse(success=True, message="删除成功", data={"id": session_id})
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除聊天会话失败: {e}")
        raise HTTPException(status_code=500, detail=f"删除聊天会话失败: {str(e)}")


@router.get("/sessions/{session_id}/messages", response_model=MessagesResponse)
async def get_chat_messages(session_id: str, limit: int = 100):
    """获取特定会话的消息"""
    ensure_d1_enabled()
    try:
        # 可选：严格要求会话存在
        session = await d1_service.get_chat_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="会话不存在")

        messages_data = await d1_service.get_chat_messages(session_id, limit)
        messages = [ChatMessage(**m) for m in messages_data]
        return MessagesResponse(messages=messages, total=len(messages))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取聊天消息失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取聊天消息失败: {str(e)}")


@router.post("/sessions/{session_id}/messages", response_model=MessageResponse)
async def add_chat_message(session_id: str, request: AddMessageRequest):
    """
    向会话添加一条消息：
    - 若会话不存在，则返回 404（避免 D1 外键失败）
    - 若存在，则调用服务写入并返回消息
    """
    ensure_d1_enabled()
    try:
        session = await d1_service.get_chat_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="会话不存在")

        # 写入消息
        message_id = await d1_service.add_chat_message(session_id, request.role, request.content)

        # 为了拿到准确的 timestamp，可尝试从列表中回查；找不到则用当前时间作为兜底
        try:
            msgs = await d1_service.get_chat_messages(session_id, limit=100)
            picked = next((m for m in msgs if m.get("id") == message_id), None)
            if picked:
                msg = ChatMessage(**picked)
            else:
                # 兜底（时间可能与库中相差毫秒级）
                msg = ChatMessage(
                    id=message_id,
                    session_id=session_id,
                    role=request.role,
                    content=request.content,
                    timestamp=int(time.time() * 1000),
                )
        except Exception:
            # 回查失败时直接兜底
            msg = ChatMessage(
                id=message_id,
                session_id=session_id,
                role=request.role,
                content=request.content,
                timestamp=int(time.time() * 1000),
            )

        return MessageResponse(message=msg)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"添加聊天消息失败: {e}")
        raise HTTPException(status_code=500, detail=f"添加聊天消息失败: {str(e)}")