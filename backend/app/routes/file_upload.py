from fastapi import APIRouter, File, UploadFile, HTTPException
from fastapi.responses import JSONResponse
import os
import uuid
from typing import List
import aiofiles
import mimetypes

router = APIRouter()

# 配置上传目录
UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# 允许的文件类型
ALLOWED_EXTENSIONS = {
    'image': {'png', 'jpg', 'jpeg', 'gif', 'webp'},
    'document': {'pdf', 'txt', 'doc', 'docx'},
    'audio': {'mp3', 'wav', 'ogg', 'm4a', 'flac', 'webm'}
}

def get_file_type(filename: str) -> str:
    ext = filename.lower().split('.')[-1]
    for file_type, extensions in ALLOWED_EXTENSIONS.items():
        if ext in extensions:
            return file_type
    return 'other'

def is_allowed_file(filename: str) -> bool:
    """检查文件类型是否允许"""
    if not filename or '.' not in filename:
        return False
    
    ext = filename.rsplit('.', 1)[1].lower()
    all_extensions = set()
    for extensions in ALLOWED_EXTENSIONS.values():
        all_extensions.update(extensions)
    
    return ext in all_extensions

@router.post("/upload")
async def upload_files(files: List[UploadFile] = File(...)):
    if not files:
        raise HTTPException(status_code=400, detail="No files uploaded")
    
    uploaded_files = []
    
    for file in files:
        # 验证文件
        if not file.filename:
            raise HTTPException(status_code=400, detail="File must have a filename")
            
        if not is_allowed_file(file.filename):
            raise HTTPException(
                status_code=400, 
                detail=f"File type not allowed: {file.filename}"
            )
        
        if file.size and file.size > 10 * 1024 * 1024:  # 10MB limit
            raise HTTPException(
                status_code=413, 
                detail=f"File {file.filename} is too large (max 10MB)"
            )
        
        try:
            # 生成唯一文件名
            file_id = str(uuid.uuid4())
            file_ext = file.filename.split('.')[-1] if '.' in file.filename else ''
            safe_filename = f"{file_id}.{file_ext}" if file_ext else file_id
            file_path = os.path.join(UPLOAD_DIR, safe_filename)
            
            # 保存文件
            async with aiofiles.open(file_path, 'wb') as f:
                content = await file.read()
                await f.write(content)
            
            # 获取文件大小
            file_size = len(content) if content else 0
            
            uploaded_files.append({
                'id': file_id,
                'filename': file.filename,
                'type': get_file_type(file.filename),
                'size': file_size,
                'path': file_path
            })
            
        except Exception as e:
            raise HTTPException(
                status_code=500, 
                detail=f"Failed to save file {file.filename}: {str(e)}"
            )
    
    return JSONResponse(content={'files': uploaded_files})

@router.get("/upload/health")
async def upload_health():
    """上传服务健康检查"""
    return {
        "status": "healthy",
        "upload_dir": UPLOAD_DIR,
        "upload_dir_exists": os.path.exists(UPLOAD_DIR),
        "allowed_extensions": ALLOWED_EXTENSIONS
    }