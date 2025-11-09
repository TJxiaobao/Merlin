"""
Merlin WebSocket 实时推送
流式响应架构

Author: TJxiaobao
License: MIT
"""
import socketio
import asyncio
from typing import Dict
import logging
import json

logger = logging.getLogger(__name__)

# 创建 Socket.IO 服务器（异步模式）
sio = socketio.AsyncServer(
    async_mode='asgi',
    cors_allowed_origins='*',
    logger=False,  # ⭐️ 关闭 Socket.IO 自己的日志，避免干扰
    engineio_logger=False
)

# 存储客户端会话
active_sessions: Dict[str, str] = {}  # {session_id: file_id}


@sio.event
async def connect(sid, environ):
    """客户端连接"""
    logger.info(f"🔗 客户端连接: {sid}")
    await sio.emit('connection_status', {'status': 'connected'}, room=sid)


@sio.event
async def disconnect(sid):
    """客户端断开"""
    logger.info(f"🔌 客户端断开: {sid}")
    if sid in active_sessions:
        del active_sessions[sid]


@sio.event
async def start_execution(sid, data):
    """
    客户端请求开始执行
    data = {"file_id": "xxx", "command": "把A设为1，然后B设为2"}
    """
    file_id = data.get('file_id')
    command = data.get('command')
    
    logger.info(f"📝 收到执行请求: {command}")
    active_sessions[sid] = file_id
    
    # 在后台异步执行（不阻塞）
    asyncio.create_task(execute_with_streaming(sid, file_id, command))


async def execute_with_streaming(sid: str, file_id: str, command: str):
    """
    流式执行任务，实时推送进度
    这是核心函数，替代了原来的同步 execute_command
    """
    from .excel_engine import ExcelEngine
    from .ai_translator import get_translator
    from .config import config
    from app.main import engines, session_manager
    
    try:
        # 步骤 0：开始
        await sio.emit('progress', {
            'type': 'start',
            'message': '🧙 Merlin 开始分析你的指令...'
        }, room=sid)
        await asyncio.sleep(0.3)  # ⭐️ 小延迟，让用户看到流式效果
        
        # 检查文件
        if file_id not in engines:
            await sio.emit('progress', {
                'type': 'error',
                'message': '❌ 文件不存在，请先上传文件'
            }, room=sid)
            return
        
        engine = engines[file_id]
        
        # 步骤 0.5：获取历史上下文
        current_history = session_manager.get_history(file_id)
        
        # 步骤 1：AI 翻译（实时推送）
        await sio.emit('progress', {
            'type': 'translating',
            'message': '🤖 AI 正在翻译指令...'
        }, room=sid)
        await asyncio.sleep(0.2)  # ⭐️ 小延迟
        
        translator = get_translator()
        
        # ⭐️ AI 拆分任务（获取子任务列表）
        try:
            tasks = translator.translate(
                user_command=command,
                headers=engine.get_headers(),
                history=current_history
            )
        except Exception as e:
            error_str = str(e)
            await sio.emit('progress', {
                'type': 'error',
                'message': f'❌ AI 翻译失败: {error_str}'
            }, room=sid)
            return
        
        # 检查是否返回的是列表（子任务）还是翻译结果
        if not tasks:
            await sio.emit('progress', {
                'type': 'error',
                'message': '❌ 任务拆分失败'
            }, room=sid)
            return
        
        # 如果是单任务且已翻译，直接使用
        if isinstance(tasks, list) and len(tasks) > 0 and isinstance(tasks[0], dict):
            # 已经是翻译结果
            translation_results = tasks
        else:
            # 是子任务列表，需要逐个翻译
            total_tasks = len(tasks)
            await sio.emit('progress', {
                'type': 'translation_done',
                'message': f'✅ 指令拆分完成，共 {total_tasks} 个任务',
                'total_tasks': total_tasks
            }, room=sid)
            await asyncio.sleep(0.3)
            
            # ⭐️ 逐个翻译子任务，实时显示进度
            translation_results = []
            for i, task in enumerate(tasks, 1):
                # 如果不是第一个任务，等待21秒避免RPM限制
                if i > 1:
                    wait_time = 21
                    await sio.emit('progress', {
                        'type': 'api_cooldown',
                        'message': f'⏳ 等待 {wait_time} 秒避免 API 限流...',
                        'remaining': wait_time
                    }, room=sid)
                    
                    # 倒计时（每5秒更新）
                    for remaining in range(wait_time, 0, -5):
                        await asyncio.sleep(5)
                        if remaining > 5:
                            await sio.emit('progress', {
                                'type': 'api_cooldown_update',
                                'message': f'⏳ 还剩 {remaining - 5} 秒...',
                                'remaining': remaining - 5
                            }, room=sid)
                
                # 翻译当前子任务
                await sio.emit('progress', {
                    'type': 'translating_subtask',
                    'message': f'🤖 正在翻译任务 {i}/{total_tasks}: {task[:30]}...',
                    'task_index': i,
                    'total_tasks': total_tasks
                }, room=sid)
                
                result = translator.translate_single_task(task, engine.get_headers(), history=current_history)
                translation_results.append(result)
                
                # ⭐️ 立即显示翻译结果
                if result.get("success"):
                    tool_calls = result.get("tool_calls", [])
                    if tool_calls:
                        tool_desc = tool_calls[0].get("tool_name", "未知工具")
                        await sio.emit('progress', {
                            'type': 'subtask_translated',
                            'message': f'✅ 任务 {i} 翻译完成 → 使用工具: {tool_desc}',
                            'task_index': i
                        }, room=sid)
                else:
                    await sio.emit('progress', {
                        'type': 'subtask_translate_failed',
                        'message': f'❌ 任务 {i} 翻译失败: {result.get("error", "未知错误")}',
                        'task_index': i
                    }, room=sid)
                
                await asyncio.sleep(0.2)
        
        total_tasks = len(translation_results)
        
        # 步骤 2：循环执行任务
        execution_log = []
        all_success = True
        last_successful_task_idx = 0
        
        for task_idx, translation_result in enumerate(translation_results, 1):
            # 实时推送：开始执行任务 N
            await sio.emit('progress', {
                'type': 'task_start',
                'message': f'⏳ 正在执行任务 {task_idx}/{total_tasks}...',
                'task_index': task_idx,
                'total_tasks': total_tasks
            }, room=sid)
            await asyncio.sleep(0.2)  # ⭐️ 小延迟
            
            try:
                # 检查翻译是否成功
                if not translation_result.get("success"):
                    error_msg = translation_result.get("error", "未知错误")
                    execution_log.append(f"❌ 任务 {task_idx} 翻译失败: {error_msg}")
                    
                    await sio.emit('progress', {
                        'type': 'task_error',
                        'message': f"❌ 任务 {task_idx} 翻译失败: {error_msg}",
                        'task_index': task_idx
                    }, room=sid)
                    
                    all_success = False
                    
                    # 提示前面的任务已保存
                    if last_successful_task_idx > 0:
                        hint_message = f"💡 提示：前 {last_successful_task_idx} 个任务已成功执行并保存。"
                        execution_log.append(hint_message)
                        await sio.emit('progress', {
                            'type': 'hint',
                            'message': hint_message
                        }, room=sid)
                    
                    break  # 停止执行后续任务
                
                # 检查是否是友好提示消息
                if translation_result.get("is_friendly_message"):
                    message = translation_result.get("message", "")
                    execution_log.append(message)
                    await sio.emit('progress', {
                        'type': 'info',
                        'message': message
                    }, room=sid)
                    continue
                
                # 检查是否是帮助指令
                if translation_result.get("is_help"):
                    message = translation_result.get("message", "")
                    execution_log.append(message)
                    await sio.emit('progress', {
                        'type': 'help',
                        'message': message
                    }, room=sid)
                    continue
                
                # 执行工具调用
                tool_calls = translation_result.get("tool_calls", [])
                if not tool_calls:
                    logger.warning(f"任务 {task_idx} 没有工具调用")
                    continue
                
                for tool_call in tool_calls:
                    tool_name = tool_call["tool_name"]
                    parameters = tool_call["parameters"]
                    
                    logger.info(f"执行工具: {tool_name} with {json.dumps(parameters, ensure_ascii=False)}")
                    
                    # 执行工具（这里复用原有的引擎方法）
                    result = engine.execute_tool(tool_name, parameters)
                    
                    # 检查是否是分析类工具
                    if result.get("is_analysis"):
                        await sio.emit('progress', {
                            'type': 'analysis_result',
                            'message': result["message"]
                        }, room=sid)
                        execution_log.append(result["message"])
                        
                        # 分析类工具完成后立即结束
                        await sio.emit('progress', {
                            'type': 'done',
                            'message': '✅ 分析完成',
                            'success': True,
                            'execution_log': execution_log,
                            'download_url': None
                        }, room=sid)
                        return
                    
                    if result["success"]:
                        execution_log.append(result["message"])
                        last_successful_task_idx = task_idx
                        
                        # 实时推送：任务成功
                        await sio.emit('progress', {
                            'type': 'task_success',
                            'message': f"✅ 任务 {task_idx}: {result['message']}",
                            'task_index': task_idx
                        }, room=sid)
                        await asyncio.sleep(0.3)  # ⭐️ 小延迟，让用户看到每个任务完成
                        
                        # 保存中间结果
                        try:
                            temp_output_path = config.UPLOAD_DIR / f"{file_id}_temp_{task_idx}.xlsx"
                            engine.save(str(temp_output_path))
                            logger.info(f"✅ 任务 {task_idx} 完成，中间结果已保存")
                        except Exception as save_error:
                            logger.warning(f"⚠️ 中间结果保存失败: {save_error}")
                    else:
                        all_success = False
                        error_message = result.get('error', '执行失败')
                        if result.get('suggestion'):
                            error_message += f"\n\n{result['suggestion']}"
                        execution_log.append(error_message)
                        
                        await sio.emit('progress', {
                            'type': 'task_error',
                            'message': f"❌ 任务 {task_idx}: {result.get('error')}",
                            'task_index': task_idx,
                            'suggestion': result.get('suggestion')
                        }, room=sid)
                        
                        # 提示前面的任务已保存
                        if last_successful_task_idx > 0:
                            hint_message = f"💡 提示：前 {last_successful_task_idx} 个任务已成功执行并保存。"
                            execution_log.append(hint_message)
                            await sio.emit('progress', {
                                'type': 'hint',
                                'message': hint_message
                            }, room=sid)
                        
                        break  # 停止执行后续任务
                
            except Exception as e:
                logger.error(f"任务 {task_idx} 异常: {e}")
                all_success = False
                error_message = f"❌ 任务 {task_idx} 执行异常: {str(e)}"
                execution_log.append(error_message)
                
                await sio.emit('progress', {
                    'type': 'task_error',
                    'message': error_message,
                    'task_index': task_idx
                }, room=sid)
                
                # 提示前面的任务已保存
                if last_successful_task_idx > 0:
                    hint_message = f"💡 提示：前 {last_successful_task_idx} 个任务已成功执行并保存。"
                    execution_log.append(hint_message)
                    await sio.emit('progress', {
                        'type': 'hint',
                        'message': hint_message
                    }, room=sid)
                
                break
        
        # 步骤 3：保存文件
        if last_successful_task_idx > 0:
            await sio.emit('progress', {
                'type': 'saving',
                'message': '💾 正在保存文件...'
            }, room=sid)
            await asyncio.sleep(0.3)  # ⭐️ 小延迟
            
            # 保存最终结果
            final_output_path = config.UPLOAD_DIR / f"{file_id}_result.xlsx"
            temp_path = config.UPLOAD_DIR / f"{file_id}_temp_{last_successful_task_idx}.xlsx"
            
            import shutil
            if temp_path.exists():
                shutil.copy(temp_path, final_output_path)
                logger.info(f"✅ 使用任务 {last_successful_task_idx} 的中间结果作为最终文件")
            else:
                engine.save(str(final_output_path))
                logger.info(f"✅ 直接保存当前状态为最终文件")
        
        # 步骤 4：保存历史
        if last_successful_task_idx > 0:
            # 构造成功日志摘要
            success_logs = [log for log in execution_log if "✅" in log or "成功" in log]
            assistant_summary = " ".join(success_logs) if success_logs else "操作成功完成"
            
            # 更新会话历史
            session_manager.update_history(
                file_id=file_id,
                user_msg=command,
                assistant_msg=assistant_summary
            )
        
        # 步骤 5：完成
        success_message = '🎉 所有任务已完成！' if all_success else f'⚠️ 部分任务执行失败'
        if not all_success and last_successful_task_idx > 0:
            success_message += f'（前 {last_successful_task_idx} 个任务已完成）'
        
        await sio.emit('progress', {
            'type': 'done',
            'message': success_message,
            'success': all_success,
            'execution_log': execution_log,
            'download_url': f"/download/{file_id}" if last_successful_task_idx > 0 else None,
            'partial_success': last_successful_task_idx > 0 and not all_success
        }, room=sid)
        
    except Exception as e:
        logger.error(f"执行失败: {e}", exc_info=True)
        await sio.emit('progress', {
            'type': 'error',
            'message': f"❌ 执行失败: {str(e)}"
        }, room=sid)


# 导出 Socket.IO 服务器实例（不是 ASGIApp）
# 供 main.py 使用
__all__ = ['sio']

