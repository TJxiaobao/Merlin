"""
提示词管理模块 - 负责加载和管理所有 AI 提示词
实现代码和提示词的分离，提高可维护性

Author: TJxiaobao
License: MIT
"""
import yaml
import os
from functools import lru_cache
from typing import Dict, Any, Optional, List
import logging

logger = logging.getLogger(__name__)

# 全局提示词缓存
_prompts: Dict[str, Any] = {}
_tools: List[Dict[str, Any]] = []
_is_loaded = False
_tools_loaded = False


def load_prompts(config_path: str = "app/prompts/merlin_v1.yml") -> None:
    """
    加载提示词配置文件到内存
    
    Args:
        config_path: YAML 配置文件路径
        
    Raises:
        FileNotFoundError: 配置文件不存在
        yaml.YAMLError: YAML 格式错误
    """
    global _prompts, _is_loaded
    
    if _is_loaded:
        logger.info("提示词已加载，跳过重复加载")
        return
    
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"❌ 提示词配置文件未找到: {config_path}")
    
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            _prompts = yaml.safe_load(f)
        
        _is_loaded = True
        logger.info(f"✅ Merlin 提示词库加载成功: {config_path}")
        logger.info(f"   - 系统提示词: {len(_prompts.get('system_prompts', {}))} 个")
        logger.info(f"   - 错误消息: {len(_prompts.get('error_messages', {}))} 个")
        logger.info(f"   - 帮助消息: {len(_prompts.get('help_messages', {}))} 个")
        
    except yaml.YAMLError as e:
        raise yaml.YAMLError(f"❌ YAML 格式错误: {e}")
    except Exception as e:
        raise Exception(f"❌ 加载提示词失败: {e}")


def reload_prompts(config_path: str = "app/prompts/merlin_v1.yml") -> None:
    """
    重新加载提示词（用于开发时热更新）
    
    Args:
        config_path: YAML 配置文件路径
    """
    global _is_loaded
    _is_loaded = False
    get_prompt.cache_clear()  # 清除缓存
    load_prompts(config_path)
    logger.info("🔄 提示词已重新加载")


@lru_cache(maxsize=128)
def get_prompt(key_path: str, **kwargs) -> str:
    """
    通过点符号路径获取提示词
    
    Args:
        key_path: 点符号路径，例如 'system_prompts.main'
        **kwargs: 格式化参数，用于动态插入内容
        
    Returns:
        提示词字符串
        
    Examples:
        >>> get_prompt('system_prompts.main', headers='列1, 列2')
        >>> get_prompt('error_messages.router_failed')
        >>> get_prompt('help_messages.main')
    """
    if not _is_loaded:
        raise RuntimeError("❌ 提示词尚未加载，请先调用 load_prompts()")
    
    try:
        # 通过点符号路径访问嵌套字典
        keys = key_path.split('.')
        value = _prompts
        
        for key in keys:
            if not isinstance(value, dict):
                raise KeyError(f"路径 '{key_path}' 中的 '{key}' 不是字典")
            value = value[key]
        
        # 如果值不是字符串，直接返回
        if not isinstance(value, str):
            return value
        
        # 如果有格式化参数，进行字符串格式化
        if kwargs:
            try:
                return value.format(**kwargs)
            except KeyError as e:
                logger.warning(f"⚠️ 格式化参数缺失: {e}")
                return value
        
        return value
        
    except KeyError as e:
        error_msg = f"❌ 提示词 Key '{key_path}' 未在配置文件中定义"
        logger.error(error_msg)
        raise KeyError(error_msg) from e
    except Exception as e:
        error_msg = f"❌ 获取提示词 '{key_path}' 失败: {e}"
        logger.error(error_msg)
        raise Exception(error_msg) from e


def get_all_prompts() -> Dict[str, Any]:
    """
    获取所有提示词（用于调试）
    
    Returns:
        所有提示词的字典
    """
    if not _is_loaded:
        raise RuntimeError("❌ 提示词尚未加载，请先调用 load_prompts()")
    
    return _prompts.copy()


def load_tools(config_path: str = "app/prompts/tools_schema.yml") -> None:
    """
    加载工具 Schema 配置文件到内存
    
    Args:
        config_path: YAML 配置文件路径
        
    Raises:
        FileNotFoundError: 配置文件不存在
        yaml.YAMLError: YAML 格式错误
    """
    global _tools, _tools_loaded
    
    if _tools_loaded:
        logger.info("工具 Schema 已加载，跳过重复加载")
        return
    
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"❌ 工具 Schema 配置文件未找到: {config_path}")
    
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        
        _tools = config.get('tools', [])
        _tools_loaded = True
        logger.info(f"✅ Merlin 工具 Schema 加载成功: {config_path}")
        logger.info(f"   - 工具数量: {len(_tools)} 个")
        
    except yaml.YAMLError as e:
        raise yaml.YAMLError(f"❌ YAML 格式错误: {e}")
    except Exception as e:
        raise Exception(f"❌ 加载工具 Schema 失败: {e}")


def get_all_tools() -> List[Dict[str, Any]]:
    """
    获取所有工具 Schema
    
    Returns:
        所有工具 Schema 的列表
    """
    if not _tools_loaded:
        raise RuntimeError("❌ 工具 Schema 尚未加载，请先调用 load_tools()")
    
    return _tools.copy()


def get_tools_by_names(tool_names: List[str]) -> List[Dict[str, Any]]:
    """
    根据工具名称获取指定的工具 Schema
    
    Args:
        tool_names: 工具名称列表
        
    Returns:
        匹配的工具 Schema 列表
    """
    if not _tools_loaded:
        raise RuntimeError("❌ 工具 Schema 尚未加载，请先调用 load_tools()")
    
    filtered = [tool for tool in _tools if tool["function"]["name"] in tool_names]
    return filtered


def is_loaded() -> bool:
    """
    检查提示词是否已加载
    
    Returns:
        True 如果已加载，否则 False
    """
    return _is_loaded


def is_tools_loaded() -> bool:
    """
    检查工具 Schema 是否已加载
    
    Returns:
        True 如果已加载，否则 False
    """
    return _tools_loaded

