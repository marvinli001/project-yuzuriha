import os
import logging
from typing import List, Dict, Any
from openai import AsyncOpenAI
from services.time_service import TimeService

logger = logging.getLogger(__name__)

class OpenAIService:
    def __init__(self):
        self.api_key = os.getenv('OPENAI_API_KEY')
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY 环境变量是必需的")
        
        self.client = AsyncOpenAI(api_key=self.api_key)
        
        # 从环境变量获取模型配置
        self.chat_model = os.getenv('OPENAI_CHAT_MODEL', 'gpt-4o')
        self.embedding_model = os.getenv('OPENAI_EMBEDDING_MODEL', 'text-embedding-3-small')
        self.system_prompt = os.getenv('SYSTEM_PROMPT', '你是一个有帮助的AI助手。')
        
        # 时间服务
        self.time_service = TimeService()
        
        logger.info(f"OpenAI服务初始化完成 - 聊天模型: {self.chat_model}, 嵌入模型: {self.embedding_model}")

    def _build_enhanced_context(
        self,
        user_message: str,
        memories: List[Dict[str, Any]] = None,
        conversation_history: List[Dict[str, str]] = None
    ) -> str:
        """构建增强的上下文，包含时间感知 - 修复编码问题"""
        try:
            time_context = self.time_service.get_time_context()
            
            context_parts = [
                self.system_prompt,
                "",
                "=== 时间信息 ===",
                f"当前时间: {time_context['current_time']}",
                f"日期: {time_context['date']}",
                f"星期: {time_context['weekday']}",
                f"时区: {time_context['timezone']}",
                ""
            ]
            
            # 添加相关记忆
            if memories and len(memories) > 0:
                context_parts.extend([
                    "=== 相关记忆 ===",
                    "以下是与当前对话相关的历史记忆："
                ])
                
                for i, memory in enumerate(memories[:3], 1):
                    # 安全地获取时间戳并格式化
                    try:
                        timestamp = memory.get('timestamp', 0)
                        if timestamp and timestamp > 0:
                            formatted_time = self.time_service.format_timestamp(timestamp)
                        else:
                            formatted_time = '时间未知'
                    except Exception:
                        formatted_time = '时间未知'
                    
                    # 安全地获取内容并清理
                    content = str(memory.get('content', memory.get('text', ''))).strip()
                    if not content:
                        content = '内容为空'
                    
                    # 限制内容长度并确保没有特殊字符导致编码问题
                    content = content[:200] + '...' if len(content) > 200 else content
                    content = content.replace('\x00', '').replace('\r\n', '\n').replace('\r', '\n')
                    
                    context_parts.append(
                        f"{i}. [{formatted_time}] {content}"
                        f" (相关度: {memory.get('relevance_score', 0):.2f})"
                    )
                context_parts.append("")
            
            # 添加最近对话历史
            if conversation_history and len(conversation_history) > 0:
                context_parts.extend([
                    "=== 最近对话 ===",
                    "以下是最近的对话内容："
                ])
                
                for msg in conversation_history[-5:]:  # 只取最近5条
                    role = "用户" if msg.get('role') == 'user' else "助手"
                    content = str(msg.get('content', '')).strip()[:100]  # 限制长度
                    content = content.replace('\x00', '').replace('\r\n', '\n').replace('\r', '\n')
                    if content:
                        context_parts.append(f"{role}: {content}")
                context_parts.append("")
            
            # 添加当前用户消息
            clean_user_message = str(user_message).strip()
            clean_user_message = clean_user_message.replace('\x00', '').replace('\r\n', '\n').replace('\r', '\n')
            
            context_parts.extend([
                "=== 当前用户消息 ===",
                f"用户: {clean_user_message}",
                "",
                "请基于以上信息，结合时间上下文和历史记忆，提供有帮助的回复。"
            ])
            
            # 确保返回的字符串是有效的
            result = "\n".join(context_parts)
            
            # 验证字符串有效性
            if not result.strip():
                result = f"{self.system_prompt}\n\n用户: {clean_user_message}\n\n请提供有帮助的回复。"
            
            return result
            
        except Exception as e:
            logger.error(f"构建上下文时出错: {e}")
            # 返回最小化的安全上下文
            clean_user_message = str(user_message).replace('\x00', '').strip()
            return f"{self.system_prompt}\n\n用户: {clean_user_message}\n\n请提供有帮助的回复。"

    async def generate_response(
        self,
        user_message: str,
        memories: List[Dict[str, Any]] = None,
        conversation_history: List[Dict[str, str]] = None
    ) -> str:
        """生成回复 - 修复 Invalid argument 错误"""
        try:
            # 构建上下文，确保没有编码问题
            context = self._build_enhanced_context(user_message, memories, conversation_history)
            
            # 验证上下文有效性
            if not context or not context.strip():
                context = f"{self.system_prompt}\n\n用户: {user_message}\n\n请提供有帮助的回复。"
            
            # 确保内容长度不超过限制
            if len(context) > 8000:  # 留出一些余量
                context = context[:8000] + "...\n\n请基于以上信息提供回复。"
            
            # 构建消息列表
            messages = [
                {"role": "system", "content": context},
                {"role": "user", "content": str(user_message).strip()}
            ]
            
            # 验证消息内容
            for msg in messages:
                if not msg["content"] or not msg["content"].strip():
                    raise ValueError("消息内容不能为空")
                # 清理潜在的有问题字符
                msg["content"] = msg["content"].replace('\x00', '').strip()
            
            logger.info(f"准备发送OpenAI请求，消息数量: {len(messages)}, 上下文长度: {len(context)}")
            
            response = await self.client.chat.completions.create(
                model=self.chat_model,
                messages=messages,
                max_tokens=1000,  # 减少token数量避免问题
                temperature=0.7,
                top_p=0.9,
                frequency_penalty=0.0,
                presence_penalty=0.0,
                timeout=30  # 添加超时
            )
            
            if not response.choices or not response.choices[0].message.content:
                raise ValueError("OpenAI返回空响应")
            
            result = response.choices[0].message.content.strip()
            if not result:
                result = "抱歉，我现在无法生成回复，请稍后再试。"
            
            return result
            
        except Exception as e:
            logger.error(f"OpenAI生成回复错误: {e}")
            # 返回友好的错误消息而不是抛出异常
            return "抱歉，发送消息时出现错误。请检查网络连接并重试。"

    async def create_embedding(self, text: str) -> List[float]:
        """创建文本嵌入 - 添加错误处理"""
        try:
            # 清理文本
            clean_text = str(text).strip().replace('\x00', '')
            if not clean_text:
                clean_text = "空文本"
            
            # 限制文本长度
            if len(clean_text) > 2000:
                clean_text = clean_text[:2000] + "..."
            
            response = await self.client.embeddings.create(
                model=self.embedding_model,
                input=clean_text,
                encoding_format="float",
                timeout=30
            )
            
            if not response.data or not response.data[0].embedding:
                raise ValueError("嵌入响应为空")
            
            return response.data[0].embedding
            
        except Exception as e:
            logger.error(f"OpenAI创建嵌入错误: {e}")
            # 返回默认嵌入向量而不是抛出异常
            return [0.0] * 1536  # text-embedding-3-small 的维度

    def get_model_info(self) -> Dict[str, str]:
        """获取模型信息"""
        return {
            'chat_model': self.chat_model,
            'embedding_model': self.embedding_model,
            'system_prompt': self.system_prompt[:100] + '...' if len(self.system_prompt) > 100 else self.system_prompt
        }