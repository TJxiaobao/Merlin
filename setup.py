#!/usr/bin/env python3
"""
Merlin 配置向导 - 快速配置 API 密钥
"""
from pathlib import Path


def setup():
    """配置向导"""
    print("=" * 60)
    print("  Merlin 配置向导")
    print("=" * 60)
    print()
    
    env_file = Path(".env")
    
    # 检查现有配置
    if env_file.exists():
        print("⚠️  检测到已有配置:")
        print()
        with open(env_file, 'r', encoding='utf-8') as f:
            print(f.read())
        print()
        if input("是否覆盖？(y/N): ").strip().lower() != 'y':
            print("❌ 已取消")
            return
    
    # 选择服务
    print("请选择 AI 服务:")
    print("  1. Kimi（推荐，国内快）")
    print("  2. OpenAI")
    print("  3. 其他")
    
    choice = input("\n选择 [1]: ").strip() or "1"
    
    if choice == "1":
        api_base = "https://api.moonshot.cn/v1"
        print("\n💡 获取 Kimi API Key: https://platform.moonshot.cn/")
    elif choice == "2":
        api_base = "https://api.openai.com/v1"
        print("\n💡 获取 OpenAI API Key: https://platform.openai.com/")
    else:
        api_base = input("\nAPI Base URL: ").strip()
    
    api_key = input("API Key: ").strip()
    
    if not api_key:
        print("❌ API Key 不能为空")
        return
    
    # 保存配置
    with open(env_file, 'w', encoding='utf-8') as f:
        f.write(f"# Merlin AI 配置\n")
        f.write(f"OPENAI_API_KEY={api_key}\n")
        f.write(f"OPENAI_API_BASE={api_base}\n")
    
    print()
    print("✅ 配置完成！")
    print()
    print("现在可以运行测试:")
    print("  python test.py")
    print()


if __name__ == "__main__":
    try:
        setup()
    except KeyboardInterrupt:
        print("\n\n❌ 已取消")

