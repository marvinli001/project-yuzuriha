import os
import httpx
import logging
from typing import List, Dict, Any
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

class MemoryService:
    def __init__(self):
        self.supermemory_api_url = os.getenv("SUPERMEMORY_API_URL")
        self.supermemory_api_key = os.getenv("SUPERMEMORY_API_KEY")
        
    async def health_check(self) -> bool:
        """Check SuperMemory MCP service health"""
        try:
            if not self.supermemory_api_url:
                return False
                
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.supermemory_api_url}/health",
                    headers={"Authorization": f"Bearer {self.supermemory_api_key}"},
                    timeout=5.0
                )
                return response.status_code == 200
        except Exception as e:
            logger.error(f"SuperMemory health check failed: {e}")
            return False
    
    async def store_conversation(self, user_message: str, assistant_response: str, timestamp: str):
        """Store conversation in SuperMemory MCP"""
        try:
            if not self.supermemory_api_url:
                logger.warning("SuperMemory API URL not configured")
                return
                
            # Format the conversation for storage
            conversation_data = {
                "content": f"Conversation at {timestamp}\nUser: {user_message}\nAssistant: {assistant_response}",
                "timestamp": timestamp,
                "type": "conversation",
                "user_id": "marvinli001",
                "metadata": {
                    "user_message": user_message,
                    "assistant_response": assistant_response,
                    "source": "yuzuriha_chat"
                }
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.supermemory_api_url}/api/memories",
                    json=conversation_data,
                    headers={"Authorization": f"Bearer {self.supermemory_api_key}"},
                    timeout=10.0
                )
                
                if response.status_code == 200:
                    logger.info("Conversation stored in SuperMemory successfully")
                else:
                    logger.error(f"Failed to store in SuperMemory: {response.status_code}")
                    
        except Exception as e:
            logger.error(f"Failed to store conversation in SuperMemory: {e}")
    
    async def get_recent_memories(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent memories from SuperMemory"""
        try:
            if not self.supermemory_api_url:
                return []
                
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.supermemory_api_url}/api/memories",
                    params={"limit": limit, "user_id": "marvinli001"},
                    headers={"Authorization": f"Bearer {self.supermemory_api_key}"},
                    timeout=10.0
                )
                
                if response.status_code == 200:
                    return response.json().get("memories", [])
                else:
                    logger.error(f"Failed to get memories: {response.status_code}")
                    return []
                    
        except Exception as e:
            logger.error(f"Failed to get memories from SuperMemory: {e}")
            return []
    
    async def clear_memories(self):
        """Clear all memories from SuperMemory"""
        try:
            if not self.supermemory_api_url:
                return
                
            async with httpx.AsyncClient() as client:
                response = await client.delete(
                    f"{self.supermemory_api_url}/api/memories",
                    params={"user_id": "marvinli001"},
                    headers={"Authorization": f"Bearer {self.supermemory_api_key}"},
                    timeout=10.0
                )
                
                if response.status_code == 200:
                    logger.info("Memories cleared from SuperMemory successfully")
                else:
                    logger.error(f"Failed to clear memories: {response.status_code}")
                    
        except Exception as e:
            logger.error(f"Failed to clear memories from SuperMemory: {e}")