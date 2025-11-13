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
    from ..core.excel_engine import ExcelEngine
    from ..core.ai_translator import get_translator
    from ..config.settings import config
    from ..models.ai_response import (
        AIResponse,
        AIResponseType,
        is_tool_calls_response,
        is_clarification_response,
        is_error_response
    )
    from app.api.main import engines, session_manager
    
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
        
        # 注意：translate() 现在返回 List[AIResponse]，不是字符串列表
        # 检查返回的是否已经是 AIResponse 对象
        from ..models.ai_response import AIResponse, is_task_list_response
        
        # translate() 现在总是返回 List[AIResponse]
        if not isinstance(tasks, list) or len(tasks) == 0 or not isinstance(tasks[0], AIResponse):
            logger.error(f"⚠️  translate() 返回了意外的类型: {type(tasks[0]) if tasks else 'empty'}")
            await sio.emit('progress', {
                'type': 'error',
                'message': '❌ AI 翻译返回格式错误'
            }, room=sid)
            return
        
        # 如果是任务列表，需要逐个翻译
        if len(tasks) == 1 and is_task_list_response(tasks[0]):
            logger.info(f"📋 检测到任务列表，需要逐个翻译")
            task_list = tasks[0].task_list
            
            await sio.emit('progress', {
                'type': 'task_split',
                'message': f'📋 任务已拆分为 {len(task_list)} 个子任务',
                'total_tasks': len(task_list)
            }, room=sid)
            
            # ⭐️ 保存初始历史（上一个会话的历史）
            initial_history = session_manager.get_history(file_id)
            logger.info(f"📚 初始历史记录（上一个会话）: {len(initial_history)} 条消息")
            
            # 逐个翻译和执行子任务（边翻译边执行，以便携带历史）
            execution_log = []
            last_successful_task_idx = 0
            all_success = True
            
            for i, subtask in enumerate(task_list, 1):
                # ⭐️ 构建历史：初始历史 + 上一个子任务的结果
                # 如果 i > 1，获取最新历史（包含上一个子任务的结果）
                if i > 1:
                    # 获取最新历史（包含上一个子任务的结果）
                    current_history = session_manager.get_history(file_id)
                    logger.info(f"📚 任务 {i} 翻译时携带历史: {len(current_history)} 条消息（初始历史 + 前 {i-1} 个子任务）")
                else:
                    # 第一个任务只携带初始历史（上一个会话的历史）
                    current_history = initial_history
                    logger.info(f"📚 任务 1 翻译时携带初始历史: {len(current_history)} 条消息（上一个会话）")
                
                await sio.emit('progress', {
                    'type': 'translating_subtask',
                    'message': f'🤖 正在翻译任务 {i}/{len(task_list)}: {subtask[:30]}...',
                    'task_index': i,
                    'total_tasks': len(task_list)
                }, room=sid)
                
                # ⭐️ 翻译子任务（携带历史：初始历史 + 上一个子任务的结果）
                result = translator.translate(
                    user_command=subtask,
                    headers=engine.get_headers(),
                    history=current_history  # ✅ 携带历史
                )
                
                if not result or len(result) == 0:
                    logger.warning(f"任务 {i} 翻译返回空结果")
                    all_success = False
                    continue
                
                translation_result = result[0]
                
                if not translation_result.success:
                    await sio.emit('progress', {
                        'type': 'subtask_translate_failed',
                        'message': f'❌ 任务 {i} 翻译失败: {translation_result.error or "未知错误"}',
                        'task_index': i
                    }, room=sid)
                    all_success = False
                    break
                
                await sio.emit('progress', {
                    'type': 'subtask_translated',
                    'message': f'✅ 任务 {i} 翻译完成',
                    'task_index': i
                }, room=sid)
                
                # ⭐️ 立即执行当前任务
                await sio.emit('progress', {
                    'type': 'task_start',
                    'message': f'⏳ 正在执行任务 {i}/{len(task_list)}...',
                    'task_index': i,
                    'total_tasks': len(task_list)
                }, room=sid)
                
                # 执行工具调用
                if is_tool_calls_response(translation_result) and translation_result.tool_calls:
                    for tool_call in translation_result.tool_calls:
                        tool_name = tool_call.tool_name
                        parameters = tool_call.parameters
                        
                        logger.info(f"执行工具: {tool_name} with {json.dumps(parameters, ensure_ascii=False)}")
                        
                        result = engine.execute_tool(tool_name, parameters)
                        
                        if result.get("success"):
                            log_msg = result.get("message", f"✅ 任务 {i} 执行成功")
                            execution_log.append(log_msg)
                            last_successful_task_idx = i
                            
                            await sio.emit('progress', {
                                'type': 'task_success',
                                'message': log_msg,
                                'task_index': i
                            }, room=sid)
                            
                            # ⭐️ 立即保存历史记录（让下一个任务可以携带）
                            assistant_summary = log_msg  # 只保存当前任务的执行结果
                            
                            logger.info(f"💾 保存历史记录（任务 {i}）: user='{subtask[:30]}...', assistant='{assistant_summary[:50]}...'")
                            session_manager.update_history(
                                file_id=file_id,
                                user_msg=subtask,
                                assistant_msg=assistant_summary
                            )
                        else:
                            error_msg = result.get("error", "未知错误")
                            execution_log.append(f"❌ 任务 {i} 执行失败: {error_msg}")
                            all_success = False
                            await sio.emit('progress', {
                                'type': 'task_error',
                                'message': f"❌ 任务 {i} 执行失败: {error_msg}",
                                'task_index': i
                            }, room=sid)
                            break
                else:
                    logger.warning(f"任务 {i} 没有工具调用")
                    all_success = False
                    break
                            
            logger.info(f"✅ {len(task_list)} 个子任务全部翻译和执行完成")
            
            # ⭐️ 保存文件（修复：最后一个任务处理问题）
            if last_successful_task_idx > 0:
                await sio.emit('progress', {
                    'type': 'saving',
                    'message': '💾 正在保存文件...'
                }, room=sid)
                await asyncio.sleep(0.3)
                
                try:
                    final_output_path = config.UPLOAD_DIR / f"{file_id}_result.xlsx"
                    engine.save(str(final_output_path))
                    logger.info(f"✅ 文件已保存: {final_output_path}")
                except Exception as save_error:
                    logger.error(f"❌ 文件保存失败: {save_error}")
                    execution_log.append(f"❌ 文件保存失败: {save_error}")
            
            # ⭐️ 所有子任务已完成，返回结果
            await sio.emit('progress', {
                'type': 'done',
                'message': '✅ 所有任务执行完成',
                'success': all_success,
                'execution_log': execution_log,
                'download_url': f'/download/{file_id}' if last_successful_task_idx > 0 else None
            }, room=sid)
            return
        else:
            # 已经是翻译结果（List[AIResponse]）
            translation_results = tasks
            logger.info(f"✅ 收到 {len(translation_results)} 个翻译结果")
        
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
                if not translation_result.success:
                    error_msg = translation_result.error or "未知错误"
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
                if translation_result.response_type == AIResponseType.FRIENDLY_MESSAGE:
                    message = translation_result.message or ""
                    execution_log.append(message)
                    await sio.emit('progress', {
                        'type': 'info',
                        'message': message
                    }, room=sid)
                    continue
                
                # 检查是否是帮助指令
                if translation_result.response_type == AIResponseType.HELP:
                    message = translation_result.message or ""
                    execution_log.append(message)
                    await sio.emit('progress', {
                        'type': 'help',
                        'message': message
                    }, room=sid)
                    continue
                
                # ⭐️ 检查是否是澄清请求
                if is_clarification_response(translation_result):
                    clarification = translation_result.clarification
                    logger.info(f"🔍 收到澄清请求: {clarification.question}")
                    logger.info(f"   选项: {clarification.options}")
                    
                    await sio.emit('progress', {
                        'type': 'clarify',
                        'question': clarification.question,
                        'options': clarification.options,
                        'file_id': file_id,
                        'original_command': command
                    }, room=sid)
                    
                    # 澄清请求不继续执行，等待用户回复
                    return
                
                # 执行工具调用
                if not is_tool_calls_response(translation_result) or not translation_result.tool_calls:
                    logger.warning(f"任务 {task_idx} 没有工具调用")
                    continue
                
                for tool_call in translation_result.tool_calls:
                    tool_name = tool_call.tool_name
                    parameters = tool_call.parameters
                    
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
                        
                        # ⭐️ 标记为成功（即使是分析类工具也要记录）
                        last_successful_task_idx = task_idx
                        
                        # ⭐️ 保存历史记录（分析类工具也需要保存历史）
                        success_logs = [log for log in execution_log if "✅" in log or "成功" in log or "📊" in log]
                        assistant_summary = " ".join(success_logs) if success_logs else result["message"]
                        
                        logger.info(f"💾 保存历史记录（分析类工具）: user='{command[:30]}...', assistant='{assistant_summary[:50]}...'")
                        session_manager.update_history(
                            file_id=file_id,
                            user_msg=command,
                            assistant_msg=assistant_summary
                        )
                        
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
        logger.info(f"🔍 检查是否保存历史: last_successful_task_idx={last_successful_task_idx}, all_success={all_success}")
        if last_successful_task_idx > 0:
            # 构造成功日志摘要
            success_logs = [log for log in execution_log if "✅" in log or "成功" in log]
            assistant_summary = " ".join(success_logs) if success_logs else "操作成功完成"
            
            logger.info(f"💾 保存历史记录: user='{command[:30]}...', assistant='{assistant_summary[:50]}...'")
            
            # 更新会话历史
            session_manager.update_history(
                file_id=file_id,
                user_msg=command,
                assistant_msg=assistant_summary
            )
        else:
            logger.warning(f"⚠️ 未保存历史：没有成功执行的任务 (last_successful_task_idx={last_successful_task_idx})")
        
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

