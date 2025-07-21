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
        """构建增强的上下文，包含时间感知"""
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
        if memories:
            context_parts.extend([
                "=== 相关记忆 ===",
                "以下是与当前对话相关的历史记忆："
            ])
            
            for i, memory in enumerate(memories[:3], 1):
                formatted_time = self.time_service.format_timestamp(
                    memory.get('timestamp', 0)
                ) if memory.get('timestamp') else '时间未知'
                
                context_parts.append(
                    f"{i}. [{formatted_time}] {memory.get('content', '')}"
                    f" (相关度: {memory.get('relevance_score', 0):.2f}, "
                    f"情绪权重: {memory.get('emotion_weight', 0):.2f})"
                )
            context_parts.append("")
        
        # 添加最近对话历史
        if conversation_history:
            context_parts.extend([
                "=== 最近对话 ===",
                "以下是最近的对话内容："
            ])
            
            for msg in conversation_history[-5:]:
                role = "用户" if msg.get('role') == 'user' else "助手"
                context_parts.append(f"{role}: {msg.get('content', '')}")
            context_parts.append("")
        
        # 添加当前用户消息
        context_parts.extend([
            "=== 当前用户消息 ===",
            f"用户: {user_message}",
            "",
            "请基于以上信息，结合时间上下文和历史记忆，提供有帮助的回复。"
        ])
        
        return "\n".join(context_parts)

    async def generate_response(
        self,
        user_message: str,
        memories: List[Dict[str, Any]] = None,
        conversation_history: List[Dict[str, str]] = None
    ) -> str:
        """生成回复"""
        try:
            context = self._build_enhanced_context(user_message, memories, conversation_history)
            
            response = await self.client.chat.completions.create(
                model=self.chat_model,
                messages=[
                    {"role": "system", "content": context}
                ],
                max_tokens=2000,
                temperature=0.7,
                top_p=0.9,
                frequency_penalty=0.0,
                presence_penalty=0.0
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            logger.error(f"OpenAI生成回复错误: {e}")
            raise Exception(f"生成回复失败: {str(e)}")

    async def create_embedding(self, text: str) -> List[float]:
        """创建文本嵌入"""
        try:
            response = await self.client.embeddings.create(
                model=self.embedding_model,
                input=text,
                encoding_format="float"
            )
            
            return response.data[0].embedding
            
        except Exception as e:
            logger.error(f"OpenAI创建嵌入错误: {e}")
            raise Exception(f"创建嵌入失败: {str(e)}")

    def get_model_info(self) -> Dict[str, str]:
        """获取模型信息"""
        return {
            'chat_model': self.chat_model,
            'embedding_model': self.embedding_model,
            'system_prompt': self.system_prompt[:100] + '...' if len(self.system_prompt) > 100 else self.system_prompt
        }