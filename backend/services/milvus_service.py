import os
import logging
from typing import List, Dict, Any
from pymilvus import connections, Collection, FieldSchema, CollectionSchema, DataType, utility
import numpy as np
from dotenv import load_dotenv
from services.openai_service import OpenAIService

load_dotenv()

logger = logging.getLogger(__name__)

class MilvusService:
    def __init__(self):
        self.collection_name = "yuzuriha_memories"
        self.collection = None
        self.openai_service = OpenAIService()
        
        # Zilliz Cloud connection parameters
        self.uri = os.getenv("MILVUS_URI")
        self.token = os.getenv("MILVUS_TOKEN")
        
    async def initialize(self):
        """Initialize connection to Milvus"""
        try:
            # Connect to Zilliz Cloud
            connections.connect(
                alias="default",
                uri=self.uri,
                token=self.token
            )
            
            # Create collection if it doesn't exist
            if not utility.has_collection(self.collection_name):
                await self._create_collection()
            else:
                self.collection = Collection(self.collection_name)
                self.collection.load()
                
            logger.info("Milvus service initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize Milvus: {e}")
            raise
    
    async def _create_collection(self):
        """Create the memories collection"""
        try:
            # Define schema
            fields = [
                FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=True),
                FieldSchema(name="text", dtype=DataType.VARCHAR, max_length=65535),
                FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=1536),  # text-embedding-3-small dimension
                FieldSchema(name="timestamp", dtype=DataType.VARCHAR, max_length=100),
                FieldSchema(name="type", dtype=DataType.VARCHAR, max_length=50),
                FieldSchema(name="user_id", dtype=DataType.VARCHAR, max_length=100)
            ]
            
            schema = CollectionSchema(fields=fields, description="Yuzuriha memory storage")
            
            # Create collection
            self.collection = Collection(name=self.collection_name, schema=schema)
            
            # Create index for vector search
            index_params = {
                "index_type": "IVF_FLAT",
                "metric_type": "COSINE",
                "params": {"nlist": 1024}
            }
            
            self.collection.create_index(field_name="embedding", index_params=index_params)
            self.collection.load()
            
            logger.info(f"Collection '{self.collection_name}' created successfully")
            
        except Exception as e:
            logger.error(f"Failed to create collection: {e}")
            raise
    
    async def health_check(self) -> bool:
        """Check Milvus connection health"""
        try:
            return utility.has_collection(self.collection_name)
        except Exception as e:
            logger.error(f"Milvus health check failed: {e}")
            return False
    
    async def store_conversation(self, user_message: str, assistant_response: str, timestamp: str):
        """Store conversation in vector database"""
        try:
            # Generate embeddings for both messages
            user_embedding = await self.openai_service.generate_embeddings(user_message)
            assistant_embedding = await self.openai_service.generate_embeddings(assistant_response)
            
            # Prepare data
            data = [
                {
                    "text": f"User: {user_message}",
                    "embedding": user_embedding,
                    "timestamp": timestamp,
                    "type": "user_message",
                    "user_id": "marvinli001"
                },
                {
                    "text": f"Assistant: {assistant_response}",
                    "embedding": assistant_embedding,
                    "timestamp": timestamp,
                    "type": "assistant_message",
                    "user_id": "marvinli001"
                }
            ]
            
            # Insert data
            self.collection.insert(data)
            self.collection.flush()
            
            logger.info("Conversation stored in Milvus successfully")
            
        except Exception as e:
            logger.error(f"Failed to store conversation in Milvus: {e}")
    
    async def search_similar(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Search for similar memories"""
        try:
            # Generate embedding for query
            query_embedding = await self.openai_service.generate_embeddings(query)
            
            # Search parameters
            search_params = {
                "metric_type": "COSINE",
                "params": {"nprobe": 10}
            }
            
            # Perform search
            results = self.collection.search(
                data=[query_embedding],
                anns_field="embedding",
                param=search_params,
                limit=limit,
                output_fields=["text", "timestamp", "type"]
            )
            
            memories = []
            for result in results[0]:
                memories.append({
                    "text": result.entity.get("text"),
                    "timestamp": result.entity.get("timestamp"),
                    "type": result.entity.get("type"),
                    "score": result.score
                })
            
            return memories
            
        except Exception as e:
            logger.error(f"Failed to search memories: {e}")
            return []
    
    async def clear_collection(self):
        """Clear all data from collection"""
        try:
            if self.collection:
                self.collection.drop()
                await self._create_collection()
                logger.info("Collection cleared successfully")
        except Exception as e:
            logger.error(f"Failed to clear collection: {e}")
            raise