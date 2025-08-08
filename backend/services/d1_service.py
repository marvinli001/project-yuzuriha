"""
Cloudflare D1 数据库服务
用于结构化存储聊天历史记录
"""

import os
import json
import uuid
import time
import logging
import asyncio
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
        # 重试配置
        self.max_retries = 3
        self.retry_delay = 1.0  # 初始延迟秒数
        
        # 调试模式 - 临时启用详细日志
        self.debug_mode = os.getenv('D1_DEBUG_MODE', 'false').lower() == 'true'
        if self.debug_mode:
            logger.warning("D1 调试模式已启用 - 将记录详细的请求和响应信息")
    
    def is_enabled(self) -> bool:
        """检查 D1 服务是否可用"""
        return self.enabled
    
    def _validate_and_clean_params(self, params: List[Any]) -> List[Any]:
        """验证和清理查询参数"""
        if not params:
            return []
        
        cleaned_params = []
        for param in params:
            if param is None:
                cleaned_params.append(None)
            elif isinstance(param, (str, int, float, bool)):
                cleaned_params.append(param)
            elif isinstance(param, bytes):
                # D1 不直接支持二进制数据，转换为字符串
                cleaned_params.append(param.decode('utf-8', errors='replace'))
            else:
                # 对于复杂类型，转换为 JSON 字符串
                try:
                    cleaned_params.append(json.dumps(param, ensure_ascii=False))
                except (TypeError, ValueError):
                    cleaned_params.append(str(param))
        
        return cleaned_params
    
    def _validate_sql(self, sql: str) -> bool:
        """基本的 SQL 语句验证"""
        if not sql or not isinstance(sql, str):
            return False
        
        sql = sql.strip()
        if not sql:
            return False
        
        # 基本的 SQL 注入防护 - 检查危险关键词
        dangerous_keywords = ['DROP', 'DELETE FROM', 'TRUNCATE', 'ALTER TABLE']
        sql_upper = sql.upper()
        
        # 对于某些操作，我们需要额外小心
        for keyword in dangerous_keywords:
            if keyword in sql_upper:
                logger.warning(f"SQL 包含潜在危险关键词: {keyword}")
        
        return True
    
    def _parse_d1_row(self, row: Any, columns: List[str]) -> Dict[str, Any]:
        """解析D1返回的行数据，支持数组和对象格式"""
        if isinstance(row, dict):
            # 如果已经是字典格式，直接返回
            return row
        elif isinstance(row, list) and columns:
            # 如果是数组格式，根据列名转换为字典
            result = {}
            for i, column in enumerate(columns):
                if i < len(row):
                    result[column] = row[i]
                else:
                    result[column] = None
            return result
        else:
            # 其他情况，尝试转换为字典
            logger.warning(f"无法解析D1行数据格式: {type(row)}, 数据: {row}")
            return {}
    
    async def _execute_with_retry(self, url: str, payload: Dict[str, Any], operation_name: str) -> Dict[str, Any]:
        """带重试机制的请求执行"""
        last_exception = None
        
        for attempt in range(self.max_retries):
            try:
                async with httpx.AsyncClient() as client:
                    logger.info(f"D1 {operation_name} 请求 (尝试 {attempt + 1}/{self.max_retries}): URL={url}")
                    
                    if self.debug_mode:
                        logger.info(f"D1 调试 - 请求头: {self.headers}")
                        logger.info(f"D1 调试 - 请求负载: {json.dumps(payload, indent=2, ensure_ascii=False)}")
                    
                    response = await client.post(
                        url,
                        headers=self.headers,
                        json=payload,
                        timeout=30.0
                    )
                    
                    logger.info(f"D1 {operation_name} 响应状态: {response.status_code}")
                    
                    if self.debug_mode:
                        logger.info(f"D1 调试 - 响应头: {dict(response.headers)}")
                    
                    if response.is_success:
                        result = response.json()
                        if self.debug_mode:
                            logger.info(f"D1 调试 - 响应内容: {json.dumps(result, indent=2, ensure_ascii=False)}")
                        logger.debug(f"D1 {operation_name} 成功")
                        return result
                    else:
                        response_text = response.text
                        logger.error(f"D1 {operation_name} 失败 - 状态码: {response.status_code}")
                        logger.error(f"D1 错误响应内容: {response_text}")
                        
                        if self.debug_mode:
                            logger.error(f"D1 调试 - 完整请求信息:")
                            logger.error(f"  URL: {url}")
                            logger.error(f"  Headers: {self.headers}")
                            logger.error(f"  Payload: {json.dumps(payload, indent=2, ensure_ascii=False)}")
                        
                        # 对于 4xx 错误，不重试
                        if 400 <= response.status_code < 500:
                            response.raise_for_status()
                        
                        # 对于 5xx 错误，可以重试
                        if attempt < self.max_retries - 1:
                            delay = self.retry_delay * (2 ** attempt)  # 指数退避
                            logger.info(f"等待 {delay} 秒后重试...")
                            await asyncio.sleep(delay)
                            continue
                        else:
                            response.raise_for_status()
                            
            except httpx.HTTPStatusError as e:
                last_exception = e
                logger.error(f"D1 {operation_name} HTTP 错误: {e.response.status_code} - {e.response.text}")
                
                # 对于 4xx 错误，不重试
                if 400 <= e.response.status_code < 500:
                    raise
                    
                # 对于 5xx 错误，可以重试
                if attempt < self.max_retries - 1:
                    delay = self.retry_delay * (2 ** attempt)
                    logger.info(f"遇到 {e.response.status_code} 错误，等待 {delay} 秒后重试...")
                    await asyncio.sleep(delay)
                    continue
                else:
                    raise
                    
            except Exception as e:
                last_exception = e
                logger.error(f"D1 {operation_name} 异常: {e}")
                
                if attempt < self.max_retries - 1:
                    delay = self.retry_delay * (2 ** attempt)
                    logger.info(f"遇到异常，等待 {delay} 秒后重试...")
                    await asyncio.sleep(delay)
                    continue
                else:
                    raise
        
        # 如果所有重试都失败了
        if last_exception:
            raise last_exception
        else:
            raise Exception(f"D1 {operation_name} 在 {self.max_retries} 次尝试后失败")
    
    async def execute_query(self, sql: str, params: List[Any] = None) -> Dict[str, Any]:
        """执行 SQL 查询"""
        if not self.enabled:
            raise Exception("D1 服务未启用")
        
        # 验证 SQL 语句
        if not self._validate_sql(sql):
            raise ValueError("无效的 SQL 语句")
        
        # 清理和验证参数
        cleaned_params = self._validate_and_clean_params(params or [])
        
        # 根据 D1 API 文档，单个查询使用对象格式
        payload = {
            "sql": sql,
            "params": cleaned_params
        }
        
        logger.debug(f"D1 查询 SQL: {sql}")
        logger.debug(f"D1 查询参数: {cleaned_params}")
        
        try:
            return await self._execute_with_retry(
                f"{self.base_url}/query",
                payload,
                "单查询"
            )
        except Exception as e:
            logger.error(f"D1 查询执行失败: {e}")
            raise
    
    async def execute_batch(self, queries: List[Dict[str, Any]]) -> Dict[str, Any]:
        """批量执行 SQL 查询 - 使用顺序执行"""
        if not self.enabled:
            raise Exception("D1 服务未启用")
        
        if not queries:
            return {"success": True, "result": [], "meta": {"duration": 0}}
        
        # 验证和清理所有查询
        cleaned_queries = []
        for i, query in enumerate(queries):
            if not isinstance(query, dict) or "sql" not in query:
                raise ValueError(f"查询 {i+1} 格式无效：缺少 sql 字段")
            
            sql = query["sql"]
            if not self._validate_sql(sql):
                raise ValueError(f"查询 {i+1} SQL 语句无效")
            
            cleaned_params = self._validate_and_clean_params(query.get("params", []))
            
            cleaned_queries.append({
                "sql": sql,
                "params": cleaned_params
            })
        
        logger.info(f"准备执行 {len(cleaned_queries)} 个批量查询")
        
        # D1 REST API 不支持真正的批量查询，只能顺序执行
        try:
            results = []
            total_duration = 0
            
            for i, query in enumerate(cleaned_queries):
                try:
                    if self.debug_mode:
                        logger.info(f"执行顺序查询 {i+1}/{len(cleaned_queries)}: {query['sql'][:100]}...")
                    
                    result = await self.execute_query(query["sql"], query["params"])
                    if result.get("success"):
                        results.append(result.get("result", []))
                        total_duration += result.get("meta", {}).get("duration", 0)
                        logger.info(f"顺序查询 {i+1}/{len(cleaned_queries)} 执行成功")
                    else:
                        logger.error(f"顺序查询 {i+1}/{len(cleaned_queries)} 返回失败: {result}")
                        raise Exception(f"查询 {i+1} 执行失败")
                except Exception as query_error:
                    logger.error(f"顺序查询 {i+1}/{len(cleaned_queries)} 执行失败: {query_error}")
                    raise Exception(f"查询 {i+1} 执行失败: {query_error}")
            
            # 返回模拟的批量结果格式
            logger.info(f"所有 {len(cleaned_queries)} 个查询顺序执行成功")
            return {
                "success": True,
                "result": results,
                "meta": {"duration": total_duration}
            }
                
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
                # D1 API 的响应结构
                query_result = result["result"][0] if isinstance(result["result"], list) else result["result"]
                
                # 获取列信息和结果行
                columns = query_result.get("meta", {}).get("columns", [])
                results = query_result.get("results", [])
                
                logger.debug(f"D1 查询列信息: {columns}")
                logger.debug(f"D1 查询结果数量: {len(results)}")
                
                # 解析每一行数据
                for row in results:
                    parsed_row = self._parse_d1_row(row, columns)
                    if parsed_row:
                        sessions.append({
                            "id": parsed_row.get("id"),
                            "title": parsed_row.get("title"),
                            "created_at": parsed_row.get("created_at"),
                            "updated_at": parsed_row.get("updated_at")
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
            
            if result.get("success") and result.get("result"):
                # D1 API 的响应结构
                query_result = result["result"][0] if isinstance(result["result"], list) else result["result"]
                
                # 获取列信息和结果行
                columns = query_result.get("meta", {}).get("columns", [])
                results = query_result.get("results", [])
                
                if results:
                    row = results[0]
                    parsed_row = self._parse_d1_row(row, columns)
                    return {
                        "id": parsed_row.get("id"),
                        "title": parsed_row.get("title"),
                        "created_at": parsed_row.get("created_at"),
                        "updated_at": parsed_row.get("updated_at")
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
        # 先删除消息，再删除会话
        try:
            # 删除消息
            await self.execute_query("DELETE FROM chat_messages WHERE session_id = ?", [session_id])
            # 删除会话
            result = await self.execute_query("DELETE FROM chat_sessions WHERE id = ?", [session_id])
            
            success = result.get("success", False)
            logger.info(f"删除聊天会话 {session_id}: {'成功' if success else '失败'}")
            return success
        except Exception as e:
            logger.error(f"删除聊天会话失败: {e}")
            raise
    
    async def add_chat_message(self, session_id: Optional[str], role: str, content: str) -> str:
        """添加聊天消息"""

        message_id = str(uuid.uuid4())
        timestamp = int(time.time() * 1000)

        try:
            # 统一计算“有效会话 ID”
            effective_session_id = session_id

            # 若未传或找不到会话，则创建新会话并改用新会话 ID
            session = None
            if effective_session_id:
                session = await self.get_chat_session(effective_session_id)

            if not session:
                logger.info(f"会话 {session_id} 不存在或未提供，创建新会话")
                effective_session_id = await self.create_chat_session("新对话")

            # 添加消息（注意这里使用 effective_session_id）
            sql_message = """
            INSERT INTO chat_messages (id, session_id, role, content, timestamp)
            VALUES (?, ?, ?, ?, ?)
            """
            params_message = [message_id, effective_session_id, role, content, timestamp]
            await self.execute_query(sql_message, params_message)

            # 更新会话的 updated_at
            sql_session = """
            UPDATE chat_sessions
            SET updated_at = ?
            WHERE id = ?
            """
            params_session = [timestamp, effective_session_id]
            await self.execute_query(sql_session, params_session)

            logger.info(f"添加聊天消息成功: {message_id} -> session {effective_session_id}")
            return message_id

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
                # D1 API 的响应结构
                query_result = result["result"][0] if isinstance(result["result"], list) else result["result"]
                
                # 获取列信息和结果行
                columns = query_result.get("meta", {}).get("columns", [])
                results = query_result.get("results", [])
                
                # 解析每一行数据
                for row in results:
                    parsed_row = self._parse_d1_row(row, columns)
                    if parsed_row:
                        messages.append({
                            "id": parsed_row.get("id"),
                            "session_id": parsed_row.get("session_id"),
                            "role": parsed_row.get("role"),
                            "content": parsed_row.get("content"),
                            "timestamp": parsed_row.get("timestamp")
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
            
            if result.get("success") and result.get("result"):
                # D1 API 的响应结构
                query_result = result["result"][0] if isinstance(result["result"], list) else result["result"]
                
                # 获取列信息和结果行
                columns = query_result.get("meta", {}).get("columns", [])
                results = query_result.get("results", [])
                
                if results:
                    row = results[0]
                    parsed_row = self._parse_d1_row(row, columns)
                    return parsed_row.get("count", 0)
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
                # D1 API 的响应结构
                query_result = result["result"][0] if isinstance(result["result"], list) else result["result"]
                
                # 获取列信息和结果行
                columns = query_result.get("meta", {}).get("columns", [])
                results = query_result.get("results", [])
                
                # 解析每一行数据
                for row in results:
                    parsed_row = self._parse_d1_row(row, columns)
                    if parsed_row:
                        messages.append({
                            "id": parsed_row.get("id"),
                            "session_id": parsed_row.get("session_id"),
                            "role": parsed_row.get("role"),
                            "content": parsed_row.get("content"),
                            "timestamp": parsed_row.get("timestamp"),
                            "session_title": parsed_row.get("title")
                        })
            
            logger.info(f"搜索到 {len(messages)} 条匹配消息")
            return messages
        except Exception as e:
            logger.error(f"搜索消息失败: {e}")
            raise
    
    async def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        try:
            # 分别执行查询
            session_result = await self.execute_query("SELECT COUNT(*) as session_count FROM chat_sessions", [])
            message_result = await self.execute_query("SELECT COUNT(*) as message_count FROM chat_messages", [])
            
            session_count = 0
            message_count = 0
            
            if session_result.get("success") and session_result.get("result"):
                # D1 API 的响应结构
                query_result = session_result["result"][0] if isinstance(session_result["result"], list) else session_result["result"]
                columns = query_result.get("meta", {}).get("columns", [])
                results = query_result.get("results", [])
                
                if results:
                    row = results[0]
                    parsed_row = self._parse_d1_row(row, columns)
                    session_count = parsed_row.get("session_count", 0)
            
            if message_result.get("success") and message_result.get("result"):
                # D1 API 的响应结构
                query_result = message_result["result"][0] if isinstance(message_result["result"], list) else message_result["result"]
                columns = query_result.get("meta", {}).get("columns", [])
                results = query_result.get("results", [])
                
                if results:
                    row = results[0]
                    parsed_row = self._parse_d1_row(row, columns)
                    message_count = parsed_row.get("message_count", 0)
            
            return {
                "enabled": self.enabled,
                "session_count": session_count,
                "message_count": message_count,
                "database_name": self.database_name
            }
        except Exception as e:
            logger.error(f"获取统计信息失败: {e}")
            return {
                "enabled": self.enabled,
                "error": str(e),
                "database_name": self.database_name
            }