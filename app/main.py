"""
Merlin - FastAPI主应用

Author: TJxiaobao
License: MIT
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
from .prompts import manager as prompt_manager

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
    
    新架构：支持多指令串行执行
    - AI translate() 现在返回列表：[result1, result2, ...]
    - 循环执行每个结果，每次都基于最新的 DataFrame
    """
    try:
        # 检查文件是否存在
        if request.file_id not in engines:
            raise HTTPException(status_code=404, detail="文件不存在，请先上传文件")
        
        engine = engines[request.file_id]
        
        logger.info(f"收到指令: {request.command}")
        
        # 步骤1: 使用AI翻译指令（现在返回列表）
        translator = get_translator()
        translation_results = translator.translate(
            user_command=request.command,
            headers=engine.get_headers()
        )
        
        logger.info(f"收到 {len(translation_results)} 个翻译结果")
        
        # 步骤2: 循环执行每个翻译结果
        execution_log = []
        all_success = True
        last_successful_task_idx = 0  # ⭐️ 方案A：记录最后成功的任务索引
        
        for task_idx, translation_result in enumerate(translation_results, 1):
            logger.info(f"执行第 {task_idx}/{len(translation_results)} 个任务")
            
            # 检查翻译是否成功
            if not translation_result.get("success"):
                all_success = False
                error_msg = translation_result.get("error", "未知错误")
                execution_log.append(f"❌ 任务 {task_idx} 翻译失败: {error_msg}")
                
                # ⭐️ 方案A：提示前面的任务已保存
                if last_successful_task_idx > 0:
                    execution_log.append(
                        f"💡 提示：前 {last_successful_task_idx} 个任务已成功执行并保存。"
                    )
                break  # 遇到错误，停止执行后续任务
            
            # 检查是否是友好提示消息
            if translation_result.get("is_friendly_message"):
                execution_log.append(translation_result.get("message", ""))
                continue
            
            # 检查是否是帮助指令
            if translation_result.get("is_help"):
                execution_log.append(translation_result.get("message", ""))
                continue
            
            # 执行工具调用
            tool_calls = translation_result.get("tool_calls", [])
            if not tool_calls:
                logger.warning(f"任务 {task_idx} 没有工具调用")
                continue
            
            for tool_call in tool_calls:
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
                elif tool_name == "concatenate_columns":  # v0.0.4-alpha
                    result = engine.concatenate_columns(**parameters)
                elif tool_name == "extract_date_part":  # v0.0.4-alpha
                    result = engine.extract_date_part(**parameters)
                elif tool_name == "group_by_aggregate":  # v0.0.4-alpha
                    result = engine.group_by_aggregate(**parameters)
                elif tool_name == "split_column":  # v0.0.4-beta
                    result = engine.split_column(**parameters)
                elif tool_name == "change_case":  # v0.0.4-beta
                    result = engine.change_case(**parameters)
                elif tool_name == "drop_duplicates":  # v0.0.4-beta
                    result = engine.drop_duplicates(**parameters)
                elif tool_name == "sort_by_column":  # v0.0.4-beta
                    # 转换 ascending 参数为布尔值（如果存在）
                    if 'ascending' in parameters and isinstance(parameters['ascending'], str):
                        parameters['ascending'] = parameters['ascending'].lower() in ['true', '1', 'yes']
                    result = engine.sort_by_column(**parameters)
                else:
                    result = {
                        "success": False,
                        "error": f"未知工具: {tool_name}"
                    }
                
                # 检查是否是分析类工具（不修改表格）
                if result.get("is_analysis"):
                    # 分析类工具直接返回结果，不保存文件
                    return ExecuteCommandResponse(
                        success=True,
                        message=result["message"],
                        execution_log=[result["message"]]
                    )
                
                if not result["success"]:
                    all_success = False
                    # ⭐️ v0.1.0: 如果有建议，一起显示
                    error_message = result.get('error', '执行失败')
                    if result.get('suggestion'):
                        error_message += f"\n\n{result['suggestion']}"
                    execution_log.append(error_message)
                    
                    # ⭐️ 方案A：遇到执行错误，提示前面的任务已保存
                    if last_successful_task_idx > 0:
                        execution_log.append(
                            f"💡 提示：前 {last_successful_task_idx} 个任务已成功执行并保存。"
                        )
                    break  # 遇到错误，停止执行后续任务
                else:
                    execution_log.append(result["message"])
                    last_successful_task_idx = task_idx
                    
                    # ⭐️ 方案A：每完成一个任务，立即保存中间结果
                    try:
                        temp_output_path = config.UPLOAD_DIR / f"{request.file_id}_temp_{task_idx}.xlsx"
                        engine.save(str(temp_output_path))
                        logger.info(f"✅ 任务 {task_idx} 完成，中间结果已保存到 {temp_output_path}")
                    except Exception as save_error:
                        logger.warning(f"⚠️ 任务 {task_idx} 的中间结果保存失败: {save_error}")
        
        # ⭐️ 方案A：保存最终结果（或最后一个成功的中间结果）
        final_output_path = config.UPLOAD_DIR / f"{request.file_id}_result.xlsx"
        
        if last_successful_task_idx > 0:
            # 如果有任务成功，保存结果
            temp_path = config.UPLOAD_DIR / f"{request.file_id}_temp_{last_successful_task_idx}.xlsx"
            
            if temp_path.exists():
                # 使用最后一个成功任务的中间结果
                shutil.copy(temp_path, final_output_path)
                logger.info(f"✅ 使用任务 {last_successful_task_idx} 的中间结果作为最终文件")
            else:
                # 备用：直接保存当前引擎状态
                engine.save(str(final_output_path))
                logger.info(f"✅ 直接保存当前状态为最终文件")
        
        if not all_success:
            # 部分失败，但有成功的任务
            if last_successful_task_idx > 0:
                return ExecuteCommandResponse(
                    success=False,
                    message=f"部分操作执行失败（前 {last_successful_task_idx} 个任务已完成）",
                    execution_log=execution_log,
                    download_url=f"/download/{request.file_id}",  # ⭐️ 仍然提供下载链接
                    error="请查看日志了解详情"
                )
            else:
                # 全部失败
                return ExecuteCommandResponse(
                    success=False,
                    message="所有操作均执行失败",
                    execution_log=execution_log,
                    error="请查看日志了解详情"
                )
        
        # 全部成功
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
    # ⭐️ 使用 asgi.py 中的包装应用（整合 Socket.IO）
    uvicorn.run("app.asgi:application", host="0.0.0.0", port=8000, reload=True)

