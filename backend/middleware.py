from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
import logging

logger = logging.getLogger(__name__)

async def error_handling_middleware(request: Request, call_next):
    """全局错误处理中间件"""
    try:
        response = await call_next(request)
        return response
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"未处理的错误: {e}")
        return JSONResponse(
            status_code=500,
            content={"detail": "内部服务器错误", "error": str(e)}
        )