/**
 * Merlin 流式响应显示逻辑
 * 核心：在同一个消息气泡中逐步更新内容
 */

// 当前正在更新的流式消息气泡
let currentStreamingMessage = null;
let streamingContent = [];

/**
 * 开始一个新的流式消息
 */
export function startStreamingMessage() {
    streamingContent = [];
    
    // 创建消息容器
    const messageDiv = document.createElement('div');
    messageDiv.className = 'message assistant streaming';
    messageDiv.id = 'streaming-message';
    
    const avatar = document.createElement('div');
    avatar.className = 'message-avatar';
    avatar.textContent = '🧙';
    
    const contentDiv = document.createElement('div');
    contentDiv.className = 'message-content';
    contentDiv.id = 'streaming-content';
    
    messageDiv.appendChild(avatar);
    messageDiv.appendChild(contentDiv);
    
    currentStreamingMessage = messageDiv;
    
    return messageDiv;
}

/**
 * 更新流式消息内容
 */
export function updateStreamingMessage(newLine, options = {}) {
    if (!currentStreamingMessage) {
        return;
    }
    
    const contentDiv = document.getElementById('streaming-content');
    if (!contentDiv) return;
    
    const { type = 'info', replace = false, showProgress = false, progress = null } = options;
    
    if (replace && streamingContent.length > 0) {
        // 替换最后一行（用于更新进度）
        streamingContent[streamingContent.length - 1] = { text: newLine, type };
    } else {
        // 添加新行
        streamingContent.push({ text: newLine, type });
    }
    
    // 重新渲染内容
    let html = '';
    streamingContent.forEach(item => {
        const icon = getIconForType(item.type);
        const cssClass = getCssClassForType(item.type);
        html += `<div class="streaming-line ${cssClass}">${icon} ${item.text}</div>`;
    });
    
    // 如果有进度条
    if (showProgress && progress) {
        html += `
            <div class="progress-bar">
                <div class="progress-fill" style="width: ${progress.percent}%;"></div>
            </div>
            <div style="font-size: 0.8em; color: var(--text-secondary); margin-top: 5px; text-align: center;">
                任务 ${progress.current} / ${progress.total}
            </div>
        `;
    }
    
    contentDiv.innerHTML = html;
}

/**
 * 结束流式消息，添加下载按钮
 */
export function finishStreamingMessage(showDownload = false) {
    if (!currentStreamingMessage) {
        return;
    }
    
    const contentDiv = document.getElementById('streaming-content');
    if (!contentDiv) return;
    
    // 移除 streaming 类（不再更新）
    currentStreamingMessage.classList.remove('streaming');
    
    // 如果需要下载按钮
    if (showDownload) {
        const downloadBtn = document.createElement('button');
        downloadBtn.className = 'message-download-btn';
        downloadBtn.innerHTML = '📥 下载修改后的文件';
        downloadBtn.onclick = () => {
            window.downloadModifiedFile();
        };
        contentDiv.appendChild(downloadBtn);
    }
    
    currentStreamingMessage = null;
    streamingContent = [];
}

/**
 * 取消流式消息（出错时）
 */
export function cancelStreamingMessage() {
    if (currentStreamingMessage) {
        currentStreamingMessage.remove();
    }
    currentStreamingMessage = null;
    streamingContent = [];
}

// 工具函数
function getIconForType(type) {
    const icons = {
        'start': '🧙',
        'translating': '🤖',
        'translation_done': '✅',
        'task_start': '⏳',
        'task_success': '✅',
        'task_error': '❌',
        'rate_limit': '⏳',
        'hint': '💡',
        'warning': '⚠️',
        'saving': '💾',
        'done': '🎉',
        'error': '❌'
    };
    return icons[type] || '';
}

function getCssClassForType(type) {
    if (type === 'task_success' || type === 'translation_done' || type === 'done') {
        return 'success';
    } else if (type === 'task_error' || type === 'error') {
        return 'error';
    } else if (type === 'warning' || type === 'hint') {
        return 'warning';
    } else {
        return 'info';
    }
}

