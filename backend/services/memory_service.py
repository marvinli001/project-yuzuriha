import os
import logging
from typing import List, Dict, Any, Optional
from supermemory import Supermemory
from services.emotion_service import EmotionAnalyzer, EventClassifier
from services.time_service import TimeService

logger = logging.getLogger(__name__)

class MemoryService:
    def __init__(self):
        self.api_key = os.getenv('SUPERMEMORY_API_KEY')
        self.enabled = bool(self.api_key)
        
        if self.enabled:
            self.client = Supermemory(api_key=self.api_key)
        
        self.emotion_analyzer = EmotionAnalyzer()
        self.event_classifier = EventClassifier()
        self.time_service = TimeService()
        
        logger.info(f"SuperMemory服务已{'启用' if self.enabled else '禁用'}")

    async def store_conversation_memory(
        self,
        user_message: str,
        ai_response: str,
        user_id: str = "marvinli001"
    ) -> bool:
        """存储完整对话记忆"""
        if not self.enabled:
            logger.info("SuperMemory未启用，跳过存储")
            return True

        try:
            # 分析用户消息
            user_emotion = self.emotion_analyzer.analyze_emotion(user_message)
            user_category, user_confidence = self.event_classifier.classify_event(user_message)
            user_complexity = self.event_classifier.get_complexity_score(user_message)
            
            # 分析AI回复
            ai_emotion = self.emotion_analyzer.analyze_emotion(ai_response)
            ai_category, ai_confidence = self.event_classifier.classify_event(ai_response)
            ai_complexity = self.event_classifier.get_complexity_score(ai_response)
            
            # 获取时间上下文
            time_context = self.time_service.get_time_context()
            
            # 构建完整的记忆内容
            memory_content = {
                'conversation': {
                    'user_message': user_message,
                    'ai_response': ai_response,
                },
                'user_analysis': {
                    'emotion': user_emotion,
                    'category': user_category,
                    'category_confidence': user_confidence,
                    'complexity': user_complexity
                },
                'ai_analysis': {
                    'emotion': ai_emotion,
                    'category': ai_category,
                    'category_confidence': ai_confidence,
                    'complexity': ai_complexity
                },
                'context': {
                    'user_id': user_id,
                    'timestamp': time_context['timestamp'],
                    'formatted_time': time_context['current_time'],
                    'timezone': time_context['timezone'],
                    'weekday': time_context['weekday']
                },
                'metadata': {
                    'conversation_length': len(user_message) + len(ai_response),
                    'user_message_length': len(user_message),
                    'ai_response_length': len(ai_response),
                    'overall_emotion_weight': (user_emotion['emotion_weight'] + ai_emotion['emotion_weight']) / 2,
                    'interaction_type': self._determine_interaction_type(user_category, ai_category)
                }
            }
            
            # 存储到SuperMemory
            result = self.client.memories.add({
                'content': f"用户: {user_message}\n助手: {ai_response}",
                'metadata': memory_content,
                'tags': [user_category, ai_category, time_context['weekday'].lower()],
                'emotion_weight': memory_content['metadata']['overall_emotion_weight']
            })
            
            logger.info(f"成功存储对话记忆，ID: {result.get('id', 'unknown')}")
            return True
            
        except Exception as e:
            logger.error(f"存储对话记忆失败: {e}")
            return False

    async def store_event_memory(
        self,
        event_content: str,
        event_type: str = "user_action",
        user_id: str = "marvinli001",
        additional_metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """存储事件记忆"""
        if not self.enabled:
            return True

        try:
            # 分析事件内容
            emotion = self.emotion_analyzer.analyze_emotion(event_content)
            category, confidence = self.event_classifier.classify_event(event_content)
            complexity = self.event_classifier.get_complexity_score(event_content)
            time_context = self.time_service.get_time_context()
            
            # 构建事件记忆
            event_memory = {
                'event': {
                    'content': event_content,
                    'type': event_type,
                },
                'analysis': {
                    'emotion': emotion,
                    'category': category,
                    'category_confidence': confidence,
                    'complexity': complexity
                },
                'context': {
                    'user_id': user_id,
                    'timestamp': time_context['timestamp'],
                    'formatted_time': time_context['current_time'],
                    'timezone': time_context['timezone'],
                    'weekday': time_context['weekday']
                },
                'metadata': additional_metadata or {}
            }
            
            result = self.client.memories.add({
                'content': event_content,
                'metadata': event_memory,
                'tags': [event_type, category, time_context['weekday'].lower()],
                'emotion_weight': emotion['emotion_weight']
            })
            
            logger.info(f"成功存储事件记忆，ID: {result.get('id', 'unknown')}")
            return True
            
        except Exception as e:
            logger.error(f"存储事件记忆失败: {e}")
            return False

    async def retrieve_relevant_memories(
        self,
        query: str,
        limit: int = 5,
        user_id: str = "marvinli001"
    ) -> List[Dict[str, Any]]:
        """检索相关记忆"""
        if not self.enabled:
            return []

        try:
            results = self.client.memories.search({
                'query': query,
                'limit': limit,
                'filter': {'user_id': user_id}
            })
            
            processed_memories = []
            for memory in results.get('memories', []):
                processed_memories.append({
                    'content': memory.get('content', ''),
                    'relevance_score': memory.get('score', 0.0),
                    'timestamp': memory.get('metadata', {}).get('context', {}).get('timestamp'),
                    'formatted_time': memory.get('metadata', {}).get('context', {}).get('formatted_time'),
                    'emotion_weight': memory.get('metadata', {}).get('metadata', {}).get('overall_emotion_weight', 0.0),
                    'category': memory.get('metadata', {}).get('user_analysis', {}).get('category', 'general')
                })
            
            logger.info(f"检索到 {len(processed_memories)} 个相关记忆")
            return processed_memories
            
        except Exception as e:
            logger.error(f"检索记忆失败: {e}")
            return []

    async def clear_all_memories(self, user_id: str = "marvinli001") -> bool:
        """清空所有记忆"""
        if not self.enabled:
            return True

        try:
            result = self.client.memories.delete_all({
                'filter': {'user_id': user_id}
            })
            logger.info(f"成功清空用户 {user_id} 的所有记忆")
            return True
        except Exception as e:
            logger.error(f"清空记忆失败: {e}")
            return False

    def _determine_interaction_type(self, user_category: str, ai_category: str) -> str:
        """确定交互类型"""
        if user_category == 'question' and ai_category == 'information':
            return 'q_and_a'
        elif user_category == 'task':
            return 'task_assistance'
        elif user_category == 'emotional':
            return 'emotional_support'
        elif user_category == 'creative':
            return 'creative_collaboration'
        else:
            return 'general_conversation'