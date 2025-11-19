/**
 * Merlin Frontend - Main JavaScript v2.0
 * 三栏式应用交互逻辑 + WebSocket 流式响应
 * Author: TJxiaobao
 * License: MIT
 */

import './style.css'
import io from 'socket.io-client';  // ⭐️ 导入 Socket.IO
import { startStreamingMessage, updateStreamingMessage, finishStreamingMessage, cancelStreamingMessage } from './streaming.js';

// 自动检测 API 地址（支持本地开发和生产部署）
// ⭐️ 开发环境：前端在 1108，后端在 8000
// ⭐️ 生产环境：前后端在同一域名
const API_BASE_URL = import.meta.env.DEV
    ? 'http://localhost:8000'  // 开发环境：直接连接后端
    : window.location.origin;   // 生产环境：使用当前域名

console.log('API_BASE_URL:', API_BASE_URL);
console.log('环境:', import.meta.env.DEV ? '开发' : '生产');

let currentFileId = null;
let currentHeaders = [];
let originalFileName = '';
let socket = null;  // ⭐️ WebSocket 连接

// DOM 元素
const dropZone = document.getElementById('dropZone');
const fileInput = document.getElementById('fileInput');
const fileInfoCard = document.getElementById('fileInfoCard');
const fileName = document.getElementById('fileName');
const totalRows = document.getElementById('totalRows');
const totalColumns = document.getElementById('totalColumns');
const columnCount = document.getElementById('columnCount');
const columnsList = document.getElementById('columnsList');
const columnsSection = document.getElementById('columnsSection');
const downloadOriginalBtn = document.getElementById('downloadOriginalBtn');
const uploadNewBtn = document.getElementById('uploadNewBtn');

const messagesContainer = document.getElementById('messagesContainer');
const emptyState = document.getElementById('emptyState');
const emptyStateText = document.getElementById('emptyStateText');
const emptyStateSuggestions = document.getElementById('emptyStateSuggestions');
const commandInput = document.getElementById('commandInput');
const sendBtn = document.getElementById('sendBtn');
const sendBtnText = document.getElementById('sendBtnText');
const magicWandBtn = document.getElementById('magicWandBtn');
const featureModal = document.getElementById('featureModal');
const modalClose = document.getElementById('modalClose');

// 编辑器相关 DOM
const editFileBtn = document.getElementById('editFileBtn');
const editorModal = document.getElementById('editorModal');
const editorCancelBtn = document.getElementById('editorCancelBtn');
const editorSaveBtn = document.getElementById('editorSaveBtn');
const spreadsheetEditor = document.getElementById('spreadsheetEditor');
let hot = null; // Handsontable 实例

// ⭐️ 检查关键 DOM 元素是否存在
if (!commandInput || !sendBtn) {
    console.error('❌ 关键 DOM 元素未找到！请检查 HTML 结构');
}
if (!sendBtnText) {
    console.warn('⚠️ sendBtnText 元素未找到，将使用 sendBtn.textContent');
}

// ==================== 文件上传相关 ====================

// 点击上传
dropZone.addEventListener('click', () => {
    if (!dropZone.classList.contains('uploading')) {
        fileInput.click();
    }
});

// 选择文件
fileInput.addEventListener('change', (e) => {
    const file = e.target.files[0];
    if (file) {
        uploadFile(file);
    }
});

// 拖拽上传
dropZone.addEventListener('dragover', (e) => {
    e.preventDefault();
    dropZone.classList.add('dragover');
});

dropZone.addEventListener('dragleave', () => {
    dropZone.classList.remove('dragover');
});

dropZone.addEventListener('drop', (e) => {
    e.preventDefault();
    dropZone.classList.remove('dragover');

    const file = e.dataTransfer.files[0];
    if (file && file.name.endsWith('.xlsx')) {
        uploadFile(file);
    } else {
        addMessage('assistant', '❌ 请上传 .xlsx 格式的Excel文件');
    }
});

// 上传新文件按钮
uploadNewBtn.addEventListener('click', () => {
    fileInput.click();
});

// 下载原始文件按钮
downloadOriginalBtn.addEventListener('click', () => {
    if (!currentFileId) return;

    const downloadUrl = `${API_BASE_URL}/download/${currentFileId}`;
    const link = document.createElement('a');
    link.href = downloadUrl;
    link.download = originalFileName;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
});

// 实时编辑按钮
if (editFileBtn) {
    editFileBtn.addEventListener('click', () => {
        if (!currentFileId) return;
        openEditor();
    });
}

// 编辑器取消按钮
if (editorCancelBtn) {
    editorCancelBtn.addEventListener('click', () => {
        editorModal.style.display = 'none';
    });
}

// 编辑器保存按钮
if (editorSaveBtn) {
    editorSaveBtn.addEventListener('click', () => {
        saveEditor();
    });
}

// 打开编辑器
async function openEditor() {
    if (!currentFileId) return;

    try {
        addMessage('assistant', '⏳ 正在加载编辑器数据...', true);

        const response = await fetch(`${API_BASE_URL}/files/${currentFileId}/content`);
        if (!response.ok) throw new Error('无法获取文件内容');

        const result = await response.json();
        removeLastMessage();

        // 显示模态框
        editorModal.style.display = 'flex';

        // 准备数据：Handsontable 需要数组数组，第一行是表头
        // 后端返回的是 { headers: [], data: [[], []] }
        // 我们需要把 headers 作为第一行拼接到 data 中，或者使用 colHeaders 选项
        // 为了简单起见，我们使用 colHeaders，data 仅包含数据行

        const container = document.getElementById('spreadsheetEditor');
        container.innerHTML = ''; // 清空旧的

        hot = new Handsontable(container, {
            data: result.data,
            colHeaders: result.headers,
            rowHeaders: true,
            height: '100%',
            width: '100%',
            licenseKey: 'non-commercial-and-evaluation',
            contextMenu: true,
            manualColumnResize: true,
            manualRowResize: true,
            filters: true,
            dropdownMenu: true,
        });

    } catch (error) {
        removeLastMessage();
        addMessage('assistant', `❌ 打开编辑器失败: ${error.message}`);
    }
}

// 保存编辑器内容
async function saveEditor() {
    if (!hot || !currentFileId) return;

    try {
        const editorSaveBtn = document.getElementById('editorSaveBtn');
        const originalText = editorSaveBtn.textContent;
        editorSaveBtn.textContent = '保存中...';
        editorSaveBtn.disabled = true;

        // 获取数据
        // getSourceData() 返回原始数据引用，getData() 返回当前视图数据
        // 我们需要包含表头的完整数据传回后端
        const headers = hot.getColHeader();
        const data = hot.getData(); // 获取所有数据

        // 拼接表头和数据
        const fullData = [headers, ...data];

        const response = await fetch(`${API_BASE_URL}/files/${currentFileId}/content`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ data: fullData })
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || '保存失败');
        }

        const result = await response.json();

        // 关闭模态框
        editorModal.style.display = 'none';

        // 提示成功
        addStructuredMessage({
            status: 'success',
            title: '编辑已保存',
            body: `✅ 手动修改已保存，共 ${result.total_rows} 行数据。`
        });

        // 更新左侧栏统计
        document.getElementById('totalRows').textContent = result.total_rows;

    } catch (error) {
        alert(`保存失败: ${error.message}`);
    } finally {
        const editorSaveBtn = document.getElementById('editorSaveBtn');
        editorSaveBtn.textContent = '保存修改';
        editorSaveBtn.disabled = false;
    }
}

// 上传文件函数
async function uploadFile(file) {
    originalFileName = file.name;

    // 隐藏空状态，显示加载消息
    emptyState.style.display = 'none';
    addMessage('user', `📤 上传文件: ${file.name}`);
    addMessage('assistant', '⏳ 正在加载文件...', true);

    const formData = new FormData();
    formData.append('file', file);

    try {
        const response = await fetch(`${API_BASE_URL}/upload`, {
            method: 'POST',
            body: formData
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || '上传失败');
        }

        const result = await response.json();

        // 移除加载消息
        removeLastMessage();

        // 保存文件信息
        currentFileId = result.file_id;
        currentHeaders = result.headers;

        // 显示成功消息（结构化）
        addStructuredMessage({
            status: 'success',
            title: '文件加载成功！',
            body: `📊 总行数: ${result.total_rows}\n📋 总列数: ${result.headers.length}\n\n现在你可以用自然语言告诉我想做什么操作了。`
        });

        // 更新左侧栏 - 文件信息
        fileName.textContent = file.name;
        totalRows.textContent = result.total_rows;
        totalColumns.textContent = result.headers.length;
        fileInfoCard.style.display = 'block';
        dropZone.style.display = 'none';

        // 更新左侧栏 - 列名列表（可复制）
        columnCount.textContent = result.headers.length;
        columnsList.innerHTML = '';
        result.headers.forEach(header => {
            const item = document.createElement('div');
            item.className = 'column-item';

            const name = document.createElement('span');
            name.className = 'column-name';
            name.textContent = header;

            const copyBtn = document.createElement('button');
            copyBtn.className = 'copy-btn';
            copyBtn.textContent = '📋';
            copyBtn.title = '复制列名';
            copyBtn.onclick = (e) => {
                e.stopPropagation();
                copyToClipboard(header, copyBtn);
            };

            // 点击整行也可以复制
            item.onclick = () => {
                copyToClipboard(header, copyBtn);
            };

            item.appendChild(name);
            item.appendChild(copyBtn);
            columnsList.appendChild(item);
        });
        columnsSection.style.display = 'block';

        // 显示空状态的智能建议
        emptyState.style.display = 'flex';
        emptyStateText.textContent = '我已读完你的文件。你可以试试这样说：';
        emptyStateSuggestions.style.display = 'block';

        // 启用输入
        commandInput.disabled = false;
        commandInput.placeholder = '输入指令，例如: 把所有税率设为0.13';
        sendBtn.disabled = false;
        magicWandBtn.disabled = false;
        commandInput.focus();

    } catch (error) {
        removeLastMessage();
        addStructuredMessage({
            status: 'error',
            title: '上传失败',
            body: error.message
        });
    }
}

// 复制到剪贴板
function copyToClipboard(text, button) {
    navigator.clipboard.writeText(text).then(() => {
        // 视觉反馈
        const originalText = button.textContent;
        button.textContent = '✅';
        button.classList.add('copied');

        setTimeout(() => {
            button.textContent = originalText;
            button.classList.remove('copied');
        }, 1500);

        // 或者插入到输入框
        const cursorPos = commandInput.selectionStart;
        const textBefore = commandInput.value.substring(0, cursorPos);
        const textAfter = commandInput.value.substring(cursorPos);
        commandInput.value = textBefore + text + textAfter;
        commandInput.focus();
        commandInput.selectionStart = commandInput.selectionEnd = cursorPos + text.length;
    }).catch(err => {
        console.error('复制失败:', err);
    });
}

// ==================== 消息发送相关 ====================

// 发送按钮
if (sendBtn) {
    sendBtn.addEventListener('click', () => {
        console.log('发送按钮被点击');
        sendCommand();
    });
} else {
    console.error('❌ sendBtn 元素未找到，无法绑定点击事件');
}

// Enter 发送，Shift+Enter 换行
commandInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey && !sendBtn.disabled) {
        e.preventDefault();
        sendCommand();
    }
});

// 自动调整 textarea 高度
commandInput.addEventListener('input', () => {
    commandInput.style.height = 'auto';
    commandInput.style.height = Math.min(commandInput.scrollHeight, 150) + 'px';
});

// 发送指令函数（改为 WebSocket）
async function sendCommand() {
    const command = commandInput.value.trim();

    // ⭐️ 添加错误提示
    if (!command) {
        console.warn('指令为空');
        return;
    }

    if (!currentFileId) {
        console.error('文件未上传');
        addMessage('assistant', '❌ 请先上传 Excel 文件');
        return;
    }

    try {
        // 初始化 WebSocket（如果还没有）
        if (!socket || !socket.connected) {
            console.log('初始化 WebSocket 连接...');
            initWebSocket();
            // 等待连接建立（最多等待5秒）
            await new Promise((resolve, reject) => {
                if (socket.connected) {
                    resolve();
                } else {
                    const timeout = setTimeout(() => {
                        reject(new Error('WebSocket 连接超时'));
                    }, 5000);
                    socket.once('connect', () => {
                        clearTimeout(timeout);
                        resolve();
                    });
                    socket.once('connect_error', (error) => {
                        clearTimeout(timeout);
                        reject(error);
                    });
                }
            });
        }

        // 隐藏空状态
        emptyState.style.display = 'none';

        // 显示用户消息
        addMessage('user', command);
        commandInput.value = '';
        commandInput.style.height = 'auto';

        // 禁用输入
        commandInput.disabled = true;
        sendBtn.disabled = true;
        if (sendBtnText) {
            sendBtnText.innerHTML = '<span class="loading"></span>';
        }

        // ⭐️ 通过 WebSocket 发送执行请求（而非 HTTP POST）
        console.log('发送执行请求:', { file_id: currentFileId, command });
        socket.emit('start_execution', {
            file_id: currentFileId,
            command: command
        });

    } catch (error) {
        console.error('发送指令失败:', error);
        addMessage('assistant', `❌ 发送失败: ${error.message || '未知错误'}`);

        // 恢复输入
        commandInput.disabled = false;
        sendBtn.disabled = false;
        if (sendBtnText) {
            sendBtnText.textContent = '发送';
        }
    }
}

// ==================== 消息显示相关 ====================

// 添加普通消息
function addMessage(role, content, temporary = false) {
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${role}`;
    if (temporary) {
        messageDiv.dataset.temporary = 'true';
    }

    const avatar = document.createElement('div');
    avatar.className = 'message-avatar';
    avatar.textContent = role === 'user' ? '👤' : '🧙';

    const contentDiv = document.createElement('div');
    contentDiv.className = 'message-content';
    contentDiv.innerHTML = content.replace(/\n/g, '<br>');

    messageDiv.appendChild(avatar);
    messageDiv.appendChild(contentDiv);

    messagesContainer.appendChild(messageDiv);
    scrollToBottom();
}

// 添加结构化消息（AI）
function addStructuredMessage({ status, title, body, suggestion = null, showDownload = false }) {
    const messageDiv = document.createElement('div');
    messageDiv.className = 'message assistant';

    const avatar = document.createElement('div');
    avatar.className = 'message-avatar';
    avatar.textContent = '🧙';

    const contentDiv = document.createElement('div');
    contentDiv.className = 'message-content';

    // 状态标题
    const statusDiv = document.createElement('div');
    statusDiv.className = `message-status ${status}`;
    statusDiv.innerHTML = `${status === 'success' ? '✅' : '❌'} <strong>${title}</strong>`;
    contentDiv.appendChild(statusDiv);

    // 消息体
    if (body) {
        const bodyDiv = document.createElement('div');
        bodyDiv.className = 'message-body';
        bodyDiv.innerHTML = body.replace(/\n/g, '<br>');
        contentDiv.appendChild(bodyDiv);
    }

    // 建议提示
    if (suggestion) {
        const suggestionDiv = document.createElement('div');
        suggestionDiv.className = 'message-suggestion';

        const suggestionTitle = document.createElement('div');
        suggestionTitle.className = 'message-suggestion-title';
        suggestionTitle.textContent = suggestion.title || '💡 建议';
        suggestionDiv.appendChild(suggestionTitle);

        if (suggestion.items && suggestion.items.length > 0) {
            const ul = document.createElement('ul');
            suggestion.items.forEach(item => {
                const li = document.createElement('li');
                li.textContent = item;
                ul.appendChild(li);
            });
            suggestionDiv.appendChild(ul);
        }

        contentDiv.appendChild(suggestionDiv);
    }

    // 下载按钮
    if (showDownload) {
        const downloadBtn = document.createElement('button');
        downloadBtn.className = 'message-download-btn';
        downloadBtn.innerHTML = '📥 下载修改后的文件';
        downloadBtn.onclick = () => {
            downloadModifiedFile();
        };
        contentDiv.appendChild(downloadBtn);
    }

    messageDiv.appendChild(avatar);
    messageDiv.appendChild(contentDiv);

    messagesContainer.appendChild(messageDiv);
    scrollToBottom();
}

// 移除最后一条临时消息
function removeLastMessage() {
    const messages = messagesContainer.querySelectorAll('[data-temporary="true"]');
    if (messages.length > 0) {
        messages[messages.length - 1].remove();
    }
}

// 滚动到底部
function scrollToBottom() {
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
}

// 下载修改后的文件
function downloadModifiedFile() {
    if (!currentFileId) return;

    const downloadUrl = `${API_BASE_URL}/download/${currentFileId}`;
    const link = document.createElement('a');
    link.href = downloadUrl;
    link.download = `modified_${originalFileName}`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
}

// 导出到 window（供 streaming.js 调用）
window.downloadModifiedFile = downloadModifiedFile;

// ==================== 魔法棒功能 ====================

magicWandBtn.addEventListener('click', () => {
    featureModal.style.display = 'flex';
});

modalClose.addEventListener('click', () => {
    featureModal.style.display = 'none';
});

featureModal.addEventListener('click', (e) => {
    if (e.target === featureModal) {
        featureModal.style.display = 'none';
    }
});

document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && featureModal.style.display === 'flex') {
        featureModal.style.display = 'none';
    }
});

document.querySelectorAll('.feature-example').forEach(example => {
    example.addEventListener('click', () => {
        const command = example.getAttribute('data-command');
        commandInput.value = command;
        featureModal.style.display = 'none';
        commandInput.focus();
    });
});

// ==================== 工具函数 ====================

// 填充示例指令
window.fillExample = function (text) {
    if (!currentFileId) {
        addMessage('assistant', '请先上传Excel文件');
        return;
    }
    commandInput.value = text;
    commandInput.focus();
    // 自动发送
    sendCommand();
}

// 检查服务器连接
async function checkServerConnection() {
    try {
        const response = await fetch(`${API_BASE_URL}/`);
        if (response.ok) {
            console.log('✅ 服务器连接正常');
            return true;
        }
    } catch (error) {
        console.error('❌ 无法连接到服务器');
        console.error('运行: ./start.sh 或 python -m uvicorn app.main:app --reload');
        return false;
    }
}

// ==================== WebSocket 流式响应 ====================

// 初始化 WebSocket 连接
function initWebSocket() {
    if (socket && socket.connected) {
        console.log('WebSocket 已连接，跳过初始化');
        return;
    }

    console.log('正在初始化 WebSocket 连接...');
    console.log('连接地址:', API_BASE_URL);
    socket = io(API_BASE_URL, {
        transports: ['websocket', 'polling'],
        reconnection: true,
        reconnectionDelay: 1000,
        reconnectionAttempts: 5,
        path: '/socket.io/',  // ⭐️ 明确指定 Socket.IO 路径
        autoConnect: true
    });

    socket.on('connect', () => {
        console.log('✅ WebSocket 连接成功');
    });

    socket.on('disconnect', (reason) => {
        console.log('🔌 WebSocket 断开:', reason);
    });

    socket.on('connect_error', (error) => {
        console.error('❌ WebSocket 连接错误:', error);
        addMessage('assistant', '❌ 无法连接到服务器，请检查后端是否运行');
    });

    socket.on('connection_status', (data) => {
        console.log('连接状态:', data.status);
    });

    socket.on('progress', (data) => {
        handleProgressUpdate(data);
    });

    socket.on('error', (error) => {
        console.error('WebSocket 错误:', error);
        addMessage('assistant', `❌ 发生错误: ${error.message || '未知错误'}`);
    });
}

// 处理进度更新（流式响应的核心 - 在同一个气泡中更新）
function handleProgressUpdate(data) {
    const { type, message, task_index, total_tasks } = data;

    switch (type) {
        case 'start':
            // 开始新的流式消息
            const streamMsg = startStreamingMessage();
            messagesContainer.appendChild(streamMsg);
            updateStreamingMessage(message, { type: 'start' });
            scrollToBottom();
            break;

        case 'translating':
            // AI正在翻译，追加新行
            updateStreamingMessage(message, { type: 'translating', replace: false });
            scrollToBottom();
            break;

        case 'translation_done':
            updateStreamingMessage(message, { type: 'translation_done' });
            scrollToBottom();
            break;

        case 'api_cooldown':
            // 第一次显示等待消息，追加新行
            updateStreamingMessage(message, { type: 'info', replace: false });
            scrollToBottom();
            break;

        case 'api_cooldown_update':
            // 倒计时更新，替换上一行
            updateStreamingMessage(message, { type: 'info', replace: true });
            scrollToBottom();
            break;

        case 'translating_subtask':
            // 显示正在翻译哪个任务，追加新行
            updateStreamingMessage(message, { type: 'translating', replace: false });
            scrollToBottom();
            break;

        case 'subtask_translated':
            updateStreamingMessage(message, { type: 'task_success' });
            scrollToBottom();
            break;

        case 'subtask_translate_failed':
            updateStreamingMessage(message, { type: 'task_error' });
            scrollToBottom();
            break;

        case 'task_start':
            // 显示任务开始（追加新行，不替换）
            updateStreamingMessage(message, {
                type: 'task_start',
                replace: false,
                showProgress: true,
                progress: {
                    current: task_index,
                    total: total_tasks,
                    percent: Math.round((task_index / total_tasks) * 100)
                }
            });
            scrollToBottom();
            break;

        case 'task_success':
            updateStreamingMessage(message, { type: 'task_success' });
            scrollToBottom();
            break;

        case 'task_error':
            updateStreamingMessage(message, { type: 'task_error' });
            if (data.suggestion) {
                updateStreamingMessage(`💡 建议：${data.suggestion}`, { type: 'hint' });
            }
            scrollToBottom();
            break;

        case 'rate_limit':
            // 429 限流提示（在同一个气泡中）
            updateStreamingMessage(message, { type: 'rate_limit' });
            scrollToBottom();
            break;

        case 'rate_limit_countdown':
            // 倒计时更新（替换上一行）
            updateStreamingMessage(message, { type: 'rate_limit', replace: true });
            scrollToBottom();
            break;

        case 'hint':
            updateStreamingMessage(message, { type: 'hint' });
            scrollToBottom();
            break;

        case 'info':
        case 'help':
        case 'analysis_result':
            updateStreamingMessage(message, { type: 'info' });
            scrollToBottom();
            break;

        case 'saving':
            // 显示保存中，追加新行
            updateStreamingMessage(message, { type: 'saving', replace: false });
            scrollToBottom();
            break;

        case 'done':
            // 结束流式消息
            updateStreamingMessage(data.message, { type: 'done' });
            finishStreamingMessage(data.download_url !== null);

            // 恢复输入
            commandInput.disabled = false;
            sendBtn.disabled = false;
            sendBtnText.textContent = '发送';
            scrollToBottom();
            break;

        case 'error':
            cancelStreamingMessage();
            addStructuredMessage({
                status: 'error',
                title: '执行出错',
                body: message
            });

            commandInput.disabled = false;
            sendBtn.disabled = false;
            sendBtnText.textContent = '发送';
            break;

        case 'clarify':
            // ⭐️ 处理澄清请求
            finishStreamingMessage(false);  // 先完成当前流式消息
            showClarificationDialog(data);

            // ⭐️ 恢复输入状态（用户可能想修改指令）
            commandInput.disabled = false;
            sendBtn.disabled = false;
            sendBtnText.textContent = '发送';
            break;
    }
}

// ⭐️ 显示澄清对话框
function showClarificationDialog(data) {
    const { question, options = [], file_id, original_command } = data;

    // 创建澄清消息气泡
    const messageDiv = document.createElement('div');
    messageDiv.className = 'message assistant clarification';

    const avatar = document.createElement('div');
    avatar.className = 'message-avatar';
    avatar.textContent = '🧙';

    const contentDiv = document.createElement('div');
    contentDiv.className = 'message-content';

    // 问题文本
    const questionDiv = document.createElement('div');
    questionDiv.className = 'clarification-question';
    questionDiv.innerHTML = `❓ <strong>${question}</strong>`;
    contentDiv.appendChild(questionDiv);

    // 选项按钮容器
    if (options && options.length > 0) {
        const optionsDiv = document.createElement('div');
        optionsDiv.className = 'clarification-options';

        options.forEach((option, index) => {
            const optionBtn = document.createElement('button');
            optionBtn.className = 'clarification-option-btn';
            optionBtn.textContent = option;
            optionBtn.onclick = () => {
                handleClarificationResponse(option, file_id, original_command);
                messageDiv.classList.add('clarification-answered');
            };
            optionsDiv.appendChild(optionBtn);
        });

        contentDiv.appendChild(optionsDiv);
    }

    // 自定义输入框
    const inputDiv = document.createElement('div');
    inputDiv.className = 'clarification-input';

    const inputField = document.createElement('input');
    inputField.type = 'text';
    inputField.className = 'clarification-text-input';
    inputField.placeholder = '或者输入您的回答...';

    const submitBtn = document.createElement('button');
    submitBtn.className = 'clarification-submit-btn';
    submitBtn.textContent = '提交';
    submitBtn.onclick = () => {
        const answer = inputField.value.trim();
        if (answer) {
            handleClarificationResponse(answer, file_id, original_command);
            messageDiv.classList.add('clarification-answered');
        }
    };

    inputField.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            submitBtn.click();
        }
    });

    inputDiv.appendChild(inputField);
    inputDiv.appendChild(submitBtn);
    contentDiv.appendChild(inputDiv);

    messageDiv.appendChild(avatar);
    messageDiv.appendChild(contentDiv);

    messagesContainer.appendChild(messageDiv);
    scrollToBottom();

    // 聚焦输入框
    setTimeout(() => inputField.focus(), 100);
}

// ⭐️ 处理澄清响应
function handleClarificationResponse(answer, file_id, original_command) {
    console.log('处理澄清响应:', { answer, file_id, original_command });

    // 显示用户的回答
    addMessage('user', answer);

    // ⭐️ 智能替换：尝试将答案代入原始指令
    // 策略1：如果原始指令中包含常见的模糊词（价格、单价等），替换它
    // 策略2：如果策略1没匹配，追加说明
    let newCommand = original_command;

    const ambiguousTerms = ['价格', '单价', '总价', '金额', '费用', '成本', '收入', '支出'];
    let replaced = false;

    for (const term of ambiguousTerms) {
        if (original_command.includes(term)) {
            newCommand = original_command.replace(new RegExp(term, 'g'), answer);
            replaced = true;
            console.log(`替换 "${term}" 为 "${answer}"`);
            break;
        }
    }

    // 如果没有找到可替换的词，使用追加方式（更安全）
    if (!replaced) {
        newCommand = `${original_command}（指的是：${answer}）`;
        console.log('追加澄清说明');
    }

    console.log('重新发送指令:', newCommand);

    // 重新发送指令
    if (!socket || !socket.connected) {
        initWebSocket();
    }

    // 禁用输入
    commandInput.disabled = true;
    sendBtn.disabled = true;
    sendBtnText.innerHTML = '<span class="loading"></span>';

    // 通过 WebSocket 发送执行请求
    socket.emit('start_execution', {
        file_id: file_id,
        command: newCommand
    });
}

// addProgressMessage 已移除，由 streaming.js 中的 updateStreamingMessage 替代

// 页面加载完成后检查服务器和初始化 WebSocket
checkServerConnection();
initWebSocket();
