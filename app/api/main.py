"""
Merlin - FastAPI主应用

Author: TJxiaobao
License: MIT
"""
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import shutil
import uuid
import json
from typing import Dict, List, Any
import logging
import os
from pydantic import BaseModel

from ..core.excel_engine import ExcelEngine
from ..core.ai_translator import get_translator
from ..models.schemas import UploadFileResponse
from ..config.settings import config
from ..models.ai_response import (
    AIResponse,
    AIResponseType,
    is_tool_calls_response,
    is_clarification_response,
    is_error_response
)
from ..utils.helpers import validate_file_extension
from ..prompts import manager as prompt_manager
from ..services.session_manager import SessionManager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 创建FastAPI应用
app = FastAPI(
    title="Merlin - AI Excel助手",
    description="通过自然语言指令操作Excel表格",
    version="0.0.6"
)

# 添加CORS支持（方便前端调用）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 挂载前端静态文件
# 支持两种环境：
# 1. 本地开发：app/api/../../frontend/dist (需要回退两级到项目根目录)
# 2. Docker 容器：/app/frontend/dist
frontend_path_dev = os.path.join(os.path.dirname(__file__), "..", "..", "frontend", "dist")
frontend_path_docker = "/app/frontend/dist"

# 优先尝试 Docker 路径，然后是开发路径
if os.path.exists(frontend_path_docker):
    frontend_path = frontend_path_docker
    logger.info(f"✅ 使用 Docker 前端路径: {frontend_path}")
elif os.path.exists(frontend_path_dev):
    frontend_path = frontend_path_dev
    logger.info(f"✅ 使用本地开发前端路径: {frontend_path}")
else:
    frontend_path = None
    logger.warning(f"⚠️ 前端目录不存在:\n   Docker: {frontend_path_docker}\n   Dev: {frontend_path_dev}")

if frontend_path:
    app.mount("/assets", StaticFiles(directory=os.path.join(frontend_path, "assets")), name="assets")
    logger.info(f"✅ 静态文件已挂载: {frontend_path}/assets")

# 全局存储：文件ID -> ExcelEngine实例
engines: Dict[str, ExcelEngine] = {}

# 全局单例：会话管理器
session_manager = SessionManager()


@app.on_event("startup")
async def startup_event():
    """启动时验证配置并加载提示词"""
    try:
        # 验证配置
        config.validate()
        logger.info("✅ 配置验证成功")
        
        # 加载提示词
        prompt_manager.load_prompts()
        logger.info("✅ Merlin 提示词库加载完成")
        
        # 加载工具 Schema
        prompt_manager.load_tools()
        logger.info("✅ Merlin 工具 Schema 加载完成")
    except Exception as e:
        logger.error(f"配置验证失败: {e}")
        raise


@app.get("/")
async def root():
    """返回前端页面"""
    # 支持两种环境：本地开发和 Docker 容器
    # 本地开发需要回退两级：app/api/../../frontend/dist/index.html
    frontend_index_dev = os.path.join(os.path.dirname(__file__), "..", "..", "frontend", "dist", "index.html")
    frontend_index_docker = "/app/frontend/dist/index.html"
    
    # 优先尝试 Docker 路径
    if os.path.exists(frontend_index_docker):
        return FileResponse(frontend_index_docker)
    elif os.path.exists(frontend_index_dev):
        return FileResponse(frontend_index_dev)
    else:
        return {
            "status": "ok",
            "message": "Merlin AI Excel 助手运行中",
            "version": "0.0.6",
            "error": f"前端文件未找到 - Docker: {frontend_index_docker}, Dev: {frontend_index_dev}"
        }

@app.get("/health")
async def health():
    """健康检查"""
    return {
        "message": "Merlin AI Excel助手运行中",
        "status": "ok",
        "version": "0.0.6"
    }


@app.post("/upload", response_model=UploadFileResponse)
async def upload_file(file: UploadFile = File(...)):
    """
    上传Excel文件
    返回文件ID和表头信息
    """
    try:
        # 检查文件类型
        if not validate_file_extension(file.filename, config.ALLOWED_EXTENSIONS):
            raise HTTPException(
                status_code=400, 
                detail=f"只支持Excel文件: {', '.join(config.ALLOWED_EXTENSIONS)}"
            )
        
        # 生成唯一文件ID
        file_id = str(uuid.uuid4())
        file_path = config.UPLOAD_DIR / f"{file_id}.xlsx"
        
        # 保存文件
        with file_path.open("wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        logger.info(f"文件上传成功: {file.filename} -> {file_id}")
        
        # 创建Excel引擎实例
        engine = ExcelEngine(str(file_path))
        engines[file_id] = engine
        
        # 返回表头信息
        headers = engine.get_headers()
        total_rows = len(engine.df)
        
        return UploadFileResponse(
            success=True,
            file_id=file_id,
            headers=headers,
            total_rows=total_rows,
            message=f"文件上传成功！识别到 {len(headers)} 列，共 {total_rows} 行数据。"
        )
        
    except Exception as e:
        logger.error(f"文件上传失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"上传失败: {str(e)}")


@app.get("/download/{file_id}")
async def download_file(file_id: str):
    """
    下载修改后的文件
    """
    result_path = config.UPLOAD_DIR / f"{file_id}_result.xlsx"
    
    if not result_path.exists():
        raise HTTPException(status_code=404, detail="文件不存在")
    
    return FileResponse(
        path=result_path,
        filename=f"modified_{file_id}.xlsx",
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )


@app.get("/preview/{file_id}")
async def preview_file(file_id: str, rows: int = 10):
    """
    预览文件内容
    """
    if file_id not in engines:
        raise HTTPException(status_code=404, detail="文件不存在")
    
    engine = engines[file_id]
    return engine.get_preview(rows=rows)


@app.get("/files/{file_id}/content")
async def get_file_content(file_id: str):
    """
    获取文件完整内容（用于前端编辑）
    """
    if file_id not in engines:
        raise HTTPException(status_code=404, detail="文件不存在")
    
    engine = engines[file_id]
    return engine.get_all_data()


class UpdateContentRequest(BaseModel):
    data: List[List[Any]]


@app.post("/files/{file_id}/content")
async def update_file_content(file_id: str, request: UpdateContentRequest):
    """
    更新文件内容（前端编辑保存）
    """
    if file_id not in engines:
        raise HTTPException(status_code=404, detail="文件不存在")
    
    engine = engines[file_id]
    result = engine.update_data(request.data)
    
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result.get("error", "更新失败"))
    
    # 保存到磁盘（result文件）
    result_path = config.UPLOAD_DIR / f"{file_id}_result.xlsx"
    engine.save(str(result_path))
    logger.info(f"实时编辑已保存到: {result_path}")
    
    return result



@app.delete("/cleanup/{file_id}")
async def cleanup_file(file_id: str):
    """
    清理文件（释放内存和磁盘空间）
    """
    if file_id in engines:
        del engines[file_id]
    
    # 删除磁盘文件
    original_file = config.UPLOAD_DIR / f"{file_id}.xlsx"
    result_file = config.UPLOAD_DIR / f"{file_id}_result.xlsx"
    
    if original_file.exists():
        original_file.unlink()
    if result_file.exists():
        result_file.unlink()
    
    return {"success": True, "message": "文件已清理"}


if __name__ == "__main__":
    import uvicorn
    # ⭐️ 使用 asgi.py 中的包装应用（整合 Socket.IO）
    uvicorn.run("app.asgi:application", host="0.0.0.0", port=8000, reload=True)

