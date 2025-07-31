"""
Cloudflare D1 数据库服务
用于结构化存储聊天历史记录
"""

import os
import json
import uuid
import time
import logging
from typing import List, Dict, Any, Optional
import httpx
from datetime import datetime

logger = logging.getLogger(__name__)


class D1Service:
    """Cloudflare D1 数据库服务类"""
    
    def __init__(self):
        """初始化 D1 服务"""
        self.account_id = os.getenv('CLOUDFLARE_ACCOUNT_ID')
        self.database_id = os.getenv('CLOUDFLARE_D1_DATABASE_ID')
        self.api_token = os.getenv('CLOUDFLARE_API_TOKEN')
        self.database_name = os.getenv('CLOUDFLARE_D1_DATABASE_NAME', 'yuzuriha_chat_db')
        
        if not all([self.account_id, self.database_id, self.api_token]):
            logger.warning("D1 配置不完整，将无法使用云端存储功能")
            self.enabled = False
        else:
            self.enabled = True
            
        self.base_url = f"https://api.cloudflare.com/client/v4/accounts/{self.account_id}/d1/database/{self.database_id}"
        self.headers = {
            "Authorization": f"Bearer {self.api_token}",
            "Content-Type": "application/json"
        }
    
    def is_enabled(self) -> bool:
        """检查 D1 服务是否可用"""
        return self.enabled
    
    async def execute_query(self, sql: str, params: List[Any] = None) -> Dict[str, Any]:
        """执行 SQL 查询"""
        if not self.enabled:
            raise Exception("D1 服务未启用")
        
        # 确保参数格式正确 - 根据 Cloudflare D1 API 文档
        cleaned_params = []
        if params:
            for param in params:
                # 确保参数类型正确，D1 支持 string, number, boolean, null
                if param is None:
                    cleaned_params.append(None)
                elif isinstance(param, (str, int, float, bool)):
                    cleaned_params.append(param)
                else:
                    # 对于其他类型，转换为字符串
                    cleaned_params.append(str(param))
        
        payload = {
            "sql": sql,
            "params": cleaned_params
        }
        
        try:
            async with httpx.AsyncClient() as client:
                # 添加详细的请求日志用于调试
                logger.info(f"D1 查询请求: URL={self.base_url}/query")
                logger.debug(f"D1 查询 SQL: {sql}")
                logger.debug(f"D1 查询参数: {cleaned_params}")
                
                response = await client.post(
                    f"{self.base_url}/query",
                    headers=self.headers,
                    json=payload,
                    timeout=30.0
                )
                
                # 添加详细的响应日志
                logger.info(f"D1 查询响应状态: {response.status_code}")
                
                if not response.is_success:
                    response_text = response.text
                    logger.error(f"D1 查询失败 - 状态码: {response.status_code}")
                    logger.error(f"请求负载: {payload}")
                    logger.error(f"响应内容: {response_text}")
                    response.raise_for_status()
                
                result = response.json()
                logger.debug(f"D1 查询成功，返回记录数: {len(result.get('result', []))}")
                return result
        except httpx.HTTPStatusError as e:
            logger.error(f"D1 查询 HTTP 错误: {e.response.status_code} - {e.response.text}")
            raise
        except Exception as e:
            logger.error(f"D1 查询执行失败: {e}")
            raise
    
    async def execute_batch(self, queries: List[Dict[str, Any]]) -> Dict[str, Any]:
        """批量执行 SQL 查询"""
        if not self.enabled:
            raise Exception("D1 服务未启用")
        
        # 清理和验证查询参数
        cleaned_queries = []
        for query in queries:
            cleaned_params = []
            if query.get("params"):
                for param in query["params"]:
                    if param is None:
                        cleaned_params.append(None)
                    elif isinstance(param, (str, int, float, bool)):
                        cleaned_params.append(param)
                    else:
                        cleaned_params.append(str(param))
            
            cleaned_queries.append({
                "sql": query["sql"],
                "params": cleaned_params
            })
        
        try:
            async with httpx.AsyncClient() as client:
                # 添加详细的请求日志用于调试
                logger.info(f"D1 批量查询请求: URL={self.base_url}/query, 查询数量={len(cleaned_queries)}")
                for i, query in enumerate(cleaned_queries):
                    logger.debug(f"查询 {i+1}: SQL={query['sql'][:100]}..., 参数={query['params']}")
                
                # 根据 Cloudflare D1 API，批量查询直接发送查询数组
                response = await client.post(
                    f"{self.base_url}/query",
                    headers=self.headers,
                    json=cleaned_queries,
                    timeout=30.0
                )
                
                # 添加详细的响应日志
                logger.info(f"D1 批量查询响应状态: {response.status_code}")
                
                if not response.is_success:
                    response_text = response.text
                    logger.error(f"D1 批量查询失败 - 状态码: {response.status_code}")
                    logger.error(f"请求负载: {cleaned_queries}")
                    logger.error(f"响应内容: {response_text}")
                    
                    # 如果批量查询失败（可能不支持），尝试顺序执行每个查询
                    logger.info("批量查询失败，尝试顺序执行单个查询")
                    results = []
                    all_success = True
                    
                    for i, query in enumerate(cleaned_queries):
                        try:
                            result = await self.execute_query(query["sql"], query["params"])
                            if result.get("success"):
                                results.append(result)
                                logger.info(f"查询 {i+1}/{len(cleaned_queries)} 执行成功")
                            else:
                                logger.error(f"查询 {i+1}/{len(cleaned_queries)} 返回失败: {result}")
                                all_success = False
                                break
                        except Exception as query_error:
                            logger.error(f"查询 {i+1}/{len(cleaned_queries)} 执行失败: {query_error}")
                            all_success = False
                            break
                    
                    if all_success:
                        # 返回模拟的批量结果格式
                        return {
                            "success": True,
                            "result": [r.get("result", []) for r in results],
                            "meta": {"duration": sum(r.get("meta", {}).get("duration", 0) for r in results)}
                        }
                    else:
                        # 如果单个查询也失败，抛出原始错误
                        response.raise_for_status()
                
                result = response.json()
                logger.info(f"D1 批量查询成功")
                return result
        except httpx.HTTPStatusError as e:
            logger.error(f"D1 批量查询 HTTP 错误: {e.response.status_code} - {e.response.text}")
            raise
        except Exception as e:
            logger.error(f"D1 批量查询执行失败: {e}")
            raise
    
    async def create_chat_session(self, title: str) -> str:
        """创建新的聊天会话"""
        session_id = str(uuid.uuid4())
        current_time = int(time.time() * 1000)  # 毫秒时间戳
        
        sql = """
        INSERT INTO chat_sessions (id, title, created_at, updated_at)
        VALUES (?, ?, ?, ?)
        """
        params = [session_id, title, current_time, current_time]
        
        try:
            await self.execute_query(sql, params)
            logger.info(f"创建聊天会话成功: {session_id}")
            return session_id
        except Exception as e:
            logger.error(f"创建聊天会话失败: {e}")
            raise
    
    async def get_chat_sessions(self, limit: int = 50) -> List[Dict[str, Any]]:
        """获取聊天会话列表"""
        sql = """
        SELECT id, title, created_at, updated_at
        FROM chat_sessions
        ORDER BY updated_at DESC
        LIMIT ?
        """
        params = [limit]
        
        try:
            result = await self.execute_query(sql, params)
            sessions = []
            
            if result.get("success") and result.get("result"):
                for row in result["result"]:
                    sessions.append({
                        "id": row["id"],
                        "title": row["title"],
                        "created_at": row["created_at"],
                        "updated_at": row["updated_at"]
                    })
            
            logger.info(f"获取到 {len(sessions)} 个聊天会话")
            return sessions
        except Exception as e:
            logger.error(f"获取聊天会话失败: {e}")
            raise
    
    async def get_chat_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """获取特定聊天会话"""
        sql = """
        SELECT id, title, created_at, updated_at
        FROM chat_sessions
        WHERE id = ?
        """
        params = [session_id]
        
        try:
            result = await self.execute_query(sql, params)
            
            if result.get("success") and result.get("result") and len(result["result"]) > 0:
                row = result["result"][0]
                return {
                    "id": row["id"],
                    "title": row["title"],
                    "created_at": row["created_at"],
                    "updated_at": row["updated_at"]
                }
            return None
        except Exception as e:
            logger.error(f"获取聊天会话失败: {e}")
            raise
    
    async def update_chat_session(self, session_id: str, title: str = None) -> bool:
        """更新聊天会话"""
        current_time = int(time.time() * 1000)
        
        if title:
            sql = """
            UPDATE chat_sessions
            SET title = ?, updated_at = ?
            WHERE id = ?
            """
            params = [title, current_time, session_id]
        else:
            sql = """
            UPDATE chat_sessions
            SET updated_at = ?
            WHERE id = ?
            """
            params = [current_time, session_id]
        
        try:
            result = await self.execute_query(sql, params)
            success = result.get("success", False)
            logger.info(f"更新聊天会话 {session_id}: {'成功' if success else '失败'}")
            return success
        except Exception as e:
            logger.error(f"更新聊天会话失败: {e}")
            raise
    
    async def delete_chat_session(self, session_id: str) -> bool:
        """删除聊天会话及其所有消息"""
        queries = [
            {
                "sql": "DELETE FROM chat_messages WHERE session_id = ?",
                "params": [session_id]
            },
            {
                "sql": "DELETE FROM chat_sessions WHERE id = ?",
                "params": [session_id]
            }
        ]
        
        try:
            result = await self.execute_batch(queries)
            success = result.get("success", False)
            logger.info(f"删除聊天会话 {session_id}: {'成功' if success else '失败'}")
            return success
        except Exception as e:
            logger.error(f"删除聊天会话失败: {e}")
            raise
    
    async def add_chat_message(self, session_id: str, role: str, content: str) -> str:
        """添加聊天消息"""
        message_id = str(uuid.uuid4())
        timestamp = int(time.time() * 1000)
        
        # 先添加消息
        sql_message = """
        INSERT INTO chat_messages (id, session_id, role, content, timestamp)
        VALUES (?, ?, ?, ?, ?)
        """
        params_message = [message_id, session_id, role, content, timestamp]
        
        # 然后更新会话的 updated_at
        sql_session = """
        UPDATE chat_sessions
        SET updated_at = ?
        WHERE id = ?
        """
        params_session = [timestamp, session_id]
        
        queries = [
            {"sql": sql_message, "params": params_message},
            {"sql": sql_session, "params": params_session}
        ]
        
        try:
            result = await self.execute_batch(queries)
            if result.get("success"):
                logger.info(f"添加聊天消息成功: {message_id}")
                return message_id
            else:
                raise Exception("批量查询失败")
        except Exception as e:
            logger.error(f"添加聊天消息失败: {e}")
            raise
    
    async def get_chat_messages(self, session_id: str, limit: int = 100) -> List[Dict[str, Any]]:
        """获取聊天消息列表"""
        sql = """
        SELECT id, session_id, role, content, timestamp
        FROM chat_messages
        WHERE session_id = ?
        ORDER BY timestamp ASC
        LIMIT ?
        """
        params = [session_id, limit]
        
        try:
            result = await self.execute_query(sql, params)
            messages = []
            
            if result.get("success") and result.get("result"):
                for row in result["result"]:
                    messages.append({
                        "id": row["id"],
                        "session_id": row["session_id"],
                        "role": row["role"],
                        "content": row["content"],
                        "timestamp": row["timestamp"]
                    })
            
            logger.info(f"获取到 {len(messages)} 条聊天消息")
            return messages
        except Exception as e:
            logger.error(f"获取聊天消息失败: {e}")
            raise
    
    async def get_message_count(self, session_id: str) -> int:
        """获取会话中的消息数量"""
        sql = """
        SELECT COUNT(*) as count
        FROM chat_messages
        WHERE session_id = ?
        """
        params = [session_id]
        
        try:
            result = await self.execute_query(sql, params)
            
            if result.get("success") and result.get("result") and len(result["result"]) > 0:
                return result["result"][0]["count"]
            return 0
        except Exception as e:
            logger.error(f"获取消息数量失败: {e}")
            return 0
    
    async def search_messages(self, query: str, limit: int = 20) -> List[Dict[str, Any]]:
        """搜索聊天消息（简单文本搜索）"""
        sql = """
        SELECT m.id, m.session_id, m.role, m.content, m.timestamp, s.title
        FROM chat_messages m
        JOIN chat_sessions s ON m.session_id = s.id
        WHERE m.content LIKE ?
        ORDER BY m.timestamp DESC
        LIMIT ?
        """
        params = [f"%{query}%", limit]
        
        try:
            result = await self.execute_query(sql, params)
            messages = []
            
            if result.get("success") and result.get("result"):
                for row in result["result"]:
                    messages.append({
                        "id": row["id"],
                        "session_id": row["session_id"],
                        "role": row["role"],
                        "content": row["content"],
                        "timestamp": row["timestamp"],
                        "session_title": row["title"]
                    })
            
            logger.info(f"搜索到 {len(messages)} 条匹配消息")
            return messages
        except Exception as e:
            logger.error(f"搜索消息失败: {e}")
            raise
    
    async def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        queries = [
            {
                "sql": "SELECT COUNT(*) as session_count FROM chat_sessions",
                "params": []
            },
            {
                "sql": "SELECT COUNT(*) as message_count FROM chat_messages",
                "params": []
            }
        ]
        
        try:
            result = await self.execute_batch(queries)
            
            if result.get("success") and len(result.get("result", [])) >= 2:
                session_count = result["result"][0].get("session_count", 0)
                message_count = result["result"][1].get("message_count", 0)
                
                return {
                    "enabled": self.enabled,
                    "session_count": session_count,
                    "message_count": message_count,
                    "database_name": self.database_name
                }
            else:
                return {
                    "enabled": self.enabled,
                    "session_count": 0,
                    "message_count": 0,
                    "database_name": self.database_name
                }
        except Exception as e:
            logger.error(f"获取统计信息失败: {e}")
            return {
                "enabled": self.enabled,
                "error": str(e),
                "database_name": self.database_name
            }