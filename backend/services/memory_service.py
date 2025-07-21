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
                self.client = supermemory.Client(
                    api_key=self.api_key
                )
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
        """存储完整对话记忆"""
        if not self.enabled or not self.client:
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
            
            # 构建记忆内容 - 按照官方文档格式
            memory_content = f"""对话记录 - {time_context['current_time']}

用户消息: {user_message}
AI回复: {ai_response}

=== 分析数据 ===
用户情绪分析:
- 正面情绪: {user_emotion['positive']:.2f}
- 负面情绪: {user_emotion['negative']:.2f}
- 中性情绪: {user_emotion['neutral']:.2f}
- 复合情绪分数: {user_emotion['compound']:.2f}
- 情绪权重: {user_emotion['emotion_weight']:.2f}

用户消息分类: {user_category} (置信度: {user_confidence:.2f})
消息复杂度: {user_complexity:.2f}

AI回复分析:
- 正面情绪: {ai_emotion['positive']:.2f}
- 负面情绪: {ai_emotion['negative']:.2f}
- 中性情绪: {ai_emotion['neutral']:.2f}
- 复合情绪分数: {ai_emotion['compound']:.2f}
- 情绪权重: {ai_emotion['emotion_weight']:.2f}

AI回复分类: {ai_category} (置信度: {ai_confidence:.2f})
回复复杂度: {ai_complexity:.2f}

=== 上下文信息 ===
用户ID: {user_id}
时间戳: {time_context['timestamp']}
时区: {time_context['timezone']}
星期: {time_context['weekday']}
交互类型: {self._determine_interaction_type(user_category, ai_category)}
总体情绪权重: {(user_emotion['emotion_weight'] + ai_emotion['emotion_weight']) / 2:.2f}
"""

            # 按照官方文档存储记忆
            result = self.client.memory.add(
                content=memory_content
            )
            
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
        """存储事件记忆"""
        if not self.enabled or not self.client:
            return True

        try:
            # 分析事件内容
            emotion = self.emotion_analyzer.analyze_emotion(event_content)
            category, confidence = self.event_classifier.classify_event(event_content)
            complexity = self.event_classifier.get_complexity_score(event_content)
            time_context = self.time_service.get_time_context()
            
            # 构建事件记忆内容
            event_memory_content = f"""事件记录 - {time_context['current_time']}

事件内容: {event_content}
事件类型: {event_type}

=== 分析数据 ===
情绪分析:
- 正面情绪: {emotion['positive']:.2f}
- 负面情绪: {emotion['negative']:.2f}
- 中性情绪: {emotion['neutral']:.2f}
- 复合情绪分数: {emotion['compound']:.2f}
- 情绪权重: {emotion['emotion_weight']:.2f}

事件分类: {category} (置信度: {confidence:.2f})
内容复杂度: {complexity:.2f}

=== 上下文信息 ===
用户ID: {user_id}
时间戳: {time_context['timestamp']}
时区: {time_context['timezone']}
星期: {time_context['weekday']}

=== 额外元数据 ===
{additional_metadata if additional_metadata else '无'}
"""
            
            result = self.client.memory.add(
                content=event_memory_content
            )
            
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
        """检索相关记忆"""
        if not self.enabled or not self.client:
            return []

        try:
            # 按照官方文档执行搜索
            results = self.client.search.execute(
                q=query
            )
            
            processed_memories = []
            memory_count = 0
            
            # 处理搜索结果
            if hasattr(results, 'results') or isinstance(results, list):
                memories_data = results.results if hasattr(results, 'results') else results
                
                for memory in memories_data[:limit]:
                    if memory_count >= limit:
                        break
                        
                    # 提取内容
                    content = ""
                    if hasattr(memory, 'content'):
                        content = memory.content
                    elif isinstance(memory, dict):
                        content = memory.get('content', '')
                    
                    # 过滤出用户相关的记忆
                    if user_id in content or not content:
                        processed_memories.append({
                            'content': content[:500] + '...' if len(content) > 500 else content,
                            'relevance_score': getattr(memory, 'score', 0.8),  # 默认相关度
                            'timestamp': self.time_service.get_current_time().timestamp(),
                            'formatted_time': self.time_service.get_formatted_time(),
                            'emotion_weight': 0.5,  # 从内容中提取或默认值
                            'category': 'general'
                        })
                        memory_count += 1
            
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

    def get_client_info(self) -> Dict[str, Any]:
        """获取客户端信息"""
        return {
            'enabled': self.enabled,
            'client_available': self.client is not None,
            'api_key_configured': bool(self.api_key)
        }