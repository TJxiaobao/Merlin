#!/usr/bin/env python3
"""
Merlin 统一测试脚本
支持多种测试模式：
  - quick: 快速测试（1次AI调用）
  - full: 完整测试（多个场景）
  - mapping: 批量映射测试
  - engine: 仅测试引擎（不调用AI）
"""
import sys
import time
import json
from pathlib import Path
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 确保能导入app模块
sys.path.insert(0, str(Path(__file__).parent))

from app.excel_engine import ExcelEngine
from app.ai_translator import AITranslator
import os


def create_test_data():
    """创建测试数据"""
    import pandas as pd
    
    data = {
        "设备类型": ["Gateway", "Sensor", "Gateway", "Sensor", "Gateway", "Controller", "Sensor", "Gateway"],
        "设备编码": ["196001", "196002", "197001", "198001", "196003", "199001", "196004", "197002"],
        "设备名称": ["网关A", "传感器B", "网关C", "传感器D", "网关E", "控制器F", "传感器G", "网关H"],
        "参考报价": [100, 50, 100, 50, 100, 200, 50, 100],
        "未税单价": [None, None, None, None, None, None, None, None],
        "税率": [None, None, None, None, None, None, None, None],
        "数量": [10, 20, 15, 25, 12, 5, 30, 8],
        "备注": ["", "", "", "", "", "", "", ""]
    }
    
    df = pd.DataFrame(data)
    output_dir = Path("test_data")
    output_dir.mkdir(exist_ok=True)
    output_path = output_dir / "test_equipment.xlsx"
    df.to_excel(output_path, index=False)
    
    print(f"✅ 测试文件已创建: {output_path}")
    return output_path


def test_engine_only():
    """测试引擎（不使用AI）"""
    print("=" * 60)
    print("模式：引擎测试（不调用AI）")
    print("=" * 60)
    
    test_file = Path("test_data/test_equipment.xlsx")
    if not test_file.exists():
        print("\n📋 创建测试数据...")
        test_file = create_test_data()
    
    print(f"\n📂 加载文件: {test_file}")
    engine = ExcelEngine(str(test_file))
    print(f"   行数: {len(engine.df)}, 列数: {len(engine.df.columns)}")
    
    print("\n" + "=" * 60)
    print("测试1: 整列赋值")
    print("=" * 60)
    result = engine.set_column_value("税率", 0.13)
    print(f"{result['message']}\n")
    
    print("=" * 60)
    print("测试2: 条件赋值")
    print("=" * 60)
    result = engine.set_by_condition(
        condition_column="设备类型",
        condition_value="Gateway",
        target_column="未税单价",
        target_value=100
    )
    print(f"{result['message']}\n")
    
    print("=" * 60)
    print("测试3: 批量映射")
    print("=" * 60)
    result = engine.set_by_mapping(
        condition_column="设备编码",
        target_column="未税单价",
        mapping={
            "196002": "50",
            "198001": "50",
            "196004": "50"
        }
    )
    print(f"{result['message']}\n")
    
    print("=" * 60)
    print("测试4: 数学计算（v0.0.2新增）")
    print("=" * 60)
    result = engine.perform_math(
        target_column="总价",
        source_column_1="未税单价",
        operator="multiply",
        source_column_2_or_number="数量"
    )
    print(f"{result['message']}\n")
    
    print("=" * 60)
    print("测试5: 数学计算（列×常数）")
    print("=" * 60)
    result = engine.perform_math(
        target_column="含税单价",
        source_column_1="未税单价",
        operator="multiply",
        source_column_2_or_number="1.13",
        round_to=2
    )
    print(f"{result['message']}\n")
    
    print("=" * 60)
    print("测试6: 数据清洗 - 查找替换")
    print("=" * 60)
    result = engine.find_and_replace(
        column="设备类型",
        find_text="Gateway",
        replace_text="网关设备"
    )
    print(f"{result['message']}\n")
    
    # 保存
    output_path = engine.save("test_data/engine_test_result.xlsx")
    print(f"💾 已保存: {output_path}\n")
    print(engine.df.to_string())


def test_quick():
    """快速测试（1次AI调用）"""
    print("=" * 60)
    print("模式：快速测试（1次AI调用）")
    print("=" * 60)
    
    test_file = Path("test_data/test_equipment.xlsx")
    if not test_file.exists():
        test_file = create_test_data()
    
    print(f"\n📂 加载文件: {test_file}")
    engine = ExcelEngine(str(test_file))
    
    if not os.getenv("OPENAI_API_KEY"):
        print("\n⚠️  未配置API密钥，切换到引擎测试模式")
        return test_engine_only()
    
    try:
        translator = AITranslator()
        print(f"   AI模型: {translator.model}")
        print(f"   API: {translator.base_url}")
        
        command = "把所有税率设为0.13"
        print(f"\n🤖 指令: {command}")
        print("-" * 60)
        
        translation = translator.translate(command, engine.get_headers())
        
        if not translation["success"]:
            print(f"❌ AI翻译失败: {translation.get('error')}")
            return
        
        for tool_call in translation["tool_calls"]:
            tool_name = tool_call["tool_name"]
            parameters = tool_call["parameters"]
            print(f"📝 AI翻译: {tool_name}({json.dumps(parameters, ensure_ascii=False)})")
            
            if tool_name == "set_column_value":
                result = engine.set_column_value(**parameters)
            elif tool_name == "set_by_condition":
                result = engine.set_by_condition(**parameters)
            elif tool_name == "set_by_mapping":
                result = engine.set_by_mapping(**parameters)
            elif tool_name == "perform_math":
                if 'round_to' in parameters and parameters['round_to']:
                    parameters['round_to'] = int(parameters['round_to'])
                result = engine.perform_math(**parameters)
            elif tool_name == "trim_whitespace":
                result = engine.trim_whitespace(**parameters)
            elif tool_name == "fill_missing_values":
                result = engine.fill_missing_values(**parameters)
            elif tool_name == "find_and_replace":
                result = engine.find_and_replace(**parameters)
            elif tool_name == "get_summary":
                if 'top_n' in parameters and isinstance(parameters['top_n'], str):
                    parameters['top_n'] = int(parameters['top_n'])
                result = engine.get_summary(**parameters)
            else:
                print(f"❌ 未知工具: {tool_name}")
                continue
            
            if result["success"]:
                print(f"✅ 执行成功!\n{result['message']}")
            else:
                print(f"❌ 失败: {result.get('error')}")
        
        output_path = engine.save("test_data/quick_test_result.xlsx")
        print(f"\n💾 已保存: {output_path}")
        
    except Exception as e:
        print(f"\n❌ 测试失败: {str(e)}")
        import traceback
        traceback.print_exc()


def test_mapping():
    """测试批量映射"""
    print("=" * 60)
    print("模式：批量映射测试")
    print("=" * 60)
    
    test_file = Path("test_data/test_equipment.xlsx")
    if not test_file.exists():
        test_file = create_test_data()
    
    print(f"\n📂 加载文件: {test_file}")
    engine = ExcelEngine(str(test_file))
    
    print("\n测试1: 直接调用（不使用AI）")
    print("-" * 60)
    result = engine.set_by_mapping(
        condition_column="设备编码",
        target_column="未税单价",
        mapping={
            "196001": "100",
            "196002": "200",
            "196003": "300"
        }
    )
    print(f"{result['message']}\n")
    
    if not os.getenv("OPENAI_API_KEY"):
        print("⚠️  未配置API密钥，跳过AI测试")
    else:
        try:
            translator = AITranslator()
            command = "把Gateway的税率设为0.13，Sensor的设为0.06"
            
            print(f"测试2: AI翻译")
            print("-" * 60)
            print(f"🤖 指令: {command}")
            
            translation = translator.translate(command, engine.get_headers())
            
            if translation["success"]:
                for tool_call in translation["tool_calls"]:
                    print(f"📝 翻译: {tool_call['tool_name']}({json.dumps(tool_call['parameters'], ensure_ascii=False)})")
                    
                    if tool_call["tool_name"] == "set_by_mapping":
                        result = engine.set_by_mapping(**tool_call["parameters"])
                        print(f"✅ {result['message']}")
            else:
                print(f"❌ {translation.get('error')}")
        
        except Exception as e:
            print(f"❌ AI测试失败: {e}")
    
    output_path = engine.save("test_data/mapping_test_result.xlsx")
    print(f"\n💾 已保存: {output_path}")


def test_full():
    """完整测试（多个场景，较慢）"""
    print("=" * 60)
    print("模式：完整测试（多个场景）")
    print("=" * 60)
    print("⚠️  此模式会触发多次AI调用，可能需要等待")
    print()
    
    test_file = Path("test_data/test_equipment.xlsx")
    if not test_file.exists():
        test_file = create_test_data()
    
    engine = ExcelEngine(str(test_file))
    
    if not os.getenv("OPENAI_API_KEY"):
        print("⚠️  未配置API密钥，切换到引擎测试模式")
        return test_engine_only()
    
    test_commands = [
        "把所有税率设为0.13",
        "把Gateway的未税单价设为100，Sensor的设为50",
        "让总价等于数量乘以未税单价",  # v0.0.2 新功能
    ]
    
    try:
        translator = AITranslator()
        
        for i, command in enumerate(test_commands, 1):
            print(f"\n🤖 测试{i}: {command}")
            print("-" * 60)
            
            if i > 1:
                print("   ⏳ 等待21秒避免Rate Limit...")
                time.sleep(21)
            
            translation = translator.translate(command, engine.get_headers())
            
            if not translation["success"]:
                print(f"   ❌ {translation.get('error')}")
                continue
            
            for tool_call in translation["tool_calls"]:
                tool_name = tool_call["tool_name"]
                parameters = tool_call["parameters"]
                print(f"   📝 {tool_name}({json.dumps(parameters, ensure_ascii=False)})")
                
                if tool_name == "set_column_value":
                    result = engine.set_column_value(**parameters)
                elif tool_name == "set_by_condition":
                    result = engine.set_by_condition(**parameters)
                elif tool_name == "set_by_mapping":
                    result = engine.set_by_mapping(**parameters)
                elif tool_name == "perform_math":
                    if 'round_to' in parameters and parameters['round_to']:
                        parameters['round_to'] = int(parameters['round_to'])
                    result = engine.perform_math(**parameters)
                elif tool_name == "trim_whitespace":
                    result = engine.trim_whitespace(**parameters)
                elif tool_name == "fill_missing_values":
                    result = engine.fill_missing_values(**parameters)
                elif tool_name == "find_and_replace":
                    result = engine.find_and_replace(**parameters)
                elif tool_name == "get_summary":
                    if 'top_n' in parameters and isinstance(parameters['top_n'], str):
                        parameters['top_n'] = int(parameters['top_n'])
                    result = engine.get_summary(**parameters)
                else:
                    continue
                
                if result["success"]:
                    print(f"   ✅ {result['message']}")
                else:
                    print(f"   ❌ {result.get('error')}")
        
        output_path = engine.save("test_data/full_test_result.xlsx")
        print(f"\n💾 已保存: {output_path}")
        
    except Exception as e:
        print(f"\n❌ 测试失败: {str(e)}")


def main():
    """主函数"""
    import sys
    
    # 解析命令行参数
    mode = sys.argv[1] if len(sys.argv) > 1 else "quick"
    
    print("\n" + "🧙 Merlin 测试工具".center(60))
    print()
    
    if mode == "engine":
        test_engine_only()
    elif mode == "quick":
        test_quick()
    elif mode == "mapping":
        test_mapping()
    elif mode == "full":
        test_full()
    else:
        print("使用方法:")
        print("  python test.py [mode]")
        print()
        print("模式:")
        print("  quick    - 快速测试（1次AI调用，默认）")
        print("  mapping  - 批量映射测试")
        print("  engine   - 引擎测试（不调用AI）")
        print("  full     - 完整测试（较慢，多次AI调用）")
        print()
        print("示例:")
        print("  python test.py quick")
        print("  python test.py engine")
        return
    
    print("\n" + "=" * 60)
    print("✅ 测试完成!")
    print("=" * 60)


if __name__ == "__main__":
    main()

