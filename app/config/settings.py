"""
配置管理模块

Author: TJxiaobao
License: MIT
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()


class Config:
    """应用配置"""
    
    # AI 服务配置
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    OPENAI_API_BASE = os.getenv("OPENAI_API_BASE", "https://api.openai.com/v1")
    
    # 文件配置
    UPLOAD_DIR = Path("uploads")
    MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
    ALLOWED_EXTENSIONS = {".xlsx", ".xls"}
    
    # 业务配置
    MAX_ROWS = 50000  # 最大行数限制
    MAX_COLUMNS = 100  # 最大列数限制
    
    # 缓存配置
    FILE_CACHE_TTL = 3600  # 文件缓存时间（秒）
    
    @classmethod
    def validate(cls):
        """验证配置"""
        if not cls.OPENAI_API_KEY:
            raise ValueError("未设置 OPENAI_API_KEY，请配置 .env 文件")
        
        # 确保上传目录存在
        cls.UPLOAD_DIR.mkdir(exist_ok=True)
        
        return True


# 全局配置实例
config = Config()

