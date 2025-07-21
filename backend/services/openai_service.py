import os
import httpx
import logging
from typing import List, Dict, Any
from models.chat_models import Message

logger = logging.getLogger(__name__)

class OpenAIService:
    def __init__(self):
        self.api_key = os.getenv('OPENAI_API_KEY')
        self.base_url = "https://api.openai.com/v1"
        
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY environment variable is required")

    async def generate_response(self, context: str) -> str:
        """Generate response using OpenAI GPT-4o"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": "gpt-4o",
                        "messages": [
                            {"role": "system", "content": context}
                        ],
                        "max_tokens": 2000,
                        "temperature": 0.7,
                        "stream": False
                    },
                    timeout=30.0
                )
                
                if response.status_code != 200:
                    logger.error(f"OpenAI API error: {response.status_code} - {response.text}")
                    raise Exception(f"OpenAI API error: {response.status_code}")
                
                data = response.json()
                return data["choices"][0]["message"]["content"]
                
        except Exception as e:
            logger.error(f"Error generating OpenAI response: {e}")
            raise

    async def create_embedding(self, text: str) -> List[float]:
        """Create embedding using OpenAI text-embedding-3-small"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/embeddings",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": "text-embedding-3-small",
                        "input": text,
                        "encoding_format": "float"
                    },
                    timeout=30.0
                )
                
                if response.status_code != 200:
                    logger.error(f"OpenAI Embedding API error: {response.status_code} - {response.text}")
                    raise Exception(f"OpenAI Embedding API error: {response.status_code}")
                
                data = response.json()
                return data["data"][0]["embedding"]
                
        except Exception as e:
            logger.error(f"Error creating embedding: {e}")
            raise