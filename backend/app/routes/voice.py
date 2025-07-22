from fastapi import APIRouter, File, UploadFile, HTTPException
from fastapi.responses import JSONResponse
import openai
import os
import tempfile
import aiofiles

router = APIRouter()

# 配置 OpenAI
openai.api_key = os.getenv("OPENAI_API_KEY")

@router.post("/transcribe")
async def transcribe_audio(audio: UploadFile = File(...)):
    if not audio.content_type.startswith('audio/'):
        raise HTTPException(status_code=400, detail="File must be an audio file")
    
    if audio.size > 25 * 1024 * 1024:  # 25MB limit for Whisper API
        raise HTTPException(status_code=413, detail="Audio file is too large")
    
    try:
        # 创建临时文件
        with tempfile.NamedTemporaryFile(delete=False, suffix='.wav') as tmp_file:
            content = await audio.read()
            tmp_file.write(content)
            tmp_file.flush()
            
            # 使用 OpenAI Whisper API 进行转录
            with open(tmp_file.name, 'rb') as audio_file:
                transcript = openai.Audio.transcribe(
                    model="whisper-1",  # 或者使用 "gpt-4o-audio-preview" 如果可用
                    file=audio_file,
                    language="zh"  # 指定中文，可根据需要调整
                )
        
        # 删除临时文件
        os.unlink(tmp_file.name)
        
        return JSONResponse(content={
            'text': transcript['text'],
            'success': True
        })
        
    except Exception as e:
        # 确保临时文件被删除
        if 'tmp_file' in locals():
            try:
                os.unlink(tmp_file.name)
            except:
                pass
        
        raise HTTPException(status_code=500, detail=f"Transcription failed: {str(e)}")