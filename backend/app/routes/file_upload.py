from fastapi import APIRouter, File, UploadFile, HTTPException
from fastapi.responses import JSONResponse
import os
import uuid
from typing import List
import aiofiles

router = APIRouter()

# 配置上传目录
UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# 允许的文件类型
ALLOWED_EXTENSIONS = {
    'image': {'png', 'jpg', 'jpeg', 'gif', 'webp'},
    'document': {'pdf', 'txt', 'doc', 'docx'},
    'audio': {'mp3', 'wav', 'ogg', 'm4a', 'flac'}
}

def get_file_type(filename: str) -> str:
    ext = filename.lower().split('.')[-1]
    for file_type, extensions in ALLOWED_EXTENSIONS.items():
        if ext in extensions:
            return file_type
    return 'other'

@router.post("/upload")
async def upload_files(files: List[UploadFile] = File(...)):
    uploaded_files = []
    
    for file in files:
        if file.size > 10 * 1024 * 1024:  # 10MB limit
            raise HTTPException(status_code=413, detail=f"File {file.filename} is too large")
        
        # 生成唯一文件名
        file_id = str(uuid.uuid4())
        file_ext = file.filename.split('.')[-1] if '.' in file.filename else ''
        safe_filename = f"{file_id}.{file_ext}" if file_ext else file_id
        file_path = os.path.join(UPLOAD_DIR, safe_filename)
        
        # 保存文件
        async with aiofiles.open(file_path, 'wb') as f:
            content = await file.read()
            await f.write(content)
        
        uploaded_files.append({
            'id': file_id,
            'filename': file.filename,
            'type': get_file_type(file.filename),
            'size': file.size,
            'path': file_path
        })
    
    return JSONResponse(content={'files': uploaded_files})