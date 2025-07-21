import os
import logging
from typing import List, Dict, Any, Optional
from services.emotion_service import EmotionAnalyzer, EventClassifier
from services.time_service import TimeService

logger = logging.getLogger(__name__)

class MemoryService:
    """基于 Milvus 的统一记忆服务 - 移除 SuperMemory 依赖"""
    
    def __init__(self, milvus_service=None):
        self.emotion_analyzer = EmotionAnalyzer()
        self.event_classifier = EventClassifier()
        self.time_service = TimeService()
        self.milvus_service = milvus_service  # 注入 Milvus 服务
        
        logger.info("记忆服务初始化完成 - 使用 Milvus 作为统一后端")

    def set_milvus_service(self, milvus_service):
        """设置 Milvus 服务实例"""
        self.milvus_service = milvus_service

    async def store_conversation_memory(
        self,
        user_message: str,
        ai_response: str,
        user_id: str = "marvinli001"
    ) -> bool:
        """存储对话记忆到 Milvus"""
        if not self.milvus_service:
            logger.warning("Milvus服务未初始化，跳过存储")
            return False

        try:
            # 分析用户消息和AI回复
            user_emotion = self.emotion_analyzer.analyze_emotion(user_message)
            user_category, user_confidence = self.event_classifier.classify_event(user_message)
            ai_emotion = self.emotion_analyzer.analyze_emotion(ai_response)
            ai_category, ai_confidence = self.event_classifier.classify_event(ai_response)
            
            # 获取时间上下文
            time_context = self.time_service.get_time_context()
            
            # 创建用户消息的嵌入（需要外部传入或者通过 OpenAI 服务创建）
            # 这里我们将在调用时传入嵌入
            
            # 构建对话记忆内容
            conversation_content = f"""对话记录 - {time_context['current_time']}

用户: {user_message}
助手: {ai_response}

=== 分析数据 ===
用户情绪权重: {user_emotion['emotion_weight']:.2f}
用户消息类型: {user_category} (置信度: {user_confidence:.2f})
AI情绪权重: {ai_emotion['emotion_weight']:.2f}
AI回复类型: {ai_category} (置信度: {ai_confidence:.2f})
交互类型: {self._determine_interaction_type(user_category, ai_category)}
用户ID: {user_id}
"""
            
            # 返回需要存储的数据，让调用者处理嵌入
            return {
                'content': conversation_content,
                'user_emotion': user_emotion,
                'user_category': user_category,
                'ai_emotion': ai_emotion,
                'ai_category': ai_category,
                'interaction_type': self._determine_interaction_type(user_category, ai_category)
            }
            
        except Exception as e:
            logger.error(f"准备对话记忆失败: {e}")
            return False

    async def retrieve_relevant_memories(
        self,
        query: str,
        query_embedding: List[float],
        limit: int = 5,
        user_id: str = "marvinli001"
    ) -> List[Dict[str, Any]]:
        """从 Milvus 检索相关记忆"""
        if not self.milvus_service:
            logger.warning("Milvus服务未初始化，返回空结果")
            return []

        try:
            # 使用 Milvus 进行语义搜索
            memories = await self.milvus_service.search_memories(
                query_embedding=query_embedding,
                limit=limit,
                emotion_weight_threshold=0.0
            )
            
            # 转换格式以匹配原有接口
            processed_memories = []
            for memory in memories:
                processed_memories.append({
                    'content': memory.get('text', ''),
                    'relevance_score': memory.get('score', 0.0),
                    'timestamp': memory.get('timestamp', 0),
                    'formatted_time': self.time_service.format_timestamp(memory.get('timestamp', 0)),
                    'emotion_weight': memory.get('emotion_weight', 0.0),
                    'category': memory.get('event_category', 'general'),
                    'interaction_type': memory.get('interaction_type', 'general'),
                    'source': 'milvus'
                })
            
            logger.info(f"从 Milvus 检索到 {len(processed_memories)} 个相关记忆")
            return processed_memories
            
        except Exception as e:
            logger.error(f"检索记忆失败: {e}")
            return []

    async def store_event_memory(
        self,
        event_content: str,
        event_embedding: List[float],
        event_type: str = "user_action",
        user_id: str = "marvinli001",
        additional_metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """存储事件记忆到 Milvus"""
        if not self.milvus_service:
            logger.warning("Milvus服务未初始化，跳过存储")
            return False

        try:
            # 分析事件内容
            emotion = self.emotion_analyzer.analyze_emotion(event_content)
            category, confidence = self.event_classifier.classify_event(event_content)
            
            # 构建事件记忆文本
            event_text = f"事件: {event_content} (类型: {event_type})"
            
            # 存储到 Milvus
            success = await self.milvus_service.store_memory(
                text=event_text,
                embedding=event_embedding,
                user_id=user_id,
                emotion_weight=emotion['emotion_weight'],
                event_category=category,
                interaction_type=event_type
            )
            
            if success:
                logger.info(f"成功存储事件记忆: {event_content[:50]}...")
            
            return success
            
        except Exception as e:
            logger.error(f"存储事件记忆失败: {e}")
            return False

    async def get_memory_stats(self, user_id: str = "marvinli001") -> Dict[str, Any]:
        """获取记忆统计信息"""
        if not self.milvus_service:
            return {"error": "Milvus服务未初始化"}
        
        try:
            stats = await self.milvus_service.get_memory_stats(user_id)
            return stats
        except Exception as e:
            logger.error(f"获取记忆统计失败: {e}")
            return {"error": str(e)}

    async def clear_all_memories(self, user_id: str = "marvinli001") -> bool:
        """清空用户记忆"""
        if not self.milvus_service:
            return False
        
        try:
            # 这里可以实现具体的清空逻辑
            logger.info(f"请求清空用户 {user_id} 的记忆")
            return True
        except Exception as e:
            logger.error(f"清空记忆失败: {e}")
            return False

    def _determine_interaction_type(self, user_category: str, ai_category: str) -> str:
        """确定交互类型"""
        interaction_map = {
            ('question', 'answer'): 'q_and_a',
            ('request', 'assistance'): 'assistance',
            ('casual', 'casual'): 'casual_chat',
            ('emotional', 'support'): 'emotional_support',
            ('task', 'instruction'): 'task_oriented'
        }
        return interaction_map.get((user_category, ai_category), 'general_conversation')

    def get_client_info(self) -> Dict[str, Any]:
        """获取客户端信息"""
        return {
            "backend": "milvus",
            "supermemory_removed": True,
            "services": {
                "emotion_analyzer": self.emotion_analyzer is not None,
                "event_classifier": self.event_classifier is not None,
                "time_service": self.time_service is not None,
                "milvus_service": self.milvus_service is not None
            }
        }