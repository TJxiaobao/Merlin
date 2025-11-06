"""
AI翻译模块 - 将自然语言指令翻译成结构化的工具调用
这是"大脑"，负责理解用户意图
"""
from openai import OpenAI
from typing import List, Dict, Any, Optional
import json
import logging

from .config import config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class AITranslator:
    """AI翻译器 - 使用LLM的Function Calling能力"""
    
    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None):
        """
        初始化AI翻译器
        Args:
            api_key: API密钥，如果为None则从配置读取
            base_url: API基础URL，支持兼容OpenAI接口的服务
        """
        self.api_key = api_key or config.OPENAI_API_KEY
        self.base_url = base_url or config.OPENAI_API_BASE
        
        if not self.api_key:
            raise ValueError("请设置OPENAI_API_KEY环境变量")
        
        self.client = OpenAI(
            api_key=self.api_key,
            base_url=self.base_url
        )
        
        # 智能选择模型
        self.model = self._select_model()
        logger.info(f"AI翻译器初始化完成，使用API: {self.base_url}")
        logger.info(f"使用模型: {self.model}")
    
    def _select_model(self) -> str:
        """
        根据 API Base URL 智能选择模型
        Returns:
            模型名称
        """
        if "moonshot" in self.base_url.lower():
            # Kimi / 月之暗面
            return "moonshot-v1-8k"
        elif "deepseek" in self.base_url.lower():
            # DeepSeek
            return "deepseek-chat"
        else:
            # OpenAI 或其他
            return "gpt-4o-mini"
    
    def get_tools_definition(self) -> List[Dict]:
        """
        定义可用的工具（Function Calling的schema）
        这是告诉AI它可以使用哪些工具
        
        注意：为了兼容不同的AI服务（Kimi不支持数组类型定义），
        这里统一使用string类型，AI会自动处理数字
        """
        return [
            {
                "type": "function",
                "function": {
                    "name": "set_column_value",
                    "description": "给整列赋值，所有行都会被设置为相同的值",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "column": {
                                "type": "string",
                                "description": "要设置的列名（必须是用户表格中实际存在的列名）"
                            },
                            "value": {
                                "type": "string",
                                "description": "要设置的值，可以是数字（如0.13、100）或文本"
                            }
                        },
                        "required": ["column", "value"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "set_by_condition",
                    "description": "根据条件筛选行，然后给这些行的指定列赋值",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "condition_column": {
                                "type": "string",
                                "description": "作为条件的列名"
                            },
                            "condition_value": {
                                "type": "string",
                                "description": "条件值，可以是数字或文本"
                            },
                            "target_column": {
                                "type": "string",
                                "description": "要修改的目标列名"
                            },
                            "target_value": {
                                "type": "string",
                                "description": "要设置的目标值，可以是数字（如0.13、100）或文本"
                            },
                            "match_type": {
                                "type": "string",
                                "enum": ["exact", "startswith", "contains"],
                                "description": "匹配类型: exact(精确匹配), startswith(前缀匹配), contains(包含匹配)",
                                "default": "exact"
                            }
                        },
                        "required": ["condition_column", "condition_value", "target_column", "target_value"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "copy_column",
                    "description": "将一列的值复制到另一列",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "source_column": {
                                "type": "string",
                                "description": "源列名"
                            },
                            "target_column": {
                                "type": "string",
                                "description": "目标列名"
                            }
                        },
                        "required": ["source_column", "target_column"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "set_by_mapping",
                    "description": "根据映射表批量设置列值。适用场景：同一列的多个不同值需要设置为不同的目标值。例如：'把设备编码为xxxx的价格设为10，yyy的设为20，zzz的设为30'",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "condition_column": {
                                "type": "string",
                                "description": "作为条件的列名"
                            },
                            "target_column": {
                                "type": "string",
                                "description": "要修改的目标列名"
                            },
                            "mapping": {
                                "type": "object",
                                "description": "映射关系，键为条件值，值为目标值。例如: {\"xxxx\": \"10\", \"yyy\": \"20\"}。注意：所有值都使用字符串格式"
                            },
                            "match_type": {
                                "type": "string",
                                "enum": ["exact", "startswith", "contains"],
                                "description": "匹配类型: exact(精确匹配), startswith(前缀匹配), contains(包含匹配)",
                                "default": "exact"
                            }
                        },
                        "required": ["condition_column", "target_column", "mapping"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_summary",
                    "description": "统计某列的数据分布情况。适用场景：用户想知道某个字段有哪些值，每个值有多少条数据。例如：'统计设备类型的分布'、'帮我总结设备编码的情况'",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "column": {
                                "type": "string",
                                "description": "要统计的列名"
                            },
                            "top_n": {
                                "type": "string",
                                "description": "返回前N个最常见的值，默认10",
                                "default": "10"
                            }
                        },
                        "required": ["column"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "perform_math",
                    "description": "执行数学计算。适用场景：需要对列进行数学运算。例如：'让总价等于数量乘以单价'、'计算利润等于售价减成本'、'把未税单价乘以1.13存入含税单价'",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "target_column": {
                                "type": "string",
                                "description": "结果存储的目标列名（可以是新列或现有列）"
                            },
                            "source_column_1": {
                                "type": "string",
                                "description": "第一个操作数的列名"
                            },
                            "operator": {
                                "type": "string",
                                "enum": ["add", "subtract", "multiply", "divide"],
                                "description": "运算符: add(加), subtract(减), multiply(乘), divide(除)"
                            },
                            "source_column_2_or_number": {
                                "type": "string",
                                "description": "第二个操作数，可以是列名或数字（字符串格式）"
                            },
                            "round_to": {
                                "type": "string",
                                "description": "保留小数位数，可选参数"
                            }
                        },
                        "required": ["target_column", "source_column_1", "operator", "source_column_2_or_number"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "trim_whitespace",
                    "description": "清理列中的首尾空格。适用场景：数据清洗，去除不必要的空格。例如：'清理设备名称列的空格'、'去掉备注列前后的空格'",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "column": {
                                "type": "string",
                                "description": "要清理空格的列名"
                            }
                        },
                        "required": ["column"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "fill_missing_values",
                    "description": "填充空白单元格。适用场景：将列中的空值填充为指定内容。例如：'把备注列的空白单元格填充为N/A'、'把空的状态都改成待处理'",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "column": {
                                "type": "string",
                                "description": "要填充空值的列名"
                            },
                            "fill_value": {
                                "type": "string",
                                "description": "用于填充空值的内容"
                            }
                        },
                        "required": ["column", "fill_value"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "find_and_replace",
                    "description": "查找并替换文本。适用场景：批量替换列中的特定文本。例如：'把客户区域列里的北京都替换成华北区'、'把所有的旧名称改成新名称'",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "column": {
                                "type": "string",
                                "description": "要进行查找替换的列名"
                            },
                            "find_text": {
                                "type": "string",
                                "description": "要查找的文本"
                            },
                            "replace_text": {
                                "type": "string",
                                "description": "替换成的文本"
                            }
                        },
                        "required": ["column", "find_text", "replace_text"]
                    }
                }
            }
        ]
    
    def build_system_prompt(self, headers: List[str]) -> str:
        """
        构建系统提示词
        Args:
            headers: 用户表格的列名列表
        Returns:
            系统提示词
        """
        return f"""你是一个Excel操作助手。用户会用自然语言告诉你想对Excel表格做什么修改。
你的任务是理解用户的意图，然后调用合适的工具来完成操作。

用户的Excel表格有以下列名：
{', '.join(headers)}

重要规则：
1. 只能使用上述列表中存在的列名
2. 如果用户提到的列名不精确（如"价格"），你需要从上述列表中找到最匹配的列名（如"未税单价"）

工具选择规则：
3. 如果用户说"把某列设为XXX"，使用 set_column_value 工具
4. 如果用户说"把符合XX条件的某列设为XXX"，使用 set_by_condition 工具
5. 如果用户说"把A列复制到B列"，使用 copy_column 工具
6. **如果用户说"把XX的某列设为A，YY的设为B，ZZ的设为C"（多个映射关系），使用 set_by_mapping 工具**
   - 例如："把设备编码为196001的价格设为10，196002的设为20，196003的设为30"
   - 应翻译为：set_by_mapping(condition_column="设备编码", target_column="价格", mapping={{"196001": "10", "196002": "20", "196003": "30"}})
7. **如果用户想要统计、查看、总结某列的数据分布，使用 get_summary 工具**
   - 例如："统计设备类型的分布"、"帮我看看设备编码有哪些"、"总结一下设备类型"
   - 应翻译为：get_summary(column="设备类型")
8. **如果用户想进行数学计算（加减乘除），使用 perform_math 工具**
   - 例如："让总价等于数量乘以单价"、"计算利润等于售价减成本"、"把未税单价乘以1.13存入含税单价"
   - 应翻译为：perform_math(target_column="总价", source_column_1="数量", operator="multiply", source_column_2_or_number="单价")
9. **如果用户要清理空格，使用 trim_whitespace 工具**
   - 例如："清理设备名称列的空格"、"去掉备注列前后的空格"
10. **如果用户要填充空值，使用 fill_missing_values 工具**
   - 例如："把备注列的空白填充为N/A"
11. **如果用户要查找替换文本，使用 find_and_replace 工具**
   - 例如："把客户区域列里的北京都替换成华北区"

匹配类型规则：
12. 当用户说"开头"、"以...开头"时，使用 match_type="startswith"
13. 当用户说"包含"时，使用 match_type="contains"  
14. 默认使用 match_type="exact"（精确匹配）

请根据用户的指令调用合适的工具。"""
    
    def translate(self, user_command: str, headers: List[str]) -> Dict[str, Any]:
        """
        翻译用户指令为工具调用
        Args:
            user_command: 用户的自然语言指令
            headers: 表格的列名列表
        Returns:
            翻译结果，包含tool_calls或错误信息
        """
        try:
            logger.info(f"开始翻译指令: {user_command}")
            logger.info(f"可用列名: {headers}")
            
            # 调用AI
            response = self.client.chat.completions.create(
                model=self.model,  # 根据API自动选择模型
                messages=[
                    {"role": "system", "content": self.build_system_prompt(headers)},
                    {"role": "user", "content": user_command}
                ],
                tools=self.get_tools_definition(),
                tool_choice="auto"  # 让AI自动决定是否使用工具
            )
            
            message = response.choices[0].message
            
            # 检查AI是否调用了工具
            if not message.tool_calls:
                # AI没有调用工具，可能是因为指令不明确
                error_msg = f"AI未能理解您的指令。AI的回复: {message.content}"
                logger.warning(error_msg)
                return {
                    "success": False,
                    "error": error_msg,
                    "ai_message": message.content
                }
            
            # 解析工具调用
            tool_calls = []
            for tool_call in message.tool_calls:
                function_name = tool_call.function.name
                function_args = json.loads(tool_call.function.arguments)
                
                tool_calls.append({
                    "tool_name": function_name,
                    "parameters": function_args
                })
                
                # 使用 json.dumps 避免字典中的花括号导致格式化错误
                logger.info(f"AI翻译结果: {function_name}({json.dumps(function_args, ensure_ascii=False)})")
            
            return {
                "success": True,
                "tool_calls": tool_calls
            }
            
        except Exception as e:
            error_msg = f"AI翻译失败: {str(e)}"
            logger.error(error_msg)
            return {
                "success": False,
                "error": error_msg
            }


# 创建全局翻译器实例（延迟初始化）
_translator_instance = None

def get_translator() -> AITranslator:
    """获取AI翻译器单例"""
    global _translator_instance
    if _translator_instance is None:
        _translator_instance = AITranslator()
    return _translator_instance

