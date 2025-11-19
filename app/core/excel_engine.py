"""
Excel操作引擎 - 使用Pandas执行实际的表格操作
这个模块是"双手"，只负责执行，不负责理解

Author: TJxiaobao
License: MIT
"""
import pandas as pd
from pathlib import Path
from typing import Dict, List, Any, Optional
import logging
from difflib import get_close_matches  # v0.1.0: 用于模糊匹配列名

from ..utils.helpers import convert_value
from ..config.settings import config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ExcelEngine:
    """Excel操作引擎"""
    
    def __init__(self, file_path: str):
        """
        初始化引擎
        Args:
            file_path: Excel文件路径
        """
        self.file_path = Path(file_path)
        self.df = pd.read_excel(file_path)
        self.original_df = self.df.copy()  # 保留原始数据副本
        self.execution_log = []  # 操作日志
        
        logger.info(f"已加载文件: {file_path}")
        logger.info(f"行数: {len(self.df)}, 列数: {len(self.df.columns)}")
        logger.info(f"列名: {list(self.df.columns)}")
    
    @staticmethod
    def _convert_value(value: Any) -> Any:
        """智能类型转换（使用工具类）"""
        return convert_value(value)
    
    def _generate_column_not_found_error(self, column_name: str) -> Dict:
        """
        生成列不存在时的友好错误信息（带模糊匹配建议）
        Args:
            column_name: 用户输入的列名
        Returns:
            包含错误和建议的字典
        """
        # 使用模糊匹配找相似的列名
        similar_columns = get_close_matches(column_name, self.df.columns, n=3, cutoff=0.6)
        
        error_msg = f"❌ 列 '{column_name}' 不存在"
        
        if similar_columns:
            suggestion = f"💡 **建议**：您是否想操作以下列？\n"
            suggestion += "\n".join([f"  • {col}" for col in similar_columns])
            suggestion += f"\n\n当前表格的所有列：{', '.join(self.df.columns[:5])}{'...' if len(self.df.columns) > 5 else ''}"
        else:
            suggestion = f"💡 **建议**：\n• 当前表格的列：{', '.join(self.df.columns)}\n• 请检查列名拼写和大小写"
        
        return {
            "success": False,
            "error": error_msg,
            "suggestion": suggestion
        }
    
    def get_headers(self) -> List[str]:
        """获取所有列名"""
        return list(self.df.columns)
    
    def get_preview(self, rows: int = 5) -> Dict:
        """获取数据预览"""
        return {
            "headers": self.get_headers(),
            "total_rows": len(self.df),
            "preview_data": self.df.head(rows).to_dict(orient='records')
        }
    
    def set_column_value(self, column: str, value: Any) -> Dict:
        """
        给整列赋值
        Args:
            column: 列名
            value: 要设置的值
        Returns:
            执行结果
        """
        if column not in self.df.columns:
            return self._generate_column_not_found_error(column)
        
        try:
            # 智能类型转换
            value = self._convert_value(value)
            affected_rows = len(self.df)
            self.df[column] = value
            
            log_msg = f"✅ 已将'{column}'列的所有 {affected_rows} 行设置为: {value}"
            logger.info(log_msg)
            self.execution_log.append(log_msg)
            
            return {
                "success": True,
                "message": log_msg,
                "affected_rows": affected_rows
            }
        except Exception as e:
            error_msg = f"执行失败: {str(e)}"
            logger.error(error_msg)
            return {"success": False, "error": error_msg}
    
    def set_by_condition(
        self, 
        condition_column: str,
        condition_value: Any,
        target_column: str,
        target_value: Any,
        match_type: str = "exact"  # exact, startswith, contains
    ) -> Dict:
        """
        根据条件给指定列赋值
        Args:
            condition_column: 条件列名
            condition_value: 条件值
            target_column: 目标列名
            target_value: 要设置的值
            match_type: 匹配类型 (exact/startswith/contains)
        Returns:
            执行结果
        """
        # 检查列是否存在
        if condition_column not in self.df.columns:
            return {
                "success": False, 
                "error": f"条件列'{condition_column}'不存在"
            }
        if target_column not in self.df.columns:
            return {
                "success": False,
                "error": f"目标列'{target_column}'不存在"
            }
        
        try:
            # 智能类型转换
            condition_value = self._convert_value(condition_value)
            target_value = self._convert_value(target_value)
            # 根据匹配类型创建条件
            if match_type == "exact":
                mask = self.df[condition_column] == condition_value
                condition_desc = f"'{condition_column}' == '{condition_value}'"
            elif match_type == "startswith":
                mask = self.df[condition_column].astype(str).str.startswith(str(condition_value))
                condition_desc = f"'{condition_column}'以'{condition_value}'开头"
            elif match_type == "contains":
                mask = self.df[condition_column].astype(str).str.contains(str(condition_value))
                condition_desc = f"'{condition_column}'包含'{condition_value}'"
            else:
                return {"success": False, "error": f"不支持的匹配类型: {match_type}"}
            
            # 执行赋值
            affected_rows = mask.sum()
            if affected_rows == 0:
                # 提供可用的值列表，帮助用户和 AI 理解为什么匹配失败
                unique_values = self.df[condition_column].unique().tolist()
                unique_values_str = ", ".join([f"'{v}'" for v in unique_values[:10]])  # 只显示前 10 个
                if len(unique_values) > 10:
                    unique_values_str += f" (还有 {len(unique_values) - 10} 个值)"
                
                log_msg = f"⚠️  没有找到符合条件的行 (条件: {condition_desc})"
                suggestion = f"💡 '{condition_column}' 列的可用值: {unique_values_str}"
                
                logger.warning(log_msg)
                logger.info(suggestion)
                self.execution_log.append(log_msg)
                self.execution_log.append(suggestion)
                
                return {
                    "success": False,  # 改为 False，因为没有匹配到任何行应该视为失败
                    "error": log_msg,
                    "suggestion": suggestion,
                    "affected_rows": 0
                }
            
            self.df.loc[mask, target_column] = target_value
            
            # 记录受影响的行号
            affected_indices = self.df[mask].index.tolist()
            
            log_msg = (
                f"✅ 已修改 {affected_rows} 行\n"
                f"   条件: {condition_desc}\n"
                f"   操作: '{target_column}' → {target_value}\n"
                f"   行号: {affected_indices[:10]}"  # 只显示前10个行号
            )
            if len(affected_indices) > 10:
                log_msg += f" ... (还有{len(affected_indices) - 10}行)"
            
            logger.info(log_msg)
            self.execution_log.append(log_msg)
            
            return {
                "success": True,
                "message": log_msg,
                "affected_rows": affected_rows,
                "affected_indices": affected_indices[:100]  # 最多返回100个行号
            }
            
        except Exception as e:
            error_msg = f"执行失败: {str(e)}"
            logger.error(error_msg)
            return {"success": False, "error": error_msg}
    
    def copy_column(self, source_column: str, target_column: str) -> Dict:
        """
        复制列
        Args:
            source_column: 源列名
            target_column: 目标列名
        Returns:
            执行结果
        """
        if source_column not in self.df.columns:
            return {"success": False, "error": f"源列'{source_column}'不存在"}
        if target_column not in self.df.columns:
            return {"success": False, "error": f"目标列'{target_column}'不存在"}
        
        try:
            self.df[target_column] = self.df[source_column]
            affected_rows = len(self.df)
            
            log_msg = f"✅ 已将'{source_column}'的值复制到'{target_column}' ({affected_rows}行)"
            logger.info(log_msg)
            self.execution_log.append(log_msg)
            
            return {
                "success": True,
                "message": log_msg,
                "affected_rows": affected_rows
            }
        except Exception as e:
            error_msg = f"执行失败: {str(e)}"
            logger.error(error_msg)
            return {"success": False, "error": error_msg}
    
    def add_column(self, column_name: str, default_value: Any = None) -> Dict:
        """
        新增列
        Args:
            column_name: 新列名
            default_value: 默认值（可选，默认为空）
        Returns:
            执行结果
        """
        if column_name in self.df.columns:
            return {"success": False, "error": f"列'{column_name}'已存在"}
        
        try:
            # 添加新列，默认值为 None 或用户指定的值
            converted_value = self._convert_value(default_value) if default_value is not None else None
            self.df[column_name] = converted_value
            
            log_msg = f"✅ 已新增列'{column_name}'"
            if default_value is not None:
                log_msg += f"，默认值：{default_value}"
            
            logger.info(log_msg)
            self.execution_log.append(log_msg)
            return {
                "success": True,
                "message": log_msg,
                "column_name": column_name,
                "default_value": default_value
            }
        except Exception as e:
            error_msg = f"新增列失败: {str(e)}"
            logger.error(error_msg)
            return {"success": False, "error": error_msg}
    
    def delete_column(self, column_name: str) -> Dict:
        """
        删除列
        Args:
            column_name: 要删除的列名
        Returns:
            执行结果
        """
        if column_name not in self.df.columns:
            return self._generate_column_not_found_error(column_name)
        
        try:
            self.df = self.df.drop(columns=[column_name])
            
            log_msg = f"✅ 已删除列'{column_name}'"
            logger.info(log_msg)
            self.execution_log.append(log_msg)
            return {
                "success": True,
                "message": log_msg,
                "column_name": column_name
            }
        except Exception as e:
            error_msg = f"删除列失败: {str(e)}"
            logger.error(error_msg)
            return {"success": False, "error": error_msg}
    
    def set_by_mapping(
        self,
        condition_column: str,
        target_column: str,
        mapping: dict,
        match_type: str = "exact"
    ) -> Dict:
        """
        根据映射表批量设置值
        Args:
            condition_column: 条件列名
            target_column: 目标列名
            mapping: 映射关系 {条件值: 目标值}，例如 {"196001": 10, "196002": 20}
            match_type: 匹配类型 (exact/startswith/contains)
        Returns:
            执行结果
        """
        # 检查列是否存在
        if condition_column not in self.df.columns:
            return {
                "success": False,
                "error": f"条件列'{condition_column}'不存在"
            }
        if target_column not in self.df.columns:
            return {
                "success": False,
                "error": f"目标列'{target_column}'不存在"
            }
        
        if not mapping or not isinstance(mapping, dict):
            return {
                "success": False,
                "error": "映射表为空或格式错误"
            }
        
        try:
            total_affected = 0
            details = []
            
            for condition_value, target_value in mapping.items():
                # 智能类型转换
                condition_value = self._convert_value(condition_value)
                target_value = self._convert_value(target_value)
                
                # 根据匹配类型创建条件
                if match_type == "exact":
                    mask = self.df[condition_column] == condition_value
                elif match_type == "startswith":
                    mask = self.df[condition_column].astype(str).str.startswith(str(condition_value))
                elif match_type == "contains":
                    mask = self.df[condition_column].astype(str).str.contains(str(condition_value))
                else:
                    return {"success": False, "error": f"不支持的匹配类型: {match_type}"}
                
                # 执行赋值
                affected = mask.sum()
                if affected > 0:
                    self.df.loc[mask, target_column] = target_value
                    total_affected += affected
                    details.append(f"    '{condition_value}' → {target_value} ({affected}行)")
                else:
                    details.append(f"    '{condition_value}' → {target_value} (0行，未找到匹配)")
            
            # 构建日志消息
            log_msg = (
                f"✅ 批量映射完成，共修改 {total_affected} 行\n"
                f"   条件列: '{condition_column}'\n"
                f"   目标列: '{target_column}'\n"
                f"   映射规则:\n" + "\n".join(details)
            )
            
            logger.info(log_msg)
            self.execution_log.append(log_msg)
            
            return {
                "success": True,
                "message": log_msg,
                "affected_rows": total_affected,
                "mapping_count": len(mapping)
            }
            
        except Exception as e:
            error_msg = f"执行失败: {str(e)}"
            logger.error(error_msg)
            return {"success": False, "error": error_msg}
    
    def get_summary(self, column: str, top_n: int = 10) -> Dict:
        """
        统计某列的数据分布情况
        Args:
            column: 要统计的列名
            top_n: 返回前N个最常见的值（默认10）
        Returns:
            统计结果
        """
        # 检查列是否存在
        if column not in self.df.columns:
            return {
                "success": False,
                "error": f"列 '{column}' 不存在"
            }
        
        try:
            # 统计各值的数量
            value_counts = self.df[column].value_counts()
            
            # 构建统计信息
            summary_lines = []
            total_count = len(self.df)
            non_null_count = self.df[column].notna().sum()
            null_count = total_count - non_null_count
            
            # 取前N个
            top_values = value_counts.head(top_n)
            
            summary_lines.append(f"📊 列 '{column}' 统计结果:")
            summary_lines.append(f"   总行数: {total_count}")
            summary_lines.append(f"   有效数据: {non_null_count}")
            if null_count > 0:
                summary_lines.append(f"   空值: {null_count}")
            summary_lines.append(f"\n   数据分布（前{min(top_n, len(top_values))}项）:")
            
            for value, count in top_values.items():
                percentage = (count / total_count) * 100
                summary_lines.append(f"     • '{value}': {count} 条 ({percentage:.1f}%)")
            
            # 如果还有其他值
            if len(value_counts) > top_n:
                other_count = value_counts[top_n:].sum()
                other_percentage = (other_count / total_count) * 100
                summary_lines.append(f"     • 其他: {other_count} 条 ({other_percentage:.1f}%)")
            
            log_msg = "\n".join(summary_lines)
            logger.info(log_msg)
            self.execution_log.append(log_msg)
            
            # 返回结构化数据
            return {
                "success": True,
                "message": log_msg,
                "is_analysis": True,  # ⭐️ 标记为分析类工具，不需要保存文件
                "column": column,
                "total_rows": total_count,
                "non_null_count": non_null_count,
                "null_count": null_count,
                "value_counts": {str(k): int(v) for k, v in top_values.items()},
                "unique_values": len(value_counts)
            }
            
        except Exception as e:
            error_msg = f"统计失败: {str(e)}"
            logger.error(error_msg)
            return {"success": False, "error": error_msg}
    
    def perform_math(
        self,
        target_column: str,
        source_column_1: str,
        operator: str,
        source_column_2_or_number: str,
        round_to: int = None
    ) -> Dict:
        """
        执行数学计算
        Args:
            target_column: 目标列名（结果存储位置）
            source_column_1: 第一个操作数列名
            operator: 运算符 (add/subtract/multiply/divide)
            source_column_2_or_number: 第二个操作数（列名或数字）
            round_to: 保留小数位数（可选）
        Returns:
            执行结果
        """
        import pandas as pd
        import numpy as np
        
        # 检查第一个列是否存在
        if source_column_1 not in self.df.columns:
            return self._generate_column_not_found_error(source_column_1)
        
        try:
            # ⭐️ 智能检查：第一个列是否全部为文本
            col_1_numeric = pd.to_numeric(self.df[source_column_1], errors='coerce')
            non_numeric_count_1 = col_1_numeric.isna().sum()
            total_count = len(self.df)
            
            # 如果超过50%无法转换，很可能是文本列
            if non_numeric_count_1 > total_count * 0.5:
                sample_values = self.df[source_column_1].head(3).tolist()
                return {
                    "success": False,
                    "error": f"❌ 列 '{source_column_1}' 主要包含文本，无法进行数学运算",
                    "suggestion": f"💡 **建议**：\n• 该列的样本值：{sample_values}\n• 如果包含数字，请先使用'查找替换'清理特殊字符\n• 或者选择一个纯数字列进行计算"
                }
            
            # 准备第一个操作数（将非数字转为0）
            col_1_data = col_1_numeric.fillna(0)
            
            # 准备第二个操作数
            is_column = source_column_2_or_number in self.df.columns
            
            if is_column:
                # ⭐️ 智能检查：第二个列是否全部为文本
                col_2_numeric = pd.to_numeric(self.df[source_column_2_or_number], errors='coerce')
                non_numeric_count_2 = col_2_numeric.isna().sum()
                
                # 如果超过50%无法转换，很可能是文本列
                if non_numeric_count_2 > total_count * 0.5:
                    sample_values = self.df[source_column_2_or_number].head(3).tolist()
                    return {
                        "success": False,
                        "error": f"❌ 列 '{source_column_2_or_number}' 主要包含文本，无法进行数学运算",
                        "suggestion": f"💡 **建议**：\n• 该列的样本值：{sample_values}\n• 如果包含数字，请先使用'查找替换'清理特殊字符\n• 或者选择一个纯数字列进行计算"
                    }
                
                # 如果是列名
                col_2_data = col_2_numeric.fillna(0)
                operand_desc = f"列 '{source_column_2_or_number}'"
            else:
                # 如果是数字
                try:
                    col_2_data = float(self._convert_value(source_column_2_or_number))
                    non_numeric_count_2 = 0
                    operand_desc = f"数字 {col_2_data}"
                except:
                    return {
                        "success": False,
                        "error": f"❌ '{source_column_2_or_number}' 既不是有效的列名也不是有效的数字",
                        "suggestion": f"💡 **建议**：\n• 检查列名是否正确（当前表格列名：{', '.join(self.df.columns[:5])}{'...' if len(self.df.columns) > 5 else ''}）\n• 如果是数字，请确保没有多余的空格或特殊字符"
                    }
            
            # 执行运算
            if operator == "add":
                result = col_1_data + col_2_data
                op_symbol = "+"
            elif operator == "subtract":
                result = col_1_data - col_2_data
                op_symbol = "-"
            elif operator == "multiply":
                result = col_1_data * col_2_data
                op_symbol = "×"
            elif operator == "divide":
                result = col_1_data / col_2_data
                # 处理除零
                result = result.replace([np.inf, -np.inf], 0)
                op_symbol = "÷"
            else:
                return {
                    "success": False,
                    "error": f"不支持的运算符: {operator}"
                }
            
            # 四舍五入
            if round_to is not None:
                result = result.round(int(round_to))
                round_desc = f"，保留{round_to}位小数"
            else:
                round_desc = ""
            
            # 保存结果
            is_new_column = target_column not in self.df.columns
            self.df[target_column] = result
            
            # 构建日志
            action = "创建" if is_new_column else "更新"
            log_msg = f"✅ 已{action}列 '{target_column}' = '{source_column_1}' {op_symbol} {operand_desc}{round_desc}"
            
            # 添加警告信息
            warnings = []
            if non_numeric_count_1 > 0:
                warnings.append(f"⚠️  '{source_column_1}' 列中有 {non_numeric_count_1} 个非数字值已视为 0")
            if is_column and non_numeric_count_2 > 0:
                warnings.append(f"⚠️  '{source_column_2_or_number}' 列中有 {non_numeric_count_2} 个非数字值已视为 0")
            
            if warnings:
                log_msg += "\n" + "\n".join(warnings)
            
            logger.info(log_msg)
            self.execution_log.append(log_msg)
            
            return {
                "success": True,
                "message": log_msg,
                "affected_rows": len(self.df)
            }
            
        except Exception as e:
            error_msg = f"❌ 数学计算失败: {str(e)}"
            logger.error(error_msg)
            return {
                "success": False,
                "error": error_msg,
                "suggestion": "💡 **建议**：请检查列名是否正确，或尝试简化计算步骤"
            }
    
    def trim_whitespace(self, column: str) -> Dict:
        """
        清理列中的首尾空格
        Args:
            column: 列名
        Returns:
            执行结果
        """
        if column not in self.df.columns:
            return self._generate_column_not_found_error(column)
        
        try:
            # 清理空格
            self.df[column] = self.df[column].astype(str).str.strip()
            
            log_msg = f"✅ 已清理 '{column}' 列的首尾空格"
            logger.info(log_msg)
            self.execution_log.append(log_msg)
            
            return {
                "success": True,
                "message": log_msg,
                "affected_rows": len(self.df)
            }
            
        except Exception as e:
            error_msg = f"清理空格失败: {str(e)}"
            logger.error(error_msg)
            return {"success": False, "error": error_msg}
    
    def fill_missing_values(self, column: str, fill_value: str) -> Dict:
        """
        填充空白单元格
        Args:
            column: 列名
            fill_value: 填充值
        Returns:
            执行结果
        """
        if column not in self.df.columns:
            return {
                "success": False,
                "error": f"列 '{column}' 不存在"
            }
        
        try:
            # 统计空值数量
            null_count = self.df[column].isna().sum()
            
            # 填充空值
            fill_value = self._convert_value(fill_value)
            self.df[column].fillna(fill_value, inplace=True)
            
            log_msg = f"✅ 已将 '{column}' 列的 {null_count} 个空白单元格填充为 '{fill_value}'"
            logger.info(log_msg)
            self.execution_log.append(log_msg)
            
            return {
                "success": True,
                "message": log_msg,
                "affected_rows": null_count
            }
            
        except Exception as e:
            error_msg = f"填充空值失败: {str(e)}"
            logger.error(error_msg)
            return {"success": False, "error": error_msg}
    
    def find_and_replace(
        self,
        column: str,
        find_text: str,
        replace_text: str
    ) -> Dict:
        """
        查找并替换文本
        Args:
            column: 列名
            find_text: 要查找的文本
            replace_text: 替换成的文本
        Returns:
            执行结果
        """
        if column not in self.df.columns:
            return {
                "success": False,
                "error": f"列 '{column}' 不存在"
            }
        
        try:
            # 统计替换数量
            find_text = str(find_text)
            replace_text = str(replace_text)
            
            # 统计包含目标文本的行数
            contains_count = self.df[column].astype(str).str.contains(find_text, na=False).sum()
            
            # 执行替换
            self.df[column] = self.df[column].astype(str).str.replace(find_text, replace_text, regex=False)
            
            log_msg = f"✅ 已在 '{column}' 列中将 '{find_text}' 替换为 '{replace_text}' ({contains_count} 处)"
            logger.info(log_msg)
            self.execution_log.append(log_msg)
            
            return {
                "success": True,
                "message": log_msg,
                "affected_rows": contains_count
            }
            
        except Exception as e:
            error_msg = f"查找替换失败: {str(e)}"
            logger.error(error_msg)
            return {"success": False, "error": error_msg}
    
    def concatenate_columns(
        self,
        target_column: str,
        source_columns: List[str],
        delimiter: str = " "
    ) -> Dict:
        """
        合并多列为一列
        Args:
            target_column: 新列名称
            source_columns: 要合并的源列名列表
            delimiter: 连接符（默认为空格）
        Returns:
            执行结果
        """
        # 检查源列是否存在
        missing_cols = [col for col in source_columns if col not in self.df.columns]
        if missing_cols:
            return {
                "success": False,
                "error": f"以下列不存在: {', '.join(missing_cols)}"
            }
        
        try:
            # 健壮性：确保所有源列都是字符串
            self.df[target_column] = self.df[source_columns].astype(str).agg(delimiter.join, axis=1)
            
            log_msg = f"✅ 已将 {len(source_columns)} 列合并为 '{target_column}'，使用 '{delimiter}' 连接"
            logger.info(log_msg)
            self.execution_log.append(log_msg)
            
            return {
                "success": True,
                "message": log_msg,
                "affected_rows": len(self.df)
            }
            
        except Exception as e:
            error_msg = f"列合并失败: {str(e)}"
            logger.error(error_msg)
            return {"success": False, "error": error_msg}
    
    def extract_date_part(
        self,
        source_column: str,
        target_column: str,
        part_to_extract: str
    ) -> Dict:
        """
        从日期列提取组件（年/月/日/星期/季度）
        Args:
            source_column: 源日期列名
            target_column: 目标列名
            part_to_extract: 要提取的部分（year/month/day/weekday/quarter）
        Returns:
            执行结果
        """
        if source_column not in self.df.columns:
            return self._generate_column_not_found_error(source_column)
        
        try:
            # 关键：健壮地转为日期，无法解析的变为 NaT
            date_series = pd.to_datetime(self.df[source_column], errors='coerce')
            
            # 检查是否全部无法解析
            null_count = date_series.isnull().sum()
            if date_series.isnull().all():
                return {
                    "success": False,
                    "error": f"无法将 '{source_column}' 列解析为日期"
                }
            
            # 提取对应部分
            if part_to_extract == 'year':
                self.df[target_column] = date_series.dt.year
                part_desc = "年份"
            elif part_to_extract == 'month':
                self.df[target_column] = date_series.dt.month
                part_desc = "月份"
            elif part_to_extract == 'day':
                self.df[target_column] = date_series.dt.day
                part_desc = "日期"
            elif part_to_extract == 'weekday':
                # 中文星期几更友好
                weekdays_chinese = ['星期一', '星期二', '星期三', '星期四', '星期五', '星期六', '星期日']
                self.df[target_column] = date_series.dt.weekday.apply(
                    lambda x: weekdays_chinese[int(x)] if pd.notna(x) else None
                )
                part_desc = "星期几"
            elif part_to_extract == 'quarter':
                self.df[target_column] = date_series.dt.quarter
                part_desc = "季度"
            else:
                return {
                    "success": False,
                    "error": f"不支持的日期部分: {part_to_extract}"
                }
            
            log_msg = f"✅ 已从 '{source_column}' 提取 {part_desc} 到 '{target_column}'"
            if null_count > 0:
                log_msg += f"\n⚠️  {null_count} 个单元格无法解析为日期"
            
            logger.info(log_msg)
            self.execution_log.append(log_msg)
            
            return {
                "success": True,
                "message": log_msg,
                "affected_rows": len(self.df)
            }
            
        except Exception as e:
            error_msg = f"日期提取失败: {str(e)}"
            logger.error(error_msg)
            return {"success": False, "error": error_msg}
    
    def group_by_aggregate(
        self,
        group_by_column: str,
        agg_column: str,
        agg_func: str
    ) -> Dict:
        """
        分组聚合统计（只统计，不修改表格）
        Args:
            group_by_column: 分组列名
            agg_column: 聚合计算的列名
            agg_func: 聚合函数（mean/sum/count）
        Returns:
            执行结果（包含统计文本）
        """
        # 检查列是否存在
        if group_by_column not in self.df.columns:
            return {
                "success": False,
                "error": f"分组列 '{group_by_column}' 不存在"
            }
        if agg_column not in self.df.columns:
            return {
                "success": False,
                "error": f"聚合列 '{agg_column}' 不存在"
            }
        
        try:
            # 健壮性：对于数值聚合，确保列是数字类型
            if agg_func in ['mean', 'sum']:
                self.df[agg_column] = pd.to_numeric(self.df[agg_column], errors='coerce').fillna(0)
            
            # 执行分组聚合
            grouped_data = self.df.groupby(group_by_column)[agg_column].agg(agg_func)
            
            # 格式化结果
            func_name_map = {
                'mean': '平均值',
                'sum': '总和',
                'count': '计数'
            }
            func_desc = func_name_map.get(agg_func, agg_func)
            
            result_text = f"📊 按 '{group_by_column}' 分组，'{agg_column}' 的 {func_desc}：\n"
            result_text += "=" * 40 + "\n"
            result_text += grouped_data.to_string()
            
            logger.info(f"分组聚合完成: {group_by_column} -> {agg_column} ({agg_func})")
            self.execution_log.append(result_text)
            
            # 重要：标记为分析类工具（不修改表格，不保存）
            return {
                "success": True,
                "message": result_text,
                "is_analysis": True  # 特殊标记
            }
            
        except Exception as e:
            error_msg = f"分组聚合失败: {str(e)}"
            logger.error(error_msg)
            return {"success": False, "error": error_msg}
    
    def split_column(
        self,
        source_column: str,
        delimiter: str,
        new_column_names: Optional[List[str]] = None
    ) -> Dict:
        """
        拆分列（按分隔符将一列拆分为多列）
        Args:
            source_column: 要拆分的源列名
            delimiter: 分隔符
            new_column_names: 可选的新列名列表。如果未提供，自动命名为 源列名_1, 源列名_2 等
        Returns:
            执行结果
        """
        if source_column not in self.df.columns:
            return {
                "success": False,
                "error": f"列 '{source_column}' 不存在"
            }
        
        try:
            # 拆分成一个临时的 DataFrame
            split_data = self.df[source_column].astype(str).str.split(delimiter, expand=True)
            actual_parts = split_data.shape[1]
            
            warnings = []
            
            # 确定新列名
            if new_column_names:
                if len(new_column_names) < actual_parts:
                    # 补全缺失的列名
                    original_len = len(new_column_names)
                    new_column_names.extend([f"{source_column}_{i+1}" for i in range(original_len, actual_parts)])
                    warnings.append(f"⚠️ 实际拆分了 {actual_parts} 列，您提供了 {original_len} 个列名，已自动补全")
                elif len(new_column_names) > actual_parts:
                    # 截断多余的列名
                    original_len = len(new_column_names)
                    new_column_names = new_column_names[:actual_parts]
                    warnings.append(f"⚠️ 实际拆分了 {actual_parts} 列，但您提供了 {original_len} 个列名，已截断")
            else:
                new_column_names = [f"{source_column}_{i+1}" for i in range(actual_parts)]
            
            # 赋给新的列
            split_data.columns = new_column_names
            self.df = pd.concat([self.df, split_data], axis=1)
            
            log_msg = f"✅ 已将 '{source_column}' 列按 '{delimiter}' 拆分为 {len(new_column_names)} 列"
            if warnings:
                log_msg += "\n" + "\n".join(warnings)
            
            logger.info(log_msg)
            self.execution_log.append(log_msg)
            
            return {
                "success": True,
                "message": log_msg,
                "affected_rows": len(self.df),
                "new_columns": new_column_names
            }
            
        except Exception as e:
            error_msg = f"列拆分失败: {str(e)}"
            logger.error(error_msg)
            return {"success": False, "error": error_msg}
    
    def change_case(
        self,
        column_name: str,
        case_type: str
    ) -> Dict:
        """
        更改列的大小写
        Args:
            column_name: 列名
            case_type: 大小写类型（upper/lower/proper）
        Returns:
            执行结果
        """
        if column_name not in self.df.columns:
            return {
                "success": False,
                "error": f"列 '{column_name}' 不存在"
            }
        
        try:
            case_desc_map = {
                'upper': '大写',
                'lower': '小写',
                'proper': '首字母大写'
            }
            
            if case_type == 'upper':
                self.df[column_name] = self.df[column_name].astype(str).str.upper()
            elif case_type == 'lower':
                self.df[column_name] = self.df[column_name].astype(str).str.lower()
            elif case_type == 'proper':
                self.df[column_name] = self.df[column_name].astype(str).str.title()  # Pandas 的 title() 即 Excel 的 PROPER()
            else:
                return {
                    "success": False,
                    "error": f"不支持的大小写类型 '{case_type}'，请使用 upper/lower/proper"
                }
            
            case_desc = case_desc_map.get(case_type, case_type)
            log_msg = f"✅ 已将 '{column_name}' 列转为{case_desc}"
            logger.info(log_msg)
            self.execution_log.append(log_msg)
            
            return {
                "success": True,
                "message": log_msg,
                "affected_rows": len(self.df)
            }
            
        except Exception as e:
            error_msg = f"大小写转换失败: {str(e)}"
            logger.error(error_msg)
            return {"success": False, "error": error_msg}
    
    def drop_duplicates(
        self,
        subset_columns: Optional[List[str]] = None
    ) -> Dict:
        """
        删除重复行
        Args:
            subset_columns: 用于判断重复的列。如果为 None，则判断所有列
        Returns:
            执行结果
        """
        try:
            original_count = len(self.df)
            
            # 如果 subset_columns 是空列表，Pandas 会报错，需转为 None
            subset = subset_columns if subset_columns else None
            
            # 验证列是否存在
            if subset:
                missing_cols = [col for col in subset if col not in self.df.columns]
                if missing_cols:
                    return {
                        "success": False,
                        "error": f"以下列不存在: {', '.join(missing_cols)}"
                    }
            
            self.df.drop_duplicates(subset=subset, keep='first', inplace=True)
            self.df.reset_index(drop=True, inplace=True)  # 重置索引
            
            new_count = len(self.df)
            deleted_count = original_count - new_count
            
            if subset:
                log_msg = f"✅ 已根据 {', '.join(subset)} 列删除 {deleted_count} 行重复数据（保留首次出现）"
            else:
                log_msg = f"✅ 已删除 {deleted_count} 行完全重复的数据（保留首次出现）"
            
            logger.info(log_msg)
            self.execution_log.append(log_msg)
            
            return {
                "success": True,
                "message": log_msg,
                "deleted_rows": deleted_count,
                "remaining_rows": new_count
            }
            
        except Exception as e:
            error_msg = f"删除重复行失败: {str(e)}"
            logger.error(error_msg)
            return {"success": False, "error": error_msg}
    
    def sort_by_column(
        self,
        column_name: str,
        ascending: bool = True
    ) -> Dict:
        """
        按列排序
        Args:
            column_name: 排序依据的列名
            ascending: 是否升序（True=升序，False=降序）
        Returns:
            执行结果
        """
        if column_name not in self.df.columns:
            return {
                "success": False,
                "error": f"列 '{column_name}' 不存在"
            }
        
        try:
            self.df.sort_values(by=column_name, ascending=ascending, inplace=True)
            self.df.reset_index(drop=True, inplace=True)  # 重置索引
            
            order_desc = "升序" if ascending else "降序"
            log_msg = f"✅ 已按 '{column_name}' 列{order_desc}排序"
            
            logger.info(log_msg)
            self.execution_log.append(log_msg)
            
            return {
                "success": True,
                "message": log_msg,
                "affected_rows": len(self.df)
            }
            
        except Exception as e:
            error_msg = f"排序失败: {str(e)}"
            logger.error(error_msg)
            return {"success": False, "error": error_msg}
    
    def save(self, output_path: Optional[str] = None) -> str:
        """
        保存修改后的文件
        Args:
            output_path: 输出路径，如果为None则自动生成
        Returns:
            保存的文件路径
        """
        if output_path is None:
            output_path = str(self.file_path.parent / f"{self.file_path.stem}_modified.xlsx")
        
        self.df.to_excel(output_path, index=False)
        logger.info(f"文件已保存: {output_path}")
        return output_path
    
    def get_execution_log(self) -> List[str]:
        """获取执行日志"""
        return self.execution_log
    
    def reset(self):
        """重置到原始状态"""
        self.df = self.original_df.copy()
        self.execution_log = []
        logger.info("已重置到原始状态")

    def get_all_data(self) -> Dict:
        """
        获取所有数据(用于前端 Handsontable 显示)
        Returns:
            包含表头和数据的字典
        """
        import numpy as np
        import math
        
        def clean_value(val):
            """清理单个值，确保JSON兼容"""
            # 处理None
            if val is None:
                return None
            
            # 处理numpy和Python的数值类型
            if isinstance(val, (np.integer, np.floating)):
                val = val.item()  # 转换为Python原生类型
            
            # 处理float类型的特殊值
            if isinstance(val, float):
                if math.isnan(val) or math.isinf(val):
                    return None
            
            return val
        
        # 逐行处理数据
        cleaned_data = []
        for _, row in self.df.iterrows():
            cleaned_row = [clean_value(val) for val in row]
            cleaned_data.append(cleaned_row)
        
        return {
            "headers": list(self.df.columns),
            "data": cleaned_data
        }

    def update_data(self, data: List[List[Any]]) -> Dict:
        """
        更新所有数据（从前端 Handsontable 保存）
        Args:
            data: 二维数组数据（包含表头）
        Returns:
            执行结果
        """
        try:
            if not data or len(data) < 1:
                return {"success": False, "error": "数据为空"}
            
            # 第一行是表头
            headers = data[0]
            rows = data[1:]
            
            # 更新 DataFrame
            self.df = pd.DataFrame(rows, columns=headers)
            
            # 尝试自动推断数据类型（否则都是字符串）
            self.df = self.df.infer_objects()
            
            log_msg = f"✅ 已手动更新表格数据 ({len(self.df)} 行)"
            logger.info(log_msg)
            self.execution_log.append(log_msg)
            
            return {
                "success": True,
                "message": log_msg,
                "total_rows": len(self.df)
            }
        except Exception as e:
            error_msg = f"数据更新失败: {str(e)}"
            logger.error(error_msg)
            return {"success": False, "error": error_msg}

    
    def execute_tool(self, tool_name: str, parameters: Dict) -> Dict:
        """
        统一的工具执行接口（供 WebSocket 使用）
        Args:
            tool_name: 工具名称
            parameters: 工具参数
        Returns:
            执行结果
        """
        # 转换参数类型
        if tool_name == "get_summary" and 'top_n' in parameters:
            if isinstance(parameters['top_n'], str):
                parameters['top_n'] = int(parameters['top_n'])
        
        if tool_name == "perform_math" and 'round_to' in parameters:
            if parameters['round_to']:
                parameters['round_to'] = int(parameters['round_to'])
        
        if tool_name == "sort_by_column" and 'ascending' in parameters:
            if isinstance(parameters['ascending'], str):
                parameters['ascending'] = parameters['ascending'].lower() in ['true', '1', 'yes']
        
        # 调用对应的方法
        if tool_name == "set_column_value":
            return self.set_column_value(**parameters)
        elif tool_name == "set_by_condition":
            return self.set_by_condition(**parameters)
        elif tool_name == "copy_column":
            return self.copy_column(**parameters)
        elif tool_name == "set_by_mapping":
            return self.set_by_mapping(**parameters)
        elif tool_name == "get_summary":
            return self.get_summary(**parameters)
        elif tool_name == "perform_math":
            return self.perform_math(**parameters)
        elif tool_name == "trim_whitespace":
            return self.trim_whitespace(**parameters)
        elif tool_name == "fill_missing_values":
            return self.fill_missing_values(**parameters)
        elif tool_name == "find_and_replace":
            return self.find_and_replace(**parameters)
        elif tool_name == "concatenate_columns":
            return self.concatenate_columns(**parameters)
        elif tool_name == "extract_date_part":
            return self.extract_date_part(**parameters)
        elif tool_name == "group_by_aggregate":
            return self.group_by_aggregate(**parameters)
        elif tool_name == "split_column":
            return self.split_column(**parameters)
        elif tool_name == "change_case":
            return self.change_case(**parameters)
        elif tool_name == "drop_duplicates":
            return self.drop_duplicates(**parameters)
        elif tool_name == "sort_by_column":
            return self.sort_by_column(**parameters)
        elif tool_name == "add_column":
            return self.add_column(**parameters)
        elif tool_name == "delete_column":
            return self.delete_column(**parameters)
        else:
            return {
                "success": False,
                "error": f"未知工具: {tool_name}"
            }


# 工具函数映射 - 供AI调用
TOOL_FUNCTIONS = {
    "set_column_value": ExcelEngine.set_column_value,
    "set_by_condition": ExcelEngine.set_by_condition,
    "copy_column": ExcelEngine.copy_column,
    "set_by_mapping": ExcelEngine.set_by_mapping,
    "get_summary": ExcelEngine.get_summary,
    "perform_math": ExcelEngine.perform_math,
    "trim_whitespace": ExcelEngine.trim_whitespace,
    "fill_missing_values": ExcelEngine.fill_missing_values,
    "find_and_replace": ExcelEngine.find_and_replace,
    "concatenate_columns": ExcelEngine.concatenate_columns,  # v0.0.4-alpha
    "extract_date_part": ExcelEngine.extract_date_part,      # v0.0.4-alpha
    "group_by_aggregate": ExcelEngine.group_by_aggregate,    # v0.0.4-alpha
    "split_column": ExcelEngine.split_column,                # v0.0.4-beta
    "change_case": ExcelEngine.change_case,                  # v0.0.4-beta
    "drop_duplicates": ExcelEngine.drop_duplicates,          # v0.0.4-beta
    "sort_by_column": ExcelEngine.sort_by_column,            # v0.0.4-beta
    "add_column": ExcelEngine.add_column,                    # v0.0.6
    "delete_column": ExcelEngine.delete_column,                # v0.0.6
}

