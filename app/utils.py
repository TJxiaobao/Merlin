"""
工具函数模块
"""
from typing import Any
import logging

logger = logging.getLogger(__name__)


def convert_value(value: Any) -> Any:
    """
    智能类型转换：尝试将字符串转换为数字
    Args:
        value: 输入值
    Returns:
        转换后的值
    """
    if not isinstance(value, str):
        return value
    
    # 尝试转换为整数
    try:
        if '.' not in value:
            return int(value)
    except (ValueError, AttributeError):
        pass
    
    # 尝试转换为浮点数
    try:
        return float(value)
    except (ValueError, AttributeError):
        pass
    
    # 无法转换，保持原样
    return value


def validate_file_extension(filename: str, allowed_extensions: set) -> bool:
    """
    验证文件扩展名
    Args:
        filename: 文件名
        allowed_extensions: 允许的扩展名集合
    Returns:
        是否有效
    """
    from pathlib import Path
    return Path(filename).suffix.lower() in allowed_extensions


def format_log_message(level: str, message: str, details: dict = None) -> dict:
    """
    格式化日志消息
    Args:
        level: 日志级别 (success/error/warning/info)
        message: 消息内容
        details: 详细信息
    Returns:
        格式化后的日志字典
    """
    log = {
        "level": level,
        "message": message,
        "timestamp": None  # TODO: 添加时间戳
    }
    
    if details:
        log["details"] = details
    
    return log


def fuzzy_match_column(target: str, available_columns: list, threshold: float = 0.6) -> str:
    """
    模糊匹配列名
    Args:
        target: 目标列名
        available_columns: 可用的列名列表
        threshold: 匹配阈值
    Returns:
        最匹配的列名，如果没有找到则返回 None
    
    TODO: 实现更复杂的模糊匹配算法（如 Levenshtein 距离）
    """
    target_lower = target.lower()
    
    # 精确匹配
    if target in available_columns:
        return target
    
    # 忽略大小写匹配
    for col in available_columns:
        if col.lower() == target_lower:
            return col
    
    # 包含匹配
    for col in available_columns:
        if target_lower in col.lower() or col.lower() in target_lower:
            return col
    
    return None


class OperationLogger:
    """操作日志记录器"""
    
    def __init__(self):
        self.logs = []
    
    def success(self, message: str, **details):
        """记录成功操作"""
        log = f"✅ {message}"
        if details:
            log += f"\n   详情: {details}"
        self.logs.append(log)
        logger.info(message)
    
    def error(self, message: str, **details):
        """记录错误"""
        log = f"❌ {message}"
        if details:
            log += f"\n   详情: {details}"
        self.logs.append(log)
        logger.error(message)
    
    def warning(self, message: str, **details):
        """记录警告"""
        log = f"⚠️  {message}"
        if details:
            log += f"\n   详情: {details}"
        self.logs.append(log)
        logger.warning(message)
    
    def info(self, message: str):
        """记录信息"""
        log = f"ℹ️  {message}"
        self.logs.append(log)
        logger.info(message)
    
    def get_all(self) -> list:
        """获取所有日志"""
        return self.logs
    
    def clear(self):
        """清空日志"""
        self.logs = []

