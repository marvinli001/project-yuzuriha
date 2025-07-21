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
            collections = self.client.list_collections()
            if self.collection_name in collections:
                logger.info(f"集合 {self.collection_name} 已存在")
                return

            # 使用简化的集合创建方式
            self.client.create_collection(
                collection_name=self.collection_name,
                dimension=self.embedding_dim,
                metric_type="COSINE",
                auto_id=True,
                consistency_level="Strong"
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
            current_timestamp = int(time.time() * 1000)  # 毫秒时间戳
            
            # 准备要插入的数据
            data = [{
                "vector": embedding,
                "text": text,
                "timestamp": current_timestamp,
                "user_id": user_id,
                "emotion_weight": emotion_weight,
                "event_category": event_category,
                "interaction_type": interaction_type
            }]
            
            # 插入数据
            result = self.client.insert(
                collection_name=self.collection_name,
                data=data
            )
            
            logger.info(f"成功存储记忆: {text[:50]}...")
            return True
            
        except Exception as e:
            logger.error(f"存储记忆失败: {e}")
            return False

    async def search_memories(
        self,
        query_embedding: List[float],
        limit: int = 5,
        emotion_weight_threshold: float = 0.0,
        user_id: str = None
    ) -> List[Dict[str, Any]]:
        """搜索相似记忆 - 增强版本"""
        try:
            # 构建搜索参数
            search_params = {
                "metric_type": "COSINE",
                "params": {"nprobe": 10}
            }
            
            # 构建过滤条件
            filter_conditions = []
            if emotion_weight_threshold > 0:
                filter_conditions.append(f"emotion_weight >= {emotion_weight_threshold}")
            if user_id:
                filter_conditions.append(f'user_id == "{user_id}"')
            
            filter_expr = " and ".join(filter_conditions) if filter_conditions else None
            
            # 执行搜索
            results = self.client.search(
                collection_name=self.collection_name,
                data=[query_embedding],
                search_params=search_params,
                limit=limit,
                filter=filter_expr,
                output_fields=["text", "timestamp", "user_id", "emotion_weight", "event_category", "interaction_type"]
            )
            
            # 处理搜索结果
            memories = []
            if results and len(results) > 0:
                for hit in results[0]:
                    memory = {
                        "text": hit.get("entity", {}).get("text", "") or hit.get("text", ""),
                        "score": float(hit.get("distance", 0.0)),
                        "timestamp": hit.get("entity", {}).get("timestamp", 0) or hit.get("timestamp", 0),
                        "user_id": hit.get("entity", {}).get("user_id", "") or hit.get("user_id", ""),
                        "emotion_weight": hit.get("entity", {}).get("emotion_weight", 0.0) or hit.get("emotion_weight", 0.0),
                        "event_category": hit.get("entity", {}).get("event_category", "general") or hit.get("event_category", "general"),
                        "interaction_type": hit.get("entity", {}).get("interaction_type", "general") or hit.get("interaction_type", "general")
                    }
                    memories.append(memory)
            
            logger.info(f"搜索到 {len(memories)} 条相关记忆")
            return memories
            
        except Exception as e:
            logger.error(f"搜索记忆失败: {e}")
            return []

    async def get_memory_stats(self, user_id: str = "marvinli001") -> Dict[str, Any]:
        """获取记忆统计信息"""
        try:
            # 获取集合统计信息
            stats = self.client.get_collection_stats(collection_name=self.collection_name)
            
            # 查询用户的记忆数量
            user_memories = self.client.query(
                collection_name=self.collection_name,
                filter=f'user_id == "{user_id}"',
                output_fields=["event_category"],
                limit=1000
            )
            
            # 统计类别分布
            category_distribution = {}
            for memory in user_memories:
                category = memory.get("event_category", "unknown")
                category_distribution[category] = category_distribution.get(category, 0) + 1
            
            return {
                "total_memories": stats.get("row_count", 0),
                "user_memories": len(user_memories),
                "category_distribution": category_distribution,
                "collection_name": self.collection_name,
                "backend": "milvus_only"
            }
            
        except Exception as e:
            logger.error(f"获取记忆统计失败: {e}")
            return {
                "total_memories": 0,
                "user_memories": 0,
                "category_distribution": {},
                "error": str(e),
                "backend": "milvus_only"
            }

    def get_client_info(self) -> Dict[str, Any]:
        """获取客户端信息"""
        return {
            "connected": self.client is not None,
            "collection_name": self.collection_name,
            "embedding_dim": self.embedding_dim,
            "uri_configured": bool(self.uri),
            "backend": "milvus_only"
        }