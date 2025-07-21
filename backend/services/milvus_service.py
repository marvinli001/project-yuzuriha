import os
import logging
import time
from typing import List, Dict, Any
from pymilvus import connections, Collection, utility, FieldSchema, CollectionSchema, DataType

logger = logging.getLogger(__name__)

class MilvusService:
    def __init__(self):
        self.uri = os.getenv('MILVUS_URI')
        self.token = os.getenv('MILVUS_TOKEN')
        
        if not self.uri or not self.token:
            raise ValueError("MILVUS_URI 和 MILVUS_TOKEN 环境变量是必需的")
        
        self.collection_name = "yuzuriha_memories"
        self.collection = None
        
    async def initialize(self):
        """初始化连接和集合"""
        try:
            # 连接到 Milvus
            connections.connect(
                alias="default",
                uri=self.uri,
                token=self.token
            )
            logger.info("成功连接到 Milvus")
            
            # 创建或加载集合
            await self._create_collection()
            
        except Exception as e:
            logger.error(f"Milvus 初始化失败: {e}")
            raise
    
    async def _create_collection(self):
        """创建集合（如果不存在）"""
        try:
            if utility.has_collection(self.collection_name):
                self.collection = Collection(self.collection_name)
                logger.info(f"加载现有集合: {self.collection_name}")
                return
            
            # 定义集合架构
            fields = [
                FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=True),
                FieldSchema(name="text", dtype=DataType.VARCHAR, max_length=65535),
                FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=1536),
                FieldSchema(name="timestamp", dtype=DataType.INT64),
                FieldSchema(name="user_id", dtype=DataType.VARCHAR, max_length=255)
            ]
            
            schema = CollectionSchema(
                fields, 
                description="Yuzuriha 记忆存储集合"
            )
            
            # 创建集合
            self.collection = Collection(
                name=self.collection_name,
                schema=schema
            )
            
            # 创建索引
            index_params = {
                "metric_type": "COSINE",
                "index_type": "HNSW",
                "params": {
                    "M": 16,
                    "efConstruction": 200
                }
            }
            
            self.collection.create_index(
                field_name="embedding",
                index_params=index_params
            )
            
            logger.info(f"成功创建集合: {self.collection_name}")
            
        except Exception as e:
            logger.error(f"创建集合失败: {e}")
            raise

    async def store_memory(self, text: str, embedding: List[float], user_id: str = "marvinli001") -> bool:
        """存储记忆到 Milvus"""
        try:
            timestamp = int(time.time() * 1000)
            
            data = [
                [text],              # text
                [embedding],         # embedding  
                [timestamp],         # timestamp
                [user_id]           # user_id
            ]
            
            result = self.collection.insert(data)
            self.collection.flush()
            
            logger.info(f"成功存储记忆，ID: {result.primary_keys}")
            return True
            
        except Exception as e:
            logger.error(f"存储记忆失败: {e}")
            return False

    async def search_memories(self, query_embedding: List[float], limit: int = 3, user_id: str = "marvinli001") -> List[Dict[str, Any]]:
        """搜索相似记忆"""
        try:
            # 加载集合到内存
            self.collection.load()
            
            # 搜索参数
            search_params = {
                "metric_type": "COSINE",
                "params": {
                    "ef": 100
                }
            }
            
            # 执行搜索
            results = self.collection.search(
                data=[query_embedding],
                anns_field="embedding",
                param=search_params,
                limit=limit,
                expr=f'user_id == "{user_id}"',
                output_fields=["text", "timestamp", "user_id"]
            )
            
            memories = []
            for result in results[0]:
                # 设置相似度阈值
                if result.score > 0.75:
                    memories.append({
                        "text": result.entity.get("text"),
                        "score": result.score,
                        "timestamp": result.entity.get("timestamp"),
                        "user_id": result.entity.get("user_id")
                    })
            
            logger.info(f"找到 {len(memories)} 个相关记忆")
            return memories
            
        except Exception as e:
            logger.error(f"搜索记忆失败: {e}")
            return []

    async def clear_memories(self, user_id: str = "marvinli001") -> bool:
        """清空用户的所有记忆"""
        try:
            # 删除指定用户的记忆
            self.collection.delete(expr=f'user_id == "{user_id}"')
            self.collection.flush()
            
            logger.info(f"成功清空用户 {user_id} 的记忆")
            return True
            
        except Exception as e:
            logger.error(f"清空记忆失败: {e}")
            return False

    async def get_memory_count(self, user_id: str = "marvinli001") -> int:
        """获取记忆数量"""
        try:
            self.collection.load()
            count = self.collection.query(
                expr=f'user_id == "{user_id}"',
                output_fields=["count(*)"]
            )
            return count[0]["count(*)"] if count else 0
            
        except Exception as e:
            logger.error(f"获取记忆数量失败: {e}")
            return 0