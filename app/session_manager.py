"""
会话记忆管理模块 - 轻量级上下文记忆引擎
负责管理用户会话的历史记录，支持代词理解

Author: TJxiaobao
License: MIT
"""
import collections
import logging
from typing import List, Dict

logger = logging.getLogger(__name__)


class SessionManager:
    """
    会话管理器 - 管理文件级别的对话历史
    
    特性：
    - 内存型存储（无需数据库）
    - LRU 缓存机制（自动淘汰最久未使用的会话）
    - 限制历史轮数（控制 Token 消耗）
    """
    
    def __init__(self, max_concurrent_sessions: int = 200, max_history_rounds: int = 3):
        """
        初始化会话管理器
        
        Args:
            max_concurrent_sessions: 最大并发会话数
            max_history_rounds: 最大历史轮数（每轮包含 user + assistant 2条消息）
        """
        self.MAX_CONCURRENT_SESSIONS = max_concurrent_sessions
        self.MAX_HISTORY_ROUNDS = max_history_rounds
        
        # 使用 OrderedDict 实现 LRU 缓存
        self.cache = collections.OrderedDict()
        
        logger.info(f"✅ SessionManager 初始化完成")
        logger.info(f"   - 最大并发会话: {self.MAX_CONCURRENT_SESSIONS}")
        logger.info(f"   - 最大历史轮数: {self.MAX_HISTORY_ROUNDS} (共 {self.MAX_HISTORY_ROUNDS * 2} 条消息)")
    
    def get_history(self, file_id: str) -> List[Dict[str, str]]:
        """
        获取指定文件的历史记录
        
        Args:
            file_id: 文件ID
            
        Returns:
            历史记录列表，格式: [{"role": "user", "content": "..."}, {"role": "assistant", "content": "..."}]
        """
        if file_id not in self.cache:
            logger.debug(f"📭 文件 {file_id} 无历史记录，返回空列表")
            return []
        
        # 移到末尾（LRU 机制）
        self.cache.move_to_end(file_id)
        
        history = self.cache[file_id]
        logger.info(f"📚 获取文件 {file_id} 的历史记录，共 {len(history)} 条消息")
        
        # 输出历史记录内容（调试用）
        for i, msg in enumerate(history):
            role = msg.get("role", "unknown")
            content = msg.get("content", "")
            # 截断过长的内容
            content_preview = content[:50] + "..." if len(content) > 50 else content
            logger.debug(f"   [{i+1}] {role}: {content_preview}")
        
        return history.copy()
    
    def update_history(self, file_id: str, user_msg: str, assistant_msg: str) -> None:
        """
        更新指定文件的历史记录
        
        Args:
            file_id: 文件ID
            user_msg: 用户消息
            assistant_msg: 助手回复消息
        """
        # 获取现有历史
        history = self.get_history(file_id)
        
        # 添加新消息
        history.append({"role": "user", "content": user_msg})
        history.append({"role": "assistant", "content": assistant_msg})
        
        # Token 限制：只保留最近的 N 轮对话
        max_messages = self.MAX_HISTORY_ROUNDS * 2
        if len(history) > max_messages:
            removed_count = len(history) - max_messages
            history = history[-max_messages:]
            logger.info(f"🗑️  历史记录超限，移除最早的 {removed_count} 条消息")
        
        # 写回缓存
        self.cache[file_id] = history
        
        logger.info(f"💾 更新文件 {file_id} 的历史记录")
        logger.info(f"   - 用户: {user_msg[:50]}..." if len(user_msg) > 50 else f"   - 用户: {user_msg}")
        logger.info(f"   - 助手: {assistant_msg[:50]}..." if len(assistant_msg) > 50 else f"   - 助手: {assistant_msg}")
        logger.info(f"   - 当前历史总数: {len(history)} 条消息")
        
        # 执行缓存淘汰
        self._enforce_cache_limit()
    
    def _enforce_cache_limit(self) -> None:
        """
        强制执行缓存限制（LRU 淘汰）
        """
        while len(self.cache) > self.MAX_CONCURRENT_SESSIONS:
            # 移除最久未使用的会话（FIFO）
            removed_file_id, _ = self.cache.popitem(last=False)
            logger.warning(f"⚠️  会话数超限，移除最久未使用的会话: {removed_file_id}")
    
    def clear_history(self, file_id: str) -> None:
        """
        清除指定文件的历史记录
        
        Args:
            file_id: 文件ID
        """
        if file_id in self.cache:
            del self.cache[file_id]
            logger.info(f"🗑️  已清除文件 {file_id} 的历史记录")
    
    def get_stats(self) -> Dict:
        """
        获取统计信息
        
        Returns:
            统计信息字典
        """
        return {
            "total_sessions": len(self.cache),
            "max_sessions": self.MAX_CONCURRENT_SESSIONS,
            "max_history_rounds": self.MAX_HISTORY_ROUNDS
        }

