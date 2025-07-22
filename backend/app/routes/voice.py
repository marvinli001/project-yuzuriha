from fastapi import APIRouter, File, UploadFile, HTTPException
from fastapi.responses import JSONResponse
import openai
import os
import tempfile
import aiofiles
from openai import AsyncOpenAI

router = APIRouter()

# 初始化 OpenAI 客户端
client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

@router.post("/transcribe")
async def transcribe_audio(audio: UploadFile = File(...)):
    if not audio.content_type or not audio.content_type.startswith('audio/'):
        raise HTTPException(status_code=400, detail="File must be an audio file")
    
    if audio.size and audio.size > 25 * 1024 * 1024:  # 25MB limit for Whisper API
        raise HTTPException(status_code=413, detail="Audio file is too large")
    
    tmp_file_path = None
    try:
        # 创建临时文件
        with tempfile.NamedTemporaryFile(delete=False, suffix='.wav') as tmp_file:
            tmp_file_path = tmp_file.name
            content = await audio.read()
            tmp_file.write(content)
            tmp_file.flush()
            
        # 使用 OpenAI Whisper API 进行转录
        with open(tmp_file_path, 'rb') as audio_file:
            transcript = await client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file,
                language="zh"  # 指定中文，可根据需要调整
            )
        
        return JSONResponse(content={
            'text': transcript.text,
            'success': True
        })
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Transcription failed: {str(e)}")
        
    finally:
        # 确保临时文件被删除
        if tmp_file_path and os.path.exists(tmp_file_path):
            try:
                os.unlink(tmp_file_path)
            except:
                pass

@router.get("/transcribe/health")
async def transcribe_health():
    """转录服务健康检查"""
    return {
        "status": "healthy",
        "openai_key_configured": bool(os.getenv("OPENAI_API_KEY")),
        "supported_formats": ["wav", "mp3", "ogg", "m4a", "flac", "webm"]
    }