import os
import secrets
from fastapi import HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional

security = HTTPBearer()

class APIKeyAuth:
    def __init__(self):
        self.api_secret = os.getenv("API_SECRET_KEY")
        if not self.api_secret:
            # 如果没有设置密钥，生成一个临时的并提示用户
            self.api_secret = secrets.token_urlsafe(32)
            print(f"警告：未设置API_SECRET_KEY，使用临时密钥：{self.api_secret}")
            print("请在.env文件中设置API_SECRET_KEY环境变量")
    
    def verify_api_key(self, credentials: HTTPAuthorizationCredentials = Depends(security)) -> bool:
        """验证API密钥"""
        if not credentials:
            raise HTTPException(
                status_code=401,
                detail="缺少授权头"
            )
        
        if credentials.credentials != self.api_secret:
            raise HTTPException(
                status_code=401,
                detail="无效的API密钥"
            )
        
        return True

# 创建全局实例
api_auth = APIKeyAuth()

def require_api_key():
    """依赖注入函数，用于需要API密钥验证的路由"""
    return Depends(api_auth.verify_api_key)