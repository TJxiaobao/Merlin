/**
 * Merlin Frontend - Main JavaScript
 * Author: TJxiaobao
 * License: MIT
 */

import './style.css'

const API_BASE_URL = 'http://localhost:8000';

let currentFileId = null;
let currentHeaders = [];

// DOM 元素
const dropZone = document.getElementById('dropZone');
const fileInput = document.getElementById('fileInput');
const fileInfo = document.getElementById('fileInfo');
const fileName = document.getElementById('fileName');
const totalRows = document.getElementById('totalRows');
const totalColumns = document.getElementById('totalColumns');
const columnsList = document.getElementById('columnsList');
const closeFileBtn = document.getElementById('closeFile');
const messagesContainer = document.getElementById('messagesContainer');
const welcomeMessage = document.getElementById('welcomeMessage');
const commandInput = document.getElementById('commandInput');
const sendBtn = document.getElementById('sendBtn');
const sendBtnText = document.getElementById('sendBtnText');
const downloadBtn = document.getElementById('downloadBtn');
const actionButtons = document.getElementById('actionButtons');
const magicWandBtn = document.getElementById('magicWandBtn');
const featureModal = document.getElementById('featureModal');
const modalClose = document.getElementById('modalClose');

// 文件上传 - 点击
dropZone.addEventListener('click', () => {
    if (!dropZone.classList.contains('uploading')) {
        fileInput.click();
    }
});

// 文件上传 - 选择文件
fileInput.addEventListener('change', (e) => {
    const file = e.target.files[0];
    if (file) {
        uploadFile(file);
    }
});

// 文件上传 - 拖拽
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
        addMessage('assistant', '请上传 .xlsx 格式的Excel文件');
    }
});

// 关闭文件
closeFileBtn.addEventListener('click', () => {
    currentFileId = null;
    currentHeaders = [];
    fileInfo.classList.remove('active');
    commandInput.disabled = true;
    commandInput.placeholder = '请先上传Excel文件...';
    sendBtn.disabled = true;
    magicWandBtn.disabled = true;
    downloadBtn.style.display = 'none';
    messagesContainer.innerHTML = '';
    messagesContainer.appendChild(welcomeMessage);
    welcomeMessage.style.display = 'block';
});

// 发送指令
sendBtn.addEventListener('click', () => {
    sendCommand();
});

// 支持 Enter 发送，Shift+Enter 换行
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

// 下载文件
downloadBtn.addEventListener('click', () => {
    downloadFile();
});

// 上传文件函数
async function uploadFile(file) {
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
        
        // 显示成功消息
        currentFileId = result.file_id;
        currentHeaders = result.headers;
        
        addMessage('assistant', `✅ 文件加载成功！\n\n📊 总行数: ${result.total_rows}\n📋 总列数: ${result.headers.length}\n\n现在你可以用自然语言告诉我想做什么操作了。`);

        // 更新文件信息区域
        fileName.textContent = file.name;
        totalRows.textContent = result.total_rows;
        totalColumns.textContent = result.headers.length;
        
        columnsList.innerHTML = '';
        result.headers.forEach(header => {
            const tag = document.createElement('span');
            tag.className = 'column-tag';
            tag.textContent = header;
            columnsList.appendChild(tag);
        });
        
        fileInfo.classList.add('active');
        welcomeMessage.style.display = 'none';
        
        // 启用输入
        commandInput.disabled = false;
        commandInput.placeholder = '输入指令，例如: 把所有税率设为0.13';
        sendBtn.disabled = false;
        magicWandBtn.disabled = false;  // 启用魔法棒按钮
        commandInput.focus();

    } catch (error) {
        removeLastMessage();
        addMessage('assistant', `❌ 上传失败: ${error.message}`);
    }
}

// 发送指令函数
async function sendCommand() {
    const command = commandInput.value.trim();
    if (!command || !currentFileId) return;

    // 显示用户消息
    addMessage('user', command);
    commandInput.value = '';

    // 禁用输入
    commandInput.disabled = true;
    sendBtn.disabled = true;
    sendBtnText.innerHTML = '<span class="loading"></span>';

    // 显示AI思考中
    addMessage('assistant', '🤔 AI正在理解你的指令...', true);

    try {
        const response = await fetch(`${API_BASE_URL}/execute`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                file_id: currentFileId,
                command: command
            })
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || '执行失败');
        }

        const result = await response.json();
        
        // 移除思考消息
        removeLastMessage();

        if (result.success) {
            // ⭐️ v0.1.0-alpha: 区分执行成功和友好提示
            if (result.execution_log && result.execution_log.length > 0) {
                // 有 execution_log，说明是真正的操作执行
                let message = '✅ 执行成功！\n\n';
                result.execution_log.forEach(log => {
                    message += log + '\n';
                });
                
                addMessage('assistant', message);

                // 显示下载按钮
                downloadBtn.style.display = 'inline-flex';
                actionButtons.style.display = 'flex';
            } else if (result.message) {
                // 没有 execution_log 但有 message，说明是友好提示或帮助信息
                addMessage('assistant', result.message);
                
                // 友好提示不显示下载按钮
            } else {
                // 既没有 log 也没有 message（不应该发生）
                addMessage('assistant', '✅ 操作完成');
            }

        } else {
            // ⭐️ v0.1.0: 优化错误显示，支持建议提示
            let errorMessage = '❌ 操作遇到问题\n\n';
            
            // 显示错误信息
            if (result.execution_log && result.execution_log.length > 0) {
                errorMessage += result.execution_log.join('\n\n');
            } else {
                errorMessage += result.error || result.message || '未知错误';
            }
            
            addMessage('assistant', errorMessage);
        }

    } catch (error) {
        removeLastMessage();
        // ⭐️ v0.1.0: 更友好的网络错误提示
        let errorMsg = '❌ 出错了\n\n';
        errorMsg += error.message || '连接服务器失败';
        errorMsg += '\n\n💡 **提示**：\n';
        errorMsg += '• 请确保后端服务正在运行\n';
        errorMsg += '• 运行命令：python -m uvicorn app.main:app --reload';
        addMessage('assistant', errorMsg);
    } finally {
        // 恢复输入
        commandInput.disabled = false;
        sendBtn.disabled = false;
        sendBtnText.textContent = '发送';
        commandInput.focus();
    }
}

// 下载文件函数
function downloadFile() {
    if (!currentFileId) return;
    
    const downloadUrl = `${API_BASE_URL}/download/${currentFileId}`;
    const link = document.createElement('a');
    link.href = downloadUrl;
    link.download = `modified_${currentFileId}.xlsx`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    
    addMessage('assistant', '📥 文件下载已开始...');
}

// 添加消息
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
    
    // 处理换行
    contentDiv.innerHTML = content.replace(/\n/g, '<br>');

    messageDiv.appendChild(avatar);
    messageDiv.appendChild(contentDiv);

    if (welcomeMessage.style.display !== 'none') {
        welcomeMessage.style.display = 'none';
    }

    messagesContainer.appendChild(messageDiv);
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
}

// 移除最后一条消息（用于移除临时消息）
function removeLastMessage() {
    const messages = messagesContainer.querySelectorAll('[data-temporary="true"]');
    if (messages.length > 0) {
        messages[messages.length - 1].remove();
    }
}

// 填充示例指令
window.fillExample = function(text) {
    if (!currentFileId) {
        addMessage('assistant', '请先上传Excel文件');
        return;
    }
    commandInput.value = text;
    commandInput.focus();
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
        console.error('❌ 无法连接到服务器，请确保后端服务已启动');
        console.error('运行: python -m uvicorn app.main:app --reload');
        return false;
    }
}

// 魔法棒按钮 - 打开功能示例模态框
magicWandBtn.addEventListener('click', () => {
    featureModal.style.display = 'flex';
});

// 关闭模态框
modalClose.addEventListener('click', () => {
    featureModal.style.display = 'none';
});

// 点击模态框背景关闭
featureModal.addEventListener('click', (e) => {
    if (e.target === featureModal) {
        featureModal.style.display = 'none';
    }
});

// 按ESC键关闭模态框
document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && featureModal.style.display === 'flex') {
        featureModal.style.display = 'none';
    }
});

// 点击功能示例，填充到输入框
document.querySelectorAll('.feature-example').forEach(example => {
    example.addEventListener('click', () => {
        const command = example.getAttribute('data-command');
        commandInput.value = command;
        featureModal.style.display = 'none';
        commandInput.focus();
    });
});

// 页面加载完成后检查服务器
checkServerConnection();

