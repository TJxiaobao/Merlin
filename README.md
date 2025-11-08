# 🧙 Merlin - AI Excel 助手

**用自然语言操作 Excel，低成本、高安全、真智能**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)

> 让非技术人员通过自然语言"指挥" AI，自动完成 Excel 数据处理

---

## 💡 为什么选择 Merlin？

### 🎯 核心优势：高效、低成本、更安全

相比于"AI 生成代码并在虚拟机中执行"的"**代码解释器**"模式，Merlin 采用了更轻量、更安全的"**AI 指令翻译**"模式。

#### 1. **更低 Token 消耗** 💰

**代码解释器方案**：
```python
# AI 必须输出完整的 Python 代码（100+ Token）
df = pd.read_excel('file.xlsx')
df['总价'] = df['数量'] * df['单价'] * df['税率']
df.to_excel('output.xlsx', index=False)
```

**Merlin 方案**：
```json
// AI 只需输出轻量的 JSON 指令（~20 Token）
{
  "function": "perform_math",
  "arguments": {"operation": "multiply", ...}
}
```

**结果**：Merlin 的单次操作 Token 消耗降低 **80-90%**，响应更快、成本更低。

#### 2. **智能路由架构** 🧠

Merlin 不会一次性把所有（20+）工具的 Schema 发给 AI：

- **快速路径（Fast Path）**：简单指令通过关键词匹配，只发送相关工具（3-4 个），减少 **60-70% 输入 Token**
- **总指挥路径（Coordinator Path）**：复杂指令先拆分，再逐个翻译，确保高精度执行

#### 3. **绝对安全** 🔒

| 方案 | AI 能做什么？ | 风险 |
|------|--------------|------|
| **代码解释器** | 执行任意 Python 代码 | ⚠️ 需要沙箱隔离，防止 `os.remove('/')` |
| **Merlin** | 只能调用预定义的安全函数 | ✅ 白名单机制，从根本上杜绝代码执行风险 |

AI 永远无法执行它"想"执行的代码，它只能"请求"调用你在 `excel_engine.py` 中预先审查过的函数。

#### 4. **代码与提示词分离** 📦

- 所有 AI 提示词、工具 Schema 外部化到 `YAML` 文件
- 优化 AI 性能**只需修改配置文件**，无需重新部署代码
- 便于 A/B 测试、多语言支持、版本管理

#### 5. **智能混合架构** ⚡

```
用户指令
    ↓
智能判断：简单 or 复杂？
    ├─ 简单 → 快速路径（关键词路由 → 专家翻译）💨 低成本
    └─ 复杂 → 总指挥路径（任务拆分 → 循环翻译 → 串行执行）🎯 高精度
```

**完美平衡**：用"快速路径"处理 80% 的简单任务（低成本），用"总指挥"处理 20% 的复杂任务（高质量）。

---

## ✨ 核心特性

- 🎯 **零学习成本** - 用说话代替复杂的 Excel 公式
- 💰 **成本优化** - Token 消耗降低 60-90%，响应速度提升
- 🔒 **绝对安全** - 白名单机制，AI 无法执行任意代码
- 🧠 **真正智能** - 自动拆分复合指令，智能路由，主动功能发现
- 🤝 **友好体验** - 智能建议、模糊匹配列名、结构化错误提示
- 📦 **易于维护** - 提示词、工具Schema、分组配置全部外部化到YAML
- 🎨 **UI 2.0** - 三栏式专业布局，可复制列名，内嵌下载按钮
- 🌊 **流式响应** - WebSocket实时推送，逐步显示进度，智能限流 ⭐️ 新

---

## 🚀 快速开始

### 1. 安装

```bash
git clone https://github.com/your-username/Merlin.git
cd Merlin

# 安装 Python 依赖
pip install -r requirements.txt

# 安装前端依赖
cd frontend && npm install && cd ..
```

### 2. 配置 API

```bash
python setup.py  # 配置向导
```

或手动创建 `.env`：
```env
OPENAI_API_KEY=你的API密钥
OPENAI_API_BASE=https://api.moonshot.cn/v1
```

> 💡 支持 Kimi、OpenAI、DeepSeek 等所有兼容 OpenAI API 的服务

### 3. 启动

```bash
./start.sh  # 一键启动，自动打开浏览器
```

访问 http://localhost:5173 开始使用！

---

## 💡 使用示例

### 基础操作
```
"把所有税率设为 0.13"
"把设备类型是 Gateway 的价格设为 100"
```

### 数学计算
```
"新建总价列等于数量乘以单价"
"计算利润等于售价减去成本"
```

### 复合指令（自动拆分）
```
"把所有税率设为 0.13，然后新建总价列等于数量乘单价再乘税率"
→ Merlin 自动拆分为 2 个子任务并串行执行
```

### 数据清洗
```
"清理备注列的空格"
"把客户区域列里的北京都替换成华北区"
```

### 批量映射
```
"把 196001 的价格设为 100，196002 的设为 200"
→ 一次 AI 调用完成，不受 Rate Limit 影响
```

### 统计分析
```
"统计设备类型的分布"
"按客户区域分组，计算平均销售额"
```

> 💡 **发现更多功能**：点击界面上的 ✨ 魔法棒按钮，或输入 `help`

---

## 🏗️ 技术架构

### 核心设计理念
![img.png](img.png)


### 核心模块

| 模块 | 职责 | 技术亮点 |
|------|------|----------|
| **AI 翻译器** | 理解自然语言 → 结构化指令 | 三阶段架构：总指挥 + 路由器 + 专家 |
| **Excel 引擎** | 执行安全的 Pandas 操作 | 白名单机制，预定义函数，无代码执行风险 |
| **提示词管理器** | 加载和管理 AI 配置 | YAML 外部化，易于优化和版本管理 |
| **智能路由** | 根据指令复杂度选择路径 | 快速路径（关键词）+ 总指挥路径（拆分） |

### 为什么这样设计？

1. **AI 负责思考** - 理解自然语言，做出决策
2. **代码负责执行** - 安全可控，经过测试
3. **完全解耦** - AI 可替换，引擎可独立运行
4. **成本优化** - 智能路由，按需加载，避免浪费

---

## 🎬 支持的操作

### 数据操作
- ✅ 整列赋值、条件筛选、批量映射、列复制

### 数学计算
- ✅ 加减乘除、四舍五入、多列运算、自动处理非数字值

### 数据清洗
- ✅ 空格处理、空值填充、查找替换

### 统计分析
- ✅ 值分布、分组聚合、数据总结

### 文本处理
- ✅ 列合并、列拆分、大小写转换、日期提取

### 表格结构
- ✅ 去重、排序、删除列、重命名列

---

## 📂 项目结构

```
Merlin/
├── app/                        # 后端核心
│   ├── main.py                # FastAPI HTTP接口
│   ├── asgi.py                # ASGI应用入口（WebSocket集成）
│   ├── websocket.py           # WebSocket流式响应处理
│   ├── ai_translator.py       # AI 翻译器（三阶段架构）
│   ├── excel_engine.py        # Pandas 安全引擎
│   ├── prompts/               # AI 配置（完全外部化）⭐️
│   │   ├── merlin_v1.yml     # 系统提示词、错误消息
│   │   ├── tools_schema.yml  # 工具Schema + 分组配置
│   │   └── manager.py        # 配置加载和管理
│   └── config.py              # 应用配置
├── frontend/                   # 前端（Vite + WebSocket）
│   ├── index.html             # 主页面
│   ├── main.js                # WebSocket客户端逻辑
│   ├── streaming.js           # 流式消息显示逻辑 ⭐️
│   ├── style.css              # UI 2.0样式
│   └── vite.config.js         # Vite配置
├── start.sh                   # 一键启动（后端+前端）
├── stop.sh                    # 停止服务
└── requirements.txt           # Python 依赖
```

---

## 🧪 测试

```bash
# 快速测试
python test.py quick

# 引擎测试（不调用 AI）
python test.py engine
```

---

## 🛣️ 路线图

### ✅ v0.1.0-alpha（当前版本）
- 三阶段 AI 架构（总指挥 + 路由器 + 专家）
- 复合指令自动拆分和串行执行
- 智能建议 + 模糊匹配列名
- **配置完全外部化** 🎯
  - 系统提示词 → `merlin_v1.yml`
  - 工具Schema → `tools_schema.yml`
  - 工具分组配置 → `tools_schema.yml` (tool_groups)
  - 优化AI性能只需修改YAML，无需改代码
- **WebSocket 流式响应** 🌊 ⭐️
  - 实时显示每个子任务的翻译和执行进度
  - 智能限流：自动等待21秒避免API限流（RPM=3）
  - 倒计时显示，用户清楚知道等待原因
  - 中间结果保存，部分失败不丢数据
- **UI 2.0 升级** ⭐️
  - 三栏式专业布局（顶部栏 + 左侧栏 + 主聊天区）
  - 可复制的列名列表（点击复制，自动插入）
  - 流式消息显示（在同一气泡中逐行更新）
  - 智能空状态提示（动态建议）
  - 内嵌下载按钮（在成功消息中）

### 🚧 未来计划
- **v0.1.0-beta** - 操作历史与撤销、批量文件处理
- **v0.2.0** - 多表格支持、规则模板、智能澄清对话
- **v1.0.0** - 公式引擎、完整文档、Docker部署

---

## 📊 性能对比

| 维度 | 代码解释器方案 | Merlin 方案 | 优势 |
|------|--------------|------------|------|
| **输出 Token** | ~100-200 (完整代码) | ~20-30 (JSON) | **降低 80-90%** |
| **输入 Token** | 所有工具 Schema | 智能路由，按需加载 | **降低 60-70%** |
| **安全性** | 需要沙箱隔离 | 白名单机制 | **从根本上安全** |
| **响应速度** | 慢（生成+执行代码） | 快（翻译+直接调用） | **提升 2-3 倍** |
| **可维护性** | 提示词嵌入代码 | YAML 外部化 | **易于优化** |

---

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

```bash
git checkout -b feature/AmazingFeature
git commit -m 'Add some AmazingFeature'
git push origin feature/AmazingFeature
```

---

## 📄 许可证

MIT License - 详见 [LICENSE](LICENSE) 文件

---

## 📮 联系方式

- **Issues**: [GitHub Issues](https://github.com/your-username/Merlin/issues)
- **Email**: gaoxingcun@apache.org

---

<p align="center">
  <strong>用 AI 的力量，让 Excel 操作变得简单、安全、高效！</strong><br>
  <br>
  如果觉得有用，请给个 ⭐️ Star 支持一下！
</p>
