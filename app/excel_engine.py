"""
Excel操作引擎 - 使用Pandas执行实际的表格操作
这个模块是"双手"，只负责执行，不负责理解
"""
import pandas as pd
from pathlib import Path
from typing import Dict, List, Any, Optional
import logging

from .utils import convert_value
from .config import config

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
            error_msg = f"列'{column}'不存在。可用列: {list(self.df.columns)}"
            logger.error(error_msg)
            return {"success": False, "error": error_msg}
        
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
                log_msg = f"⚠️  没有找到符合条件的行 (条件: {condition_desc})"
                logger.warning(log_msg)
                self.execution_log.append(log_msg)
                return {
                    "success": True,
                    "message": log_msg,
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
            return {
                "success": False,
                "error": f"列 '{source_column_1}' 不存在"
            }
        
        try:
            # 准备第一个操作数（健壮性处理：将非数字转为0）
            col_1_data = pd.to_numeric(self.df[source_column_1], errors='coerce').fillna(0)
            non_numeric_count_1 = self.df[source_column_1].isna().sum()
            
            # 准备第二个操作数
            is_column = source_column_2_or_number in self.df.columns
            
            if is_column:
                # 如果是列名
                col_2_data = pd.to_numeric(self.df[source_column_2_or_number], errors='coerce').fillna(0)
                non_numeric_count_2 = self.df[source_column_2_or_number].isna().sum()
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
                        "error": f"'{source_column_2_or_number}' 既不是有效的列名也不是有效的数字"
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
            error_msg = f"数学计算失败: {str(e)}"
            logger.error(error_msg)
            return {"success": False, "error": error_msg}
    
    def trim_whitespace(self, column: str) -> Dict:
        """
        清理列中的首尾空格
        Args:
            column: 列名
        Returns:
            执行结果
        """
        if column not in self.df.columns:
            return {
                "success": False,
                "error": f"列 '{column}' 不存在"
            }
        
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
}

