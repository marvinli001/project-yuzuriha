import os
import logging
from typing import List, Dict, Any, Optional
import supermemory
from services.emotion_service import EmotionAnalyzer, EventClassifier
from services.time_service import TimeService

logger = logging.getLogger(__name__)

class MemoryService:
    def __init__(self):
        self.api_key = os.getenv('SUPERMEMORY_API_KEY')
        self.enabled = bool(self.api_key)
        
        if self.enabled:
            try:
                # 按照官方文档初始化客户端
                self.client = supermemory.Client(api_key=self.api_key)
                logger.info("SuperMemory客户端初始化成功")
            except Exception as e:
                logger.error(f"SuperMemory客户端初始化失败: {e}")
                self.enabled = False
                self.client = None
        else:
            self.client = None
        
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
        """存储完整对话记忆 - 修复版本"""
        if not self.enabled or not self.client:
            logger.info("SuperMemory未启用，跳过存储")
            return True

        try:
            # 分析用户消息和AI回复（保留用于元数据）
            user_emotion = self.emotion_analyzer.analyze_emotion(user_message)
            user_category, user_confidence = self.event_classifier.classify_event(user_message)
            ai_emotion = self.emotion_analyzer.analyze_emotion(ai_response)
            ai_category, ai_confidence = self.event_classifier.classify_event(ai_response)
            
            # 获取时间上下文
            time_context = self.time_service.get_time_context()
            
            # 构建简化的记忆内容 - 减少复杂性，避免API错误
            memory_content = f"""对话记录 - {time_context['current_time']}

用户: {user_message}
助手: {ai_response}

=== 元数据 ===
用户ID: {user_id}
时间戳: {time_context['timestamp']}
用户情绪权重: {user_emotion['emotion_weight']:.2f}
用户消息类型: {user_category} (置信度: {user_confidence:.2f})
AI情绪权重: {ai_emotion['emotion_weight']:.2f}
AI回复类型: {ai_category} (置信度: {ai_confidence:.2f})
交互类型: {self._determine_interaction_type(user_category, ai_category)}
"""

            # 使用正确的 SuperMemory API 调用方式
            result = self.client.add(content=memory_content)
            
            logger.info(f"成功存储对话记忆到SuperMemory")
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
        """存储事件记忆 - 修复版本"""
        if not self.enabled or not self.client:
            return True

        try:
            # 分析事件内容
            emotion = self.emotion_analyzer.analyze_emotion(event_content)
            category, confidence = self.event_classifier.classify_event(event_content)
            time_context = self.time_service.get_time_context()
            
            # 构建简化的事件记忆内容
            event_memory_content = f"""事件记录 - {time_context['current_time']}

事件内容: {event_content}
事件类型: {event_type}

=== 元数据 ===
用户ID: {user_id}
时间戳: {time_context['timestamp']}
情绪权重: {emotion['emotion_weight']:.2f}
事件分类: {category} (置信度: {confidence:.2f})
额外信息: {additional_metadata if additional_metadata else '无'}
"""
            
            # 使用正确的 SuperMemory API 调用
            result = self.client.add(content=event_memory_content)
            
            logger.info(f"成功存储事件记忆到SuperMemory")
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
        """检索相关记忆 - 修复搜索 API 调用"""
        if not self.enabled or not self.client:
            return []

        try:
            # 使用正确的搜索 API
            results = self.client.search(q=query, limit=limit)
            
            processed_memories = []
            
            # 处理搜索结果
            if hasattr(results, 'results'):
                memories_data = results.results
            elif isinstance(results, list):
                memories_data = results
            else:
                # 如果结果格式不明确，尝试转换
                memories_data = [results] if results else []
            
            for memory in memories_data[:limit]:
                try:
                    # 提取内容
                    if hasattr(memory, 'content'):
                        content = memory.content
                    elif isinstance(memory, dict):
                        content = memory.get('content', memory.get('text', str(memory)))
                    else:
                        content = str(memory)
                    
                    # 过滤出用户相关的记忆（可选）
                    processed_memories.append({
                        'content': content[:500] + '...' if len(content) > 500 else content,
                        'relevance_score': getattr(memory, 'score', 0.8),  # 默认相关度
                        'timestamp': self.time_service.get_current_time().timestamp(),
                        'formatted_time': self.time_service.get_formatted_time(),
                        'emotion_weight': 0.5,  # 默认情绪权重
                        'category': 'general'
                    })
                except Exception as memory_error:
                    logger.warning(f"处理单个记忆时出错: {memory_error}")
                    continue
            
            logger.info(f"从SuperMemory检索到 {len(processed_memories)} 个相关记忆")
            return processed_memories
            
        except Exception as e:
            logger.error(f"检索记忆失败: {e}")
            return []

    async def clear_all_memories(self, user_id: str = "marvinli001") -> bool:
        """清空所有记忆（注意：SuperMemory可能不支持按用户删除）"""
        if not self.enabled or not self.client:
            return True

        try:
            # SuperMemory的删除功能可能有限，这里记录警告
            logger.warning("SuperMemory可能不支持批量删除特定用户的记忆")
            logger.info(f"请求清空用户 {user_id} 的记忆（操作可能不被支持）")
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
            "enabled": self.enabled,
            "client_available": self.client is not None,
            "api_key_configured": bool(self.api_key),
            "version": "3.0.0a23",
            "status": "pre-release" if self.enabled else "disabled"
        }

    def get_service_status(self) -> Dict[str, Any]:
        """获取服务状态"""
        return {
            "supermemory": {
                "enabled": self.enabled,
                "client_ready": self.client is not None,
                "api_key_set": bool(self.api_key)
            },
            "emotion_analyzer": {
                "ready": self.emotion_analyzer is not None
            },
            "event_classifier": {
                "ready": self.event_classifier is not None
            },
            "time_service": {
                "ready": self.time_service is not None
            }
        }