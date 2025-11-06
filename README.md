# 🧙 Merlin - AI Excel 助手

**让非技术人员通过自然语言"指挥"AI，自动完成 Excel 数据处理**

> 版本：v0.0.2 (The Toolbox) | 作者：TJxiaobao | 许可证：MIT

---

## 📖 项目简介

Merlin 是一个"小而美"的 AI 工具，能理解自然语言指令，自动完成 Excel 中繁琐的数据填充、计算、清洗和修改任务。

> ⚠️ **当前状态**：这是 v0.0.2 版本，新增数学计算和数据清洗功能，建议在测试环境使用。正式版本将在后续发布。

### 核心价值
- 🎯 **零学习成本**：用说话代替复杂的 Excel 公式
- ⚡ **效率提升 100 倍**：将数小时的重复劳动压缩到几分钟
- 🔒 **安全可控**：原始文件永不修改，所有操作可追溯

### 典型场景
```
数据填充：  "把所有税率设为 0.13"
条件筛选：  "把设备类型是 Gateway 的未税单价设为 100"
批量映射：  "把 196001 的价格设为100，196002 的设为200"
数学计算：  "让总价等于数量乘以单价" ⭐️ v0.0.2 新增
数据清洗：  "把客户区域列里的北京都替换成华北区" ⭐️ v0.0.2 新增
统计分析：  "统计设备类型的分布"
```

---

## ⚡ 快速开始

### 1. 安装依赖
```bash
git clone https://github.com/your-username/Merlin.git
cd Merlin
pip install -r requirements.txt
```

### 2. 配置 API（支持 Kimi/OpenAI/DeepSeek）

**使用配置向导（推荐）**:
```bash
python setup.py
```

或手动创建 `.env` 文件：
```env
OPENAI_API_KEY=你的API密钥
OPENAI_API_BASE=https://api.moonshot.cn/v1
```

> 💡 推荐使用 Kimi（国内快速）：https://platform.moonshot.cn/

### 3. 启动 Web 界面 🚀

```bash
# 一键启动（启动后端+打开前端）
./start_frontend.sh

# 或手动启动
python -m uvicorn app.main:app --reload
# 然后打开浏览器访问: frontend/index.html
```

**Web 界面特点**：
- 💬 **超大聊天区域** - 左右分栏设计，舒适的对话体验
- 📱 **侧边栏** - 固定显示文件信息和列名
- 📁 **拖拽上传** - 支持点击或拖拽上传 Excel
- 📥 **一键下载** - 修改后的文件轻松下载
- 🎨 **现代美观** - 渐变色、动画效果

---

## 🎬 支持的操作

### 1. 整列赋值
```
"把所有税率设为 0.13"
"让所有备注都是'已处理'"
```

### 2. 条件筛选
```
"把设备类型是 Gateway 的价格设为 100"
"把状态是'待处理'的备注改为'进行中'"
```

### 3. 前缀/包含匹配
```
"把设备编码是 196 开头的价格改为 1"
"把地址包含'北京'的运费设为 20"
```

### 4. 列复制
```
"把参考报价复制到未税单价"
```

### 5. 批量映射 ⭐️
```
"把设备编码为196001的价格设为100，196002的设为200，196003的设为300"
"把Gateway的税率设为0.13，Sensor的设为0.06"
```
**优势**: 一次 AI 调用完成多个映射，不受 Rate Limit 影响！

### 6. 统计分析
```
"统计设备类型的分布"
"帮我看看设备编码有哪些"
"总结一下客户来源情况"
```

**返回示例**:
```
📊 列 '设备类型' 统计结果:
   总行数: 228
   有效数据: 228
   
   数据分布（前10项）:
     • 'Gateway': 95 条 (41.7%)
     • 'Sensor': 78 条 (34.2%)
     • 'Controller': 55 条 (24.1%)
```

### 7. 数学计算 ⭐️ v0.0.2 新增
```
"让总价等于数量乘以单价"
"计算利润等于售价减去成本"
"把未税单价乘以1.13存入含税单价"
"让利润率等于利润除以售价，保留4位小数"
```

**支持运算**：
- ➕ 加法 (add)
- ➖ 减法 (subtract)
- ✖️ 乘法 (multiply)
- ➗ 除法 (divide)

**智能特性**：
- ✅ 自动识别列名或数字
- ✅ 自动处理非数字值（视为0）
- ✅ 自动处理除零错误
- ✅ 支持四舍五入

### 8. 数据清洗 ⭐️ v0.0.2 新增

#### 8.1 清理空格
```
"清理设备名称列的空格"
"去掉备注列前后的空格"
```

#### 8.2 填充空值
```
"把备注列的空白单元格填充为N/A"
"把空的状态都改成待处理"
```

#### 8.3 查找替换
```
"把客户区域列里的北京都替换成华北区"
"把所有的'旧名称'改成'新名称'"
```

---

## 🏗️ 项目架构

```
用户自然语言
    ↓
AI 翻译器（Kimi/OpenAI）
    ↓
结构化 JSON 指令
    ↓
Pandas 引擎执行
    ↓
修改后的 Excel
```

### 核心设计理念

- 🧠 **AI 负责思考**：理解自然语言，翻译为结构化指令
- 🤲 **代码负责执行**：安全可控，经过测试
- 🔄 **完全解耦**：AI 可替换，引擎可独立运行

---

## 📂 项目结构

```
Merlin/
├── app/                    # 后端核心代码
│   ├── main.py            # FastAPI 接口
│   ├── ai_translator.py   # AI 翻译模块
│   ├── excel_engine.py    # Pandas 操作引擎
│   ├── config.py          # 配置管理
│   └── utils.py           # 工具函数
├── frontend/               # 前端界面
│   ├── index.html         # Web 界面
│   └── app.js             # 前端逻辑
├── setup.py               # 配置向导
├── start_frontend.sh      # 一键启动脚本
├── product.md             # 产品设计文档
└── requirements.txt       # 依赖
```

---

## 🔧 开发与测试

### API 文档
```bash
# 启动服务后访问
http://localhost:8000/docs
```

### 测试工具
```bash
# 快速测试（推荐）
python test.py quick

# 批量映射测试
python test.py mapping

# 引擎测试（不调用AI）
python test.py engine
```

---

## 🎯 产品路线图

### ✅ v0.0.2（当前版本 - The Toolbox）
- [x] 核心功能验证
- [x] Web 前端界面（左右分栏）
- [x] 基础数据操作（赋值、条件、复制）
- [x] 批量映射功能
- [x] 统计分析功能
- [x] **数学计算工具** ⭐️ 新增
- [x] **数据清洗工具**（空格清理、空值填充、查找替换）⭐️ 新增

### ✅ v0.0.1（已发布 - Demo）
- [x] 概念验证
- [x] 基础 UI 原型
- [x] AI 翻译引擎

### 🚧 v0.1.0（计划中 - 稳定化）
- [ ] 代码优化和重构
- [ ] 完善错误处理
- [ ] 添加单元测试
- [ ] 性能优化
- [ ] 操作历史记录

### 🔮 v1.0.0（正式版本）
- [ ] 规则模板保存和加载
- [ ] 多表格批处理
- [ ] 智能澄清（AI 主动提问）
- [ ] 公式引擎（如 "=A1+B1"）
- [ ] 完整的文档和教程

---

## 🤝 贡献指南

欢迎提交 Issue 和 Pull Request！

### 开发环境设置
```bash
# 克隆仓库
git clone https://github.com/your-username/Merlin.git
cd Merlin

# 创建虚拟环境
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt

# 配置 API
python setup.py

# 启动开发服务器
python -m uvicorn app.main:app --reload
```

---

## 📄 许可证

MIT License - 详见 [LICENSE](LICENSE) 文件

---

## 🙏 致谢

- **OpenAI / Kimi** - 提供强大的 AI 能力
- **FastAPI** - 优秀的 Python Web 框架
- **Pandas** - 强大的数据处理库

---

## 📮 联系方式

- **Issues**: [GitHub Issues](https://github.com/your-username/Merlin/issues)
- **Email**: gaoxingcun@apache.org
- **文档**: 查看 [product.md](product.md) 了解产品设计思路

---

<p align="center">
  <strong>用 AI 的力量，让 Excel 操作变得简单！</strong><br>
  如果觉得有用，请给个 ⭐️ Star 支持一下！
</p>
