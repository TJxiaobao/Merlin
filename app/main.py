"""
Merlin - FastAPI主应用
"""
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
import shutil
import uuid
import json
from typing import Dict
import logging

from .excel_engine import ExcelEngine
from .ai_translator import get_translator
from .schemas import ExecuteCommandRequest, ExecuteCommandResponse, UploadFileResponse
from .config import config
from .utils import validate_file_extension

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 创建FastAPI应用
app = FastAPI(
    title="Merlin - AI Excel助手",
    description="通过自然语言指令操作Excel表格",
    version="0.1.0"
)

# 添加CORS支持（方便前端调用）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 全局存储：文件ID -> ExcelEngine实例
engines: Dict[str, ExcelEngine] = {}


@app.on_event("startup")
async def startup_event():
    """启动时验证配置"""
    try:
        config.validate()
        logger.info("配置验证成功")
    except Exception as e:
        logger.error(f"配置验证失败: {e}")
        raise


@app.get("/")
async def root():
    """健康检查"""
    return {
        "message": "Merlin AI Excel助手运行中",
        "status": "ok",
        "version": "0.1.0"
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


@app.post("/execute", response_model=ExecuteCommandResponse)
async def execute_command(request: ExecuteCommandRequest):
    """
    执行用户指令
    """
    try:
        # 检查文件是否存在
        if request.file_id not in engines:
            raise HTTPException(status_code=404, detail="文件不存在，请先上传文件")
        
        engine = engines[request.file_id]
        
        logger.info(f"收到指令: {request.command}")
        
        # 步骤1: 使用AI翻译指令
        translator = get_translator()
        translation_result = translator.translate(
            user_command=request.command,
            headers=engine.get_headers()
        )
        
        if not translation_result["success"]:
            return ExecuteCommandResponse(
                success=False,
                message="AI无法理解您的指令",
                error=translation_result.get("error", "未知错误"),
                execution_log=[translation_result.get("ai_message", "")]
            )
        
        # 步骤2: 执行工具调用
        execution_log = []
        all_success = True
        
        for tool_call in translation_result["tool_calls"]:
            tool_name = tool_call["tool_name"]
            parameters = tool_call["parameters"]
            
            # 使用 json.dumps 避免字典中的花括号导致格式化错误
            logger.info(f"执行工具: {tool_name} with {json.dumps(parameters, ensure_ascii=False)}")
            
            # 调用对应的引擎方法
            if tool_name == "set_column_value":
                result = engine.set_column_value(**parameters)
            elif tool_name == "set_by_condition":
                result = engine.set_by_condition(**parameters)
            elif tool_name == "copy_column":
                result = engine.copy_column(**parameters)
            elif tool_name == "set_by_mapping":
                result = engine.set_by_mapping(**parameters)
            elif tool_name == "get_summary":
                # 转换 top_n 参数为整数
                if 'top_n' in parameters and isinstance(parameters['top_n'], str):
                    parameters['top_n'] = int(parameters['top_n'])
                result = engine.get_summary(**parameters)
            elif tool_name == "perform_math":
                # 转换 round_to 参数为整数（如果存在）
                if 'round_to' in parameters and parameters['round_to']:
                    parameters['round_to'] = int(parameters['round_to'])
                result = engine.perform_math(**parameters)
            elif tool_name == "trim_whitespace":
                result = engine.trim_whitespace(**parameters)
            elif tool_name == "fill_missing_values":
                result = engine.fill_missing_values(**parameters)
            elif tool_name == "find_and_replace":
                result = engine.find_and_replace(**parameters)
            else:
                result = {
                    "success": False,
                    "error": f"未知工具: {tool_name}"
                }
            
            if not result["success"]:
                all_success = False
                execution_log.append(f"❌ {result.get('error', '执行失败')}")
            else:
                execution_log.append(result["message"])
        
        if not all_success:
            return ExecuteCommandResponse(
                success=False,
                message="部分操作执行失败",
                execution_log=execution_log,
                error="请查看日志了解详情"
            )
        
        # 步骤3: 保存修改后的文件
        output_path = config.UPLOAD_DIR / f"{request.file_id}_result.xlsx"
        engine.save(str(output_path))
        
        return ExecuteCommandResponse(
            success=True,
            message="指令执行成功！",
            execution_log=execution_log,
            download_url=f"/download/{request.file_id}"
        )
        
    except Exception as e:
        logger.error(f"执行失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"执行失败: {str(e)}")


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
    uvicorn.run(app, host="0.0.0.0", port=8000)

