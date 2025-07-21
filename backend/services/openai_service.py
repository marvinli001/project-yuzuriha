import openai
import os
import logging
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

class OpenAIService:
    def __init__(self):
        self.client = openai.AsyncOpenAI(
            api_key=os.getenv("OPENAI_API_KEY")
        )
        
    async def health_check(self) -> bool:
        """Check if OpenAI service is available"""
        try:
            await self.client.models.list()
            return True
        except Exception as e:
            logger.error(f"OpenAI health check failed: {e}")
            return False
    
    async def generate_response(self, message: str, context: str = "") -> str:
        """Generate response using GPT-4"""
        try:
            system_prompt = """You are Yuzuriha, an AI assistant with memory capabilities. 
            You are helpful, knowledgeable, and can remember past conversations.
            
            Guidelines:
            - Be conversational and friendly
            - Use the provided context and memories to give relevant responses
            - If you remember something from a past conversation, mention it naturally
            - Be concise but thorough
            - Always aim to be helpful and accurate
            """
            
            messages = [
                {"role": "system", "content": system_prompt}
            ]
            
            if context:
                messages.append({"role": "system", "content": f"Context: {context}"})
            
            messages.append({"role": "user", "content": message})
            
            response = await self.client.chat.completions.create(
                model="gpt-4o",
                messages=messages,
                temperature=0.7,
                max_tokens=2000
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            logger.error(f"OpenAI API error: {e}")
            raise Exception(f"Failed to generate response: {str(e)}")
    
    async def generate_embeddings(self, text: str) -> list:
        """Generate embeddings for text using OpenAI"""
        try:
            response = await self.client.embeddings.create(
                model="text-embedding-3-small",
                input=text
            )
            return response.data[0].embedding
        except Exception as e:
            logger.error(f"Embedding generation error: {e}")
            raise Exception(f"Failed to generate embeddings: {str(e)}")