import os
import logging
import time
from typing import List, Dict, Any
from pymilvus import MilvusClient, DataType

logger = logging.getLogger(__name__)

class MilvusService:
    def __init__(self):
        self.uri = os.getenv('MILVUS_URI')
        self.token = os.getenv('MILVUS_TOKEN')
        self.collection_name = os.getenv('MILVUS_COLLECTION_NAME', 'yuzuriha_memories')
        
        if not self.uri or not self.token:
            raise ValueError("MILVUS_URI 和 MILVUS_TOKEN 环境变量是必需的")
        
        self.client = None
        self.embedding_dim = 1536  # text-embedding-3-small 的维度

    async def initialize(self):
        """初始化Milvus客户端和集合"""
        try:
            # 创建Milvus客户端
            self.client = MilvusClient(
                uri=self.uri,
                token=self.token
            )
            
            logger.info("成功连接到 Zilliz Cloud")
            
            # 创建集合（如果不存在）
            await self._create_collection()
            
        except Exception as e:
            logger.error(f"Milvus 初始化失败: {e}")
            raise

    async def _create_collection(self):
        """根据Zilliz Cloud文档创建集合"""
        try:
            # 检查集合是否存在
            if self.client.has_collection(collection_name=self.collection_name):
                logger.info(f"集合 {self.collection_name} 已存在")
                return

            # 创建集合架构
            schema = self.client.create_schema(
                auto_id=True,
                enable_dynamic_field=True,
            )

            # 添加字段
            schema.add_field(field_name="id", datatype=DataType.INT64, is_primary=True)
            schema.add_field(field_name="text", datatype=DataType.VARCHAR, max_length=65535)
            schema.add_field(field_name="embedding", datatype=DataType.FLOAT_VECTOR, dim=self.embedding_dim)
            schema.add_field(field_name="timestamp", datatype=DataType.INT64)
            schema.add_field(field_name="user_id", datatype=DataType.VARCHAR, max_length=255)
            schema.add_field(field_name="emotion_weight", datatype=DataType.DOUBLE)
            schema.add_field(field_name="event_category", datatype=DataType.VARCHAR, max_length=100)
            schema.add_field(field_name="interaction_type", datatype=DataType.VARCHAR, max_length=100)

            # 准备索引参数
            index_params = self.client.prepare_index_params()

            # 为向量字段添加索引
            index_params.add_index(
                field_name="embedding",
                index_type="AUTOINDEX",  # Zilliz Cloud推荐的自动索引
                metric_type="COSINE"
            )

            # 创建集合
            self.client.create_collection(
                collection_name=self.collection_name,
                schema=schema,
                index_params=index_params
            )

            logger.info(f"成功创建集合: {self.collection_name}")

        except Exception as e:
            logger.error(f"创建集合失败: {e}")
            raise

    async def store_memory(
        self,
        text: str,
        embedding: List[float],
        user_id: str = "marvinli001",
        emotion_weight: float = 0.0,
        event_category: str = "general",
        interaction_type: str = "general_conversation"
    ) -> bool:
        """存储记忆到Milvus"""
        try:
            timestamp = int(time.time() * 1000)
            
            data = [{
                "text": text,
                "embedding": embedding,
                "timestamp": timestamp,
                "user_id": user_id,
                "emotion_weight": emotion_weight,
                "event_category": event_category,
                "interaction_type": interaction_type
            }]

            result = self.client.insert(
                collection_name=self.collection_name,
                data=data
            )

            logger.info(f"成功存储记忆，插入了 {result['insert_count']} 条记录")
            return True

        except Exception as e:
            logger.error(f"存储记忆失败: {e}")
            return False

    async def search_memories(
        self,
        query_embedding: List[float],
        limit: int = 5,
        user_id: str = "marvinli001",
        emotion_weight_threshold: float = 0.0
    ) -> List[Dict[str, Any]]:
        """搜索相似记忆"""
        try:
            # 构建搜索参数
            search_params = {
                "metric_type": "COSINE",
                "params": {
                    "level": 1  # Zilliz Cloud AUTOINDEX 搜索参数
                }
            }

            # 构建过滤条件
            filter_expr = f'user_id == "{user_id}"'
            if emotion_weight_threshold > 0:
                filter_expr += f' && emotion_weight >= {emotion_weight_threshold}'

            results = self.client.search(
                collection_name=self.collection_name,
                data=[query_embedding],
                anns_field="embedding",
                search_params=search_params,
                limit=limit,
                expr=filter_expr,
                output_fields=[
                    "text", "timestamp", "user_id", 
                    "emotion_weight", "event_category", "interaction_type"
                ]
            )

            memories = []
            for result in results[0]:
                # 设置相似度阈值
                if result['distance'] <= 0.3:  # COSINE距离，越小越相似
                    entity = result['entity']
                    memories.append({
                        "text": entity.get("text"),
                        "score": 1 - result['distance'],  # 转换为相似度分数
                        "timestamp": entity.get("timestamp"),
                        "user_id": entity.get("user_id"),
                        "emotion_weight": entity.get("emotion_weight"),
                        "event_category": entity.get("event_category"),
                        "interaction_type": entity.get("interaction_type")
                    })

            logger.info(f"找到 {len(memories)} 个相关记忆")
            return memories

        except Exception as e:
            logger.error(f"搜索记忆失败: {e}")
            return []

    async def get_memories_by_category(
        self,
        category: str,
        user_id: str = "marvinli001",
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """根据事件类别获取记忆"""
        try:
            filter_expr = f'user_id == "{user_id}" && event_category == "{category}"'
            
            results = self.client.query(
                collection_name=self.collection_name,
                expr=filter_expr,
                output_fields=[
                    "text", "timestamp", "emotion_weight", 
                    "event_category", "interaction_type"
                ],
                limit=limit
            )

            memories = []
            for result in results:
                memories.append({
                    "text": result.get("text"),
                    "timestamp": result.get("timestamp"),
                    "emotion_weight": result.get("emotion_weight"),
                    "event_category": result.get("event_category"),
                    "interaction_type": result.get("interaction_type")
                })

            return memories

        except Exception as e:
            logger.error(f"按类别获取记忆失败: {e}")
            return []

    async def clear_memories(self, user_id: str = "marvinli001") -> bool:
        """清空用户的所有记忆"""
        try:
            filter_expr = f'user_id == "{user_id}"'
            
            self.client.delete(
                collection_name=self.collection_name,
                expr=filter_expr
            )

            logger.info(f"成功清空用户 {user_id} 的记忆")
            return True

        except Exception as e:
            logger.error(f"清空记忆失败: {e}")
            return False

    async def get_memory_stats(self, user_id: str = "marvinli001") -> Dict[str, Any]:
        """获取记忆统计信息"""
        try:
            # 获取总数
            total_count = self.client.query(
                collection_name=self.collection_name,
                expr=f'user_id == "{user_id}"',
                output_fields=["count(*)"]
            )

            # 获取各类别统计
            categories = ["question", "task", "conversation", "information", "creative", "analysis", "emotional"]
            category_stats = {}
            
            for category in categories:
                count = self.client.query(
                    collection_name=self.collection_name,
                    expr=f'user_id == "{user_id}" && event_category == "{category}"',
                    output_fields=["count(*)"]
                )
                category_stats[category] = len(count)

            return {
                "total_memories": len(total_count),
                "category_distribution": category_stats,
                "user_id": user_id
            }

        except Exception as e:
            logger.error(f"获取记忆统计失败: {e}")
            return {"total_memories": 0, "category_distribution": {}, "user_id": user_id}