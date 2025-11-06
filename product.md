好的，这是一个非常棒的迭代目标！你 `README.md` 中的 `v1.0.0` 路线图提到了“数学计算”，我们上次也详细讨论了它的重要性。

让我们把 `v0.0.2` 版本的主题定为 **“Excel 工具箱第一期 (The Toolbox v1)”**。

这份功能型开发文档将为你（和你的编程 AI）提供清晰的实现目标。

---

### 📄 Merlin v0.0.2 功能开发文档

**版本:** `0.0.2`
**主题:** Excel 工具箱 (The Toolbox v1)
**目标:** 扩展 Merlin 的能力，从“数据填充”升级为“数据计算与清洗”，实现两个最高频的 Excel 场景。

---

### FEATURE-01: 数学计算工具 (Math Engine)

这是 `v0.0.2` 的**核心功能**，它让你 `README.md` 中规划的 `"让未税单价=参考报价*0.9"` 成为可能。

#### 1.1. 用户故事 (User Story)

* **作为** 商务或财务人员，
* **我想要** 通过自然语言执行“列与列”或“列与数字”之间的数学运算，
* **以便于** 我能快速计算出总价、利润、利润率或折扣价，而无需手动编写 Excel 公式。

#### 1.2. 用户指令 (AI 需理解)

* **(列 x 常数):** `"把'未税单价'乘以 1.13，结果存入'含税单价'列"`
* **(列 x 列):** `"帮我创建一个'总价'列，等于'数量'乘以'单价'"`
* **(列 - 列):** `"计算'利润' = '售价' - '成本价'"`
* **(列 / 列):** `"计算'利润率' = '利润' / '售价'，结果保留4位小数"`
* **(列 + 列):** `"让'合计' = 'A列' + 'B列'"`

#### 1.3. 功能实现 (开发指南)

**1. AI “大脑” (`ai_translator.py`)**

* **新工具名称 (Function Call):** `perform_math`
* **工具参数 (JSON Schema):**
    * `target_col: str` (目标列名, AI 需智能判断是更新现有列还是创建新列)
    * `source_col_1: str` (第一个操作列名)
    * `operator: str` (枚举: `add`, `subtract`, `multiply`, `divide`)
    * `source_col_2_or_number: any` (第二个操作数。AI 需智能判断这是**另一个列名**还是一个**数字**)
    * `round_to: int (optional)` (可选的四舍五入小数位数)

**2. “双手” (`excel_engine.py`)**

* **新方法 (Python Function):** `def perform_math(self, target_col, source_col_1, operator, source_col_2_or_number, round_to=None):`
* **核心实现逻辑 (Pandas):**
    1.  **参数检查:** 检查 `source_col_1` 是否存在。
    2.  **操作数 (Operand) 准备:**
        * **健壮性处理 (关键):** 使用 `pd.to_numeric(self.df[source_col_1], errors='coerce').fillna(0)` 来加载 `col_1` 的数据，这能自动将 "N/A" 或空值转为 0。
        * 检查 `source_col_2_or_number` **是不是一个列名** (例如 `if ... in self.df.columns`)。
        * **如果是列名：** 同样使用 `pd.to_numeric` 加载 `col_2` 的数据。
        * **如果是数字：** 直接使用这个数字作为操作数。
    3.  **执行运算:**
        * 使用 `.add()`, `.subtract()`, `.multiply()`, `.divide()` 方法执行 `col_1` 和 `col_2` 的运算。
    4.  **除零处理:** 在执行 `divide` 后，使用 `df.replace([np.inf, -np.inf], 0)` 将无穷大值替换为 0。
    5.  **四舍五入:** 如果 `round_to` 参数存在，执行 `self.df[target_col] = self.df[target_col].round(round_to)`。
    6.  **保存结果:** 将结果存入 `self.df[target_col]`。
    7.  **返回日志:** `return f"✅ 成功：已计算 '{target_col}' 列。"`

**3. 用户日志 (Log) 关键点**

* **成功日志:** `✅ 成功：已创建/更新 '总价' 列。`
* **警告日志 (健壮性):** 如果 `pd.to_numeric` 过程中发现了非数字（`coerce` 起了作用），应返回一个警告：`⚠️ 警告：在 '数量' 列发现 3 个非数字单元格，已在计算中视为 0。`

---

### FEATURE-02: 数据清洗工具 (Data Cleaner)

这是 `Merlin` 工具箱的第二块拼图，解决 Excel 中最繁琐的“脏活”。

#### 2.1. 用户故事 (User Story)

* **作为** 运营或助理，
* **我想要** 快速清理掉数据中的多余空格、替换特定文本、或填充空白单元格，
* **以便于** 我能快速地将数据标准化，用于后续的分析或系统导入。

#### 2.2. 用户指令 (AI 需理解)

* **(清理空格):** `"帮我清理'设备名称'列前后的空格"`
* **(填充空值):** `"把'备注'列的所有空白单元格都填上'N/A'"`
* **(查找替换):** `"把'客户区域'列里所有的'北京'都替换成'华北区'"`

#### 2.3. 功能实现 (开发指南)

这个功能需要为 AI “大脑”提供 **3 个**新的、小而精的工具。

**1. 工具：`trim_whitespace`**
* **AI 参数:** `column_name: str`
* **Engine 方法:** `def trim_whitespace(self, column_name):`
* **Pandas 逻辑:**
    * `self.df[column_name] = self.df[column_name].astype(str).str.strip()`
    * `return f"✅ 成功：已清理 '{column_name}' 列的行首/行尾空格。"`

**2. 工具：`fill_missing_values`**
* **AI 参数:** `column_name: str`, `fill_value: str`
* **Engine 方法:** `def fill_missing_values(self, column_name, fill_value):`
* **Pandas 逻辑:**
    * `self.df[column_name].fillna(fill_value, inplace=True)`
    * `return f"✅ 成功：已将 '{column_name}' 列的空白单元格填充为 '{fill_value}'。"`

**3. 工具：`find_and_replace`**
* **AI 参数:** `column_name: str`, `find_text: str`, `replace_text: str`
* **Engine 方法:** `def find_and_replace(self, column_name, find_text, replace_text):`
* **Pandas 逻辑:**
    * `self.df[column_name] = self.df[column_name].astype(str).str.replace(find_text, replace_text)`
    * `return f"✅ 成功：已在 '{column_name}' 列中将 '{find_text}' 替换为 '{replace_text}'。"`

---

### v0.0.2 开发路线图 (建议)

1.  **后端 (Engine):** 在 `excel_engine.py` 中，**优先实现**上述 4 个 Python 函数 (`perform_math`, `trim_whitespace`, `fill_missing_values`, `find_and_replace`)。**不依赖 AI，编写单元测试 (如 `test.py`)** 确保它们 100% 可靠。
2.  **后端 (Brain):** 在 `ai_translator.py` 中，将这 4 个工具的 JSON Schema 添加到 `TOOLS_SCHEMA` 列表里。
3.  **联调:** 运行 `start_frontend.sh`，通过前端 UI 测试新的自然语言指令是否能被正确“翻译”和“执行”。


这是一个很好的问题。你已经有了“填充”、“计算”和“清洗”，这覆盖了 60% 的 Excel 繁重工作。

为了让 `Merlin` v0.0.2 (或 v0.1.0) 成为一个更完整的“工具箱”，我们应该瞄准 Excel 中另外几个“高频、繁琐、但有固定模式”的操作。

这里有 3 个“工具集”，它们与你现有的功能完美契合：

-----

### 工具集 3: 文本“缝合”与“造型” (Text Manipulation)

**为什么？**：数据常常是“散装”的。你需要把它们合并起来，或者统一它们的格式。

#### 3.1. 功能: `concatenate` (合并列 / 字符串连接)

  * **用户故事：** “我的‘姓’和‘名’是分开的，我想把它们合并成一个‘全名’列。”
  * **用户指令 (AI 需理解)：**
      * `"帮我创建一个'全名'列，等于'姓'列 + ' ' + '名'列"`
      * `"把'区域'和'城市'列合并到'地址'列"`
  * **功能实现 (开发指南)：**
      * **AI 工具 (Function Call):** `concatenate_columns`
      * **AI 参数:** `target_col: str`, `source_columns: List[str]`, `delimiter: str`
      * **Engine 方法:** `def concatenate_columns(self, target_col, source_columns, delimiter):`
      * **Pandas 逻辑:**
        ```python
        # 确保所有源列都是字符串
        self.df[target_col] = self.df[source_columns].astype(str).agg(delimiter.join, axis=1)
        return f"✅ 成功：已将 {len(source_columns)} 列合并为 '{target_col}'。"
        ```

#### 3.2. 功能: `change_case` (更改大小写)

  * **用户故事：** “我的‘产品编码’(SKU) 有些是大写有些是小写，我想把它们全部统一为大写，以便 VLOOKUP。”
  * **用户指令 (AI 需理解)：**
      * `"把'产品编码'列全部转为大写"`
      * `"让'客户邮箱'列全部小写"`
  * **功能实现 (开发指南)：**
      * **AI 工具 (Function Call):** `change_case`
      * **AI 参数:** `column_name: str`, `case_type: str` (枚举: `upper`, `lower`, `proper`[首字母大写])
      * **Engine 方法:** `def change_case(self, column_name, case_type):`
      * **Pandas 逻辑:**
        ```python
        if case_type == 'upper':
            self.df[column_name] = self.df[column_name].astype(str).str.upper()
        elif case_type == 'lower':
            self.df[column_name] = self.df[column_name].astype(str).str.lower()
        # ...
        return f"✅ 成功：已将 '{column_name}' 列转为 {case_type}。"
        ```

-----

### 工具集 4: 日期与时间 “提取器” (Date/Time Engine)

**为什么？**：Excel 用户在处理日期上花费了 *巨量* 的时间。这是 `Merlin` 可以大放异彩的地方。

#### 4.1. 功能: `extract_date_part` (提取日期组件)

  * **用户故事：** “我有一个‘订单日期’列，我想按‘月份’来分析销售额。”
  * **用户指令 (AI 需理解)：**
      * `"从'订单日期'列提取'月份'，存入'订单月份'新列"`
      * `"帮我从'创建时间'里提取出'年份'"`
      * `"提取'生日'列的'星期几'"`
  * **功能实现 (开发指南)：**
      * **AI 工具 (Function Call):** `extract_date_part`
      * **AI 参数:** `target_col: str`, `source_col: str`, `part_to_extract: str` (枚举: `year`, `month`, `day`, `weekday`, `quarter`)
      * **Engine 方法:** `def extract_date_part(self, target_col, source_col, part_to_extract):`
      * **Pandas 逻辑 (关键：`pd.to_datetime` 和 `.dt` 访问器):**
        ```python
        # 健壮性：强制转为日期，无效的变为 NaT
        date_series = pd.to_datetime(self.df[source_col], errors='coerce')

        if part_to_extract == 'year':
            self.df[target_col] = date_series.dt.year
        elif part_to_extract == 'month':
            self.df[target_col] = date_series.dt.month
        # ...
        return f"✅ 成功：已从 '{source_col}' 提取 '{part_to_extract}' 到 '{target_col}'。"
        ```

-----

### 工具集 5: 结构与统计 “重塑器” (Structure & Stats)

**为什么？**：这能让你 `README.md` 中的“统计分析”功能 变得更强大，并加入 Excel 的另一个核心功能——去重。

#### 5.1. 功能: `drop_duplicates` (删除重复项)

  * **用户故事：** “我的客户列表里，同一个‘客户邮箱’重复了好几次，我只想保留第一个。”
  * **用户指令 (AI 需理解)：**
      * `"帮我删除重复行"` (基于所有列)
      * `"根据'客户邮箱'列，删除重复的数据"` (基于特定列)
  * **功能实现 (开发指南)：**
      * **AI 工具 (Function Call):** `drop_duplicates`
      * **AI 参数:** `subset_columns: List[str] (optional)` (AI 需智能判断：如果用户没说，就传 `None`，代表所有列)
      * **Engine 方法:** `def drop_duplicates(self, subset_columns=None):`
      * **Pandas 逻辑:**
        ```python
        original_count = len(self.df)
        self.df.drop_duplicates(subset=subset_columns, keep='first', inplace=True)
        new_count = len(self.df)
        return f"✅ 成功：已删除 {original_count - new_count} 行重复数据。"
        ```

#### 5.2. 功能: `group_by_aggregate` (分组聚合)

  * **为什么？**：这是你 `README.md` 中“统计设备类型的分布” 功能的**终极版**。它不再只是“计数”(Count)，它可以做“求和”(Sum)、“平均”(Mean)！
  * **用户故事：** “我想知道每个‘设备类型’的‘未税单价’平均值是多少。”
  * **用户指令 (AI 需理解)：**
      * `"按'设备类型'分组，计算'未税单价'的平均值"`
      * `"统计每个'区域'的'销售额'总和"`
  * **功能实现 (开发指南)：**
      * **AI 工具 (Function Call):** `group_by_aggregate`
      * **AI 参数:** `group_by_col: str`, `agg_col: str`, `agg_func: str` (枚举: `mean`, `sum`, `count`)
      * **Engine 方法:** `def group_by_aggregate(self, group_by_col, agg_col, agg_func):`
      * **Pandas 逻辑 (这会返回一个新的 DataFrame，而不是修改原有的):**
        ```python
        # 这个工具不修改 self.df，它返回一个“结果”
        grouped_data = self.df.groupby(group_by_col)[agg_col].agg(agg_func)

        # 将结果格式化为漂亮的日志
        result_log = f"📊 按 '{group_by_col}' 分组，对 '{agg_col}' 进行 '{agg_func}' 聚合结果：\n"
        result_log += grouped_data.to_string() # 转为字符串
        return result_log
        ```
      * **前端修改：** `v0.0.1` 的统计功能 返回的是修改后的 Excel。这个功能应该**只在“执行日志”区域返回统计结果 (文本)**，而**不**生成新文件。



好的，你已经抓住了 `Merlin` 从“Demo”走向“健壮产品”的两个关键节点。

这是一份详细的开发文档，分为两个独立的功能模块。你可以按顺序实现它们。

-----

### 📄 Merlin v0.1.0 (或 v0.2.0) 功能开发文档

**主题：** 用户体验 (UX) 与 架构可扩展性 (Scalability)

-----

### FEATURE-01: 功能发现 (Discoverability)

**目标：** 解决“用户不知道 `Merlin` 能做什么”的问题。我们将通过两种方式（一个简单，一个高级）来引导用户。



#### 1.1. (高级) “魔法棒”功能示例 (Magic Wand Pop-up)

**设计：** 在聊天框旁边放一个 `✨` 按钮。点击它，弹出一个“抽屉”，分类展示 `Merlin` 的所有核心能力。

**实现指南 (Frontend: `index.html` / `app.js`)**

1.  **数据 (Data):**

      * 在 `app.js` 中，定义一个“功能树”对象 (Object)：

    <!-- end list -->

    ```javascript
    // (在 data/setup 中)
    const featureTree = {
      "填充与修改": [
        "把'状态'列全部设为'已完成'",
        "把'设备类型'是'Gateway'的'税率'设为 0.13",
        "把'设备编码'为'196001'的价格设为 100，'196002'的设为 200"
      ],
      "数学与计算": [
        "计算'总价' = '单价' * '数量'",
        "让'利润' = '售价' - '成本价'",
        "计算'折扣价' = '售价' * 0.9 (保留2位小数)"
      ],
      "数据清洗": [
        "清理'客户名称'列前后的空格",
        "把'备注'列的空白单元格填上'N/A'",
        "把'区域'列所有的'北京'替换为'华北区'"
      ],
      "统计与分析": [
        "统计'设备类型'的分布",
        "按'区域'分组，计算'销售额'的总和",
        "从'订单日期'列提取'月份'"
      ]
    };

    const showFeatureModal = ref(false);
    ```

2.  **界面 (UI - `index.html`)**

      * 在聊天输入框（`textarea`）旁边添加一个按钮：
        `<button @click="showFeatureModal = true" class="magic-wand-btn">✨ 功能示例</button>`
      * 创建一个“模态框 (Modal)”或“抽屉 (Drawer)”组件，**默认隐藏** (`v-if="showFeatureModal"`)。
      * 在这个模态框中，使用 `v-for` 来渲染 `featureTree`：

    <!-- end list -->

    ```html
    <div class="modal-overlay" v-if="showFeatureModal" @click.self="showFeatureModal = false">
      <div class="modal-content">
        <h2>Merlin 魔法示例 ✨</h2>
        <div v-for="(examples, category) in featureTree" :key="category">
          <h3>{{ category }}</h3>
          <ul>
            <li v-for="ex in examples" :key="ex" @click="selectExample(ex)">
              {{ ex }}
            </li>
          </ul>
        </div>
      </div>
    </div>
    ```

3.  **逻辑 (Logic - `app.js`)**

      * 实现 `selectExample(exampleText)` 函数：

    <!-- end list -->

    ```javascript
    function selectExample(exampleText) {
      command.value = exampleText; // 复制指令到聊天框
      showFeatureModal.value = false; // 关闭模态框
      // (可选) 让 textarea 自动获得焦点
      document.getElementById('chat-textarea').focus();
    }
    ```

-----

### FEATURE-02: AI 路由架构 (AI Router Architecture)

**目标：** 解决 `TOOLS_SCHEMA` 随功能增多而“爆炸” 的问题。我们将实现你所说的“两阶段 AI 调用”，将“全能 AI”重构为“接待员 (Router)” + “专家 (Specialist)”。

**实现指南 (Backend: `app/ai_translator.py`)**

1.  **步骤 1：定义你的“专家”工具清单 (Schemas)**

      * 在 `ai_translator.py` 中，**打散**你现在巨大的 `TOOLS_SCHEMA`。
      * 你需要为你**所有的** `excel_engine.py` 函数 定义 JSON Schema。

    <!-- end list -->

    ```python
    # (示例)
    # 1. 填充专家的工具
    SCHEMA_FILLING = [
        # set_column_value 的 Schema...
        # set_column_by_condition 的 Schema...
        # copy_column_values 的 Schema...
        # find_and_replace 的 Schema...
    ]

    # 2. 数学专家的工具
    SCHEMA_MATH = [
        # perform_math 的 Schema...
        # (未来) calculate_sum 的 Schema...
    ]

    # 3. 统计专家的工具
    SCHEMA_STATS = [
        # group_by_aggregate 的 Schema...
        # value_counts (你 README 里的统计) 的 Schema...
    ]

    # 4. 清洗/结构专家的工具
    SCHEMA_CLEANING = [
        # trim_whitespace 的 Schema...
        # fill_missing_values 的 Schema...
        # drop_duplicates 的 Schema...
        # concatenate_columns 的 Schema...
    ]

    # ... (其他专家) ...
    ```

2.  **步骤 2：定义你的“路由 (Router)”工具清单**

      * 这是**最关键**的一步。这个清单**不包含**任何 `excel_engine.py` 的函数。
      * 它只包含“分类”函数。

    <!-- end list -->

    ```python
    SCHEMA_ROUTER = [
        {
            "type": "function",
            "function": {
                "name": "route_to_filling_expert",
                "description": "用于填充、设置、修改、复制或替换单元格的值。例如: '把A设为B', '把所有C改为D', '复制A到B'",
                # "parameters": { "type": "object", "properties": {} } # 无参数
            }
        },
        {
            "type": "function",
            "function": {
                "name": "route_to_math_expert",
                "description": "用于所有数学计算。例如: '计算A=B*C', 'A=B+D', 'A=B*0.9'",
                # "parameters": ...
            }
        },
        {
            "type": "function",
            "function": {
                "name": "route_to_stats_expert",
                "description": "用于统计、分析、汇总、分组、计数、提取日期。例如: '统计A的分布', '按B分组计算C', '提取月份'",
                # "parameters": ...
            }
        },
        {
            "type": "function",
            "function": {
                "name": "route_to_cleaning_expert",
                "description": "用于数据清洗。例如: '清理空格', '填充空白', '删除重复', '合并列', '改大小写'",
                # "parameters": ...
            }
        }
    ]
    ```

3.  **步骤 3：重构 `ai_translator.py`**

      * 你需要一个**统一的** AI 调用函数：

    <!-- end list -->

    ```python
    def _call_ai(command: str, headers: list, tools: list):
        # (这里是你现有的调用 Kimi / OpenAI 的代码)
        system_prompt = f"你是 Merlin 助手。表格列为: {headers}。请根据用户指令调用工具。"
        
        response = client.chat.completions.create(
            model="...",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": command}
            ],
            tools=tools,
            tool_choice="auto" # 或 "required"
        )
        # (返回 response_message)
    ```

      * 修改你**现有**的 `get_ai_instructions` (或类似) 函数，让它执行**两阶段调用**：

    <!-- end list -->

    ```python
    def get_ai_instructions(command: str, headers: list):
        
        # --- 阶段 1: AI 路由调用 ---
        try:
            router_response = _call_ai(command, headers, SCHEMA_ROUTER)
            tool_calls = router_response.choices[0].message.tool_calls
            
            if not tool_calls:
                # AI 无法分类，可能只是聊天，或使用默认
                print("路由失败，使用默认专家...")
                selected_schema = SCHEMA_FILLING # (选择一个默认的)
            else:
                # 路由成功！
                route_name = tool_calls[0].function.name
                
                # --- 选择“专家”的工具清单 ---
                if route_name == "route_to_math_expert":
                    selected_schema = SCHEMA_MATH
                elif route_name == "route_to_stats_expert":
                    selected_schema = SCHEMA_STATS
                elif route_name == "route_to_cleaning_expert":
                    selected_schema = SCHEMA_CLEANING
                else: # route_to_filling_expert
                    selected_schema = SCHEMA_FILLING
                    
        except Exception as e:
            print(f"路由阶段出错: {e}")
            # 出错时，回退到默认（例如，最大的那个 schema）
            selected_schema = SCHEMA_FILLING 
        
        
        # --- 阶段 2: AI 专家调用 ---
        try:
            # *再次*调用同一个 AI，但这次使用“专家”的工具清单
            specialist_response = _call_ai(command, headers, selected_schema)
            
            # (这里是你现有的逻辑，解析 specialist_response 并返回 JSON 指令)
            final_tool_calls = specialist_response.choices[0].message.tool_calls
            if not final_tool_calls:
                raise Exception("专家 AI 未能找到合适的工具。")
                
            # ... (解析 final_tool_calls 并返回) ...
            
        except Exception as e:
            print(f"专家阶段出错: {e}")
            raise # 将错误抛给 API 端点
    ```

4.  **`app/main.py` 的改动**

      * **零改动。**
      * 你的 `/execute` 接口仍然只是调用 `get_ai_instructions`。所有的复杂性都被你完美地封装在 `ai_translator.py` 内部了。




这是一份面向 `v0.0.4` 的详细开发文档，主题是 **"全功能工具箱 (The Complete Toolbox)"**。

-----

### 📄 Merlin v0.0.4 功能开发文档

**版本:** `v0.0.4` (分阶段发布)
**主题:** 全功能工具箱 (Completing the Toolbox)
**目标:** 继 `v0.0.2` 的"数学"和"清洗"工具之后，补全 Excel 中最高频的"文本处理"、"日期处理"和"表格结构"操作。

**实施方案:** 采用分阶段渐进式开发
- **v0.0.4-alpha** (✅ 已完成): 3个核心功能（concatenate_columns, extract_date_part, group_by_aggregate）
- **v0.0.4-beta** (🚧 规划中): 增加 4个功能（split_column, change_case, drop_duplicates, sort_by_column）
- **v0.0.4 正式版** (🔮 未来): 完整的 8个功能

**开发建议总结:**
1. **group_by_aggregate 返回格式** - 已采纳：统一返回 Dict 格式，添加 is_analysis 标记
2. **split_column 新列名处理** - 已优化：智能补全和截断逻辑
3. **工具路由关键词扩充** - 已实施：新增 text、date 分组，扩展 analysis 分组
4. **extract_date_part 星期显示** - 已优化：使用中文显示（星期一~星期日）
5. **前端魔法棒分类** - 已更新：新增文本处理和日期工具分类

-----

### FEATURE-01: 文本工具箱 (Text Toolbox)

**目标:** 解决数据“缝合”与“拆分”的繁琐操作。

#### 1.1. 功能: `concatenate_columns` (合并列)

  * **用户故事:** “我的‘姓’和‘名’是分开的，我想把它们合并成一个‘全名’列，中间用空格隔开。”
  * **用户指令 (AI 需理解):**
      * `"帮我创建一个'全名'列，等于'姓' + ' ' + '名'"`
      * `"把'区域'和'城市'列合并到'地址'列，用'-'连接"`
  * **开发指南:**
      * **AI “大脑” (`ai_translator.py`):**
          * **工具名称 (Function Call):** `concatenate_columns`
          * **工具参数 (JSON Schema):**
              * `target_col: str` (新列的名称)
              * `source_columns: List[str]` (要合并的源列名数组，例如 `['姓', '名']`)
              * `delimiter: str` (连接符，例如 `' '` 或 `'-'`)
      * **“双手” (`excel_engine.py`):**
          * **Engine 方法:** `def concatenate_columns(self, target_col: str, source_columns: list, delimiter: str):`
          * **Pandas 逻辑:**
            ```python
            # 健壮性：确保所有源列都是字符串
            self.df[target_col] = self.df[source_columns].astype(str).agg(delimiter.join, axis=1)
            return f"✅ 成功：已将 {len(source_columns)} 列合并为 '{target_col}'，使用 '{delimiter}' 连接。"
            ```

#### 1.2. 功能: `split_column` (拆分列)

  * **用户故事:** “我的‘客户信息’列是‘张三-13800000000’，我想把它按‘-’拆分成‘姓名’和‘电话’两列。”
  * **用户指令 (AI 需理解):**
      * `"把'客户信息'列按'-'拆分"`
      * `"将'全名'列按空格拆分为'姓'和'名'"`
  * **开发指南:**
      * **AI “大脑” (`ai_translator.py`):**
          * **工具名称 (Function Call):** `split_column`
          * **工具参数 (JSON Schema):**
              * `source_col: str` (要拆分的源列名)
              * `delimiter: str` (分隔符)
              * `new_column_names: List[str] (optional)` (可选的新列名数组。AI 尽量从指令中提取，如 `['姓', '名']`。如果未提供，Engine 自动命名为 `_1`, `_2`)
      * **“双手” (`excel_engine.py`):**
          * **Engine 方法:** `def split_column(self, source_col: str, delimiter: str, new_column_names: list = None):`
          * **Pandas 逻辑:**
            ```python
            # 拆分成一个临时的 DataFrame
            split_data = self.df[source_col].astype(str).str.split(delimiter, expand=True)

            # 确定新列名
            if not new_column_names:
                new_column_names = [f"{source_col}_{i+1}" for i in range(split_data.shape[1])]
            else:
                # 确保列名数量匹配
                if len(new_column_names) != split_data.shape[1]:
                    # (此处应有更健壮的逻辑，例如截断或补全)
                    new_column_names = new_column_names[:split_data.shape[1]]

            # 赋给新的列
            split_data.columns = new_column_names
            self.df = pd.concat([self.df, split_data], axis=1)

            return f"✅ 成功：已将 '{source_col}' 列按 '{delimiter}' 拆分为 {len(new_column_names)} 列。"
            ```

#### 1.3. 功能: `change_case` (更改大小写)

  * **用户故事:** “我的‘产品编码’(SKU) 有些是大写有些是小写，我想把它们全部统一为大写。”
  * **用户指令 (AI 需理解):** `"把'产品编码'列全部转为大写"`
  * **开发指南:**
      * **AI “大脑” (`ai_translator.py`):**
          * **工具名称 (Function Call):** `change_case`
          * **工具参数 (JSON Schema):**
              * `column_name: str`
              * `case_type: str` (枚举: `upper`, `lower`, `proper` [首字母大写])
      * **“双手” (`excel_engine.py`):**
          * **Engine 方法:** `def change_case(self, column_name: str, case_type: str):`
          * **Pandas 逻辑:**
            ```python
            if case_type == 'upper':
                self.df[column_name] = self.df[column_name].astype(str).str.upper()
            elif case_type == 'lower':
                self.df[column_name] = self.df[column_name].astype(str).str.lower()
            elif case_type == 'proper':
                self.df[column_name] = self.df[column_name].astype(str).str.title() # Pandas 的 title() 即 Excel 的 PROPER()
            else:
                return f"❌ 错误：不支持的大小写类型 '{case_type}'。"
            return f"✅ 成功：已将 '{column_name}' 列转为 {case_type}。"
            ```

-----

### FEATURE-02: 日期工具箱 (Date Toolbox)

**目标:** 解决 Excel 中最繁琐的日期提取操作。

#### 2.1. 功能: `extract_date_part` (提取日期组件)

  * **用户故事:** “我有一个‘订单日期’列，我想按‘月份’来分析销售额。”
  * **用户指令 (AI 需理解):**
      * `"从'订单日期'列提取'月份'，存入'订单月份'新列"`
      * `"帮我从'创建时间'里提取出'年份'"`
      * `"提取'生日'列的'星期几'"`
  * **开发指南:**
      * **AI “大脑” (`ai_translator.py`):**
          * **工具名称 (Function Call):** `extract_date_part`
          * **工具参数 (JSON Schema):**
              * `source_col: str`
              * `target_col: str` (AI 智能生成，例如 `'订单日期_月份'`)
              * `part_to_extract: str` (枚举: `year`, `month`, `day`, `weekday` [星期], `quarter` [季度])
      * **“双手” (`excel_engine.py`):**
          * **Engine 方法:** `def extract_date_part(self, source_col: str, target_col: str, part_to_extract: str):`
          * **Pandas 逻辑:**
            ```python
            # 关键：健壮地转为日期，无法解析的变为 NaT (Not a Time)
            date_series = pd.to_datetime(self.df[source_col], errors='coerce')

            if date_series.isnull().all():
                return f"⚠️ 警告：无法将 '{source_col}' 列解析为日期。"

            if part_to_extract == 'year':
                self.df[target_col] = date_series.dt.year
            elif part_to_extract == 'month':
                self.df[target_col] = date_series.dt.month
            elif part_to_extract == 'day':
                self.df[target_col] = date_series.dt.day
            elif part_to_extract == 'weekday':
                self.df[target_col] = date_series.dt.weekday # (周一=0, 周日=6)
            elif part_to_extract == 'quarter':
                self.df[target_col] = date_series.dt.quarter
            else:
                return f"❌ 错误：不支持的日期部分 '{part_to_extract}'。"

            return f"✅ 成功：已从 '{source_col}' 提取 '{part_to_extract}' 到 '{target_col}'。"
            ```

-----

### FEATURE-03: 结构工具箱 (Structure Toolbox)

**目标:** 允许用户操作表格本身的结构，而不只是单元格的值。

#### 3.1. 功能: `drop_duplicates` (删除重复项)

  * **用户故事:** “我的客户列表里，同一个‘客户邮箱’重复了好几次，我只想保留第一个。”
  * **用户指令 (AI 需理解):**
      * `"帮我删除重复行"` (AI 传 `subset_columns=None`)
      * `"根据'客户邮箱'列，删除重复的数据"` (AI 传 `subset_columns=['客户邮箱']`)
  * **开发指南:**
      * **AI “大脑” (`ai_translator.py`):**
          * **工具名称 (Function Call):** `drop_duplicates`
          * **工具参数 (JSON Schema):**
              * `subset_columns: List[str] (optional)` (用于判断重复的列，如果为 `null` 或 `[]`，则判断所有列)
      * **“双手” (`excel_engine.py`):**
          * **Engine 方法:** `def drop_duplicates(self, subset_columns: list = None):`
          * **Pandas 逻辑:**
            ```python
            original_count = len(self.df)
            # 如果 subset_columns 是空列表，Pandas 会报错，需转为 None
            subset = subset_columns if subset_columns else None

            self.df.drop_duplicates(subset=subset, keep='first', inplace=True)
            new_count = len(self.df)
            return f"✅ 成功：已删除 {original_count - new_count} 行重复数据。"
            ```

#### 3.2. 功能: `sort_by_column` (排序)

  * **用户故事:** “我想按‘销售额’列从高到低重新排列这个表格。”
  * **用户指令 (AI 需理解):**
      * `"按'销售额'列降序排序"` (AI 传 `ascending=False`)
      * `"把表格按'日期'升序排列"` (AI 传 `ascending=True`)
  * **开发指南:**
      * **AI “大脑” (`ai_translator.py`):**
          * **工具名称 (Function Call):** `sort_by_column`
          * **工具参数 (JSON Schema):**
              * `column_name: str`
              * `ascending: bool = True` (默认为 `True` [升序])
      * **“双手” (`excel_engine.py`):**
          * **Engine 方法:** `def sort_by_column(self, column_name: str, ascending: bool = True):`
          * **Pandas 逻辑:**
            ```python
            self.df.sort_values(by=column_name, ascending=ascending, inplace=True)
            order_desc = "降序" if not ascending else "升序"
            return f"✅ 成功：已按 '{column_name}' 列 {order_desc} 排序。"
            ```

#### 3.3. 功能: `drop_columns` (删除列)

  * **用户故事:** “‘备注’和‘内部编码’这两列我不需要了，帮我删掉。”
  * **用户指令 (AI 需理解):** `"删除'备注'和'内部编码'列"`
  * **开发指南:**
      * **AI “大脑” (`ai_translator.py`):**
          * **工具名称 (Function Call):** `drop_columns`
          * **工具参数 (JSON Schema):**
              * `columns_to_drop: List[str]`
      * **“双手” (`excel_engine.py`):**
          * **Engine 方法:** `def drop_columns(self, columns_to_drop: list):`
          * **Pandas 逻辑:**
            ```python
            # 健壮性：只删除实际存在的列，避免报错
            existing_cols = [col for col in columns_to_drop if col in self.df.columns]
            if not existing_cols:
                return f"⚠️ 警告：要删除的列 {columns_to_drop} 均不存在。"
                
            self.df.drop(columns=existing_cols, inplace=True)
            return f"✅ 成功：已删除 {len(existing_cols)} 列: {', '.join(existing_cols)}。"
            ```

-----

### FEATURE-04: 统计引擎 v2 (升级)

**目标:** 升级 `v0.0.1` 的“统计分析” 功能，从“计数” 升级为“分组聚合”。

#### 4.1. 功能: `group_by_aggregate` (分组聚合)

  * **用户故事:** “我想知道每个‘设备类型’的‘未税单价’平均值是多少。”
  * **用户指令 (AI 需理解):**
      * `"按'设备类型'分组，计算'未税单价'的平均值"`
      * `"统计每个'区域'的'销售额'总和"`
  * **开发指南:**
      * **AI “大脑” (`ai_translator.py`):**
          * **工具名称 (Function Call):** `group_by_aggregate`
          * **工具参数 (JSON Schema):**
              * `group_by_col: str` (分组列)
              * `agg_col: str` (计算列)
              * `agg_func: str` (枚举: `mean`[平均], `sum`[求和], `count`[计数])
      * **“双手” (`excel_engine.py`):**
          * **Engine 方法:** `def group_by_aggregate(self, group_by_col: str, agg_col: str, agg_func: str):`
          * **重要设计:** **此工具不修改 `self.df`**。它只计算并返回一个**文本日志**。
          * **Pandas 逻辑:**
            ```python
            try:
                # 健壮性：计算前确保 agg_col 是数字
                if agg_func in ['mean', 'sum']:
                    self.df[agg_col] = pd.to_numeric(self.df[agg_col], errors='coerce').fillna(0)
                
                grouped_data = self.df.groupby(group_by_col)[agg_col].agg(agg_func)
                
                # 格式化为漂亮的字符串
                result_log = f"📊 按 '{group_by_col}' 分组，对 '{agg_col}' 进行 '{agg_func}' 聚合结果：\n"
                result_log += "="*30 + "\n"
                result_log += grouped_data.to_string() # to_string() 易于阅读
                
                # 关键：这个工具只返回日志，不修改 df
                return result_log
            except Exception as e:
                return f"❌ 错误：聚合失败: {e}"
            ```

-----

### 🚀 v0.0.4 整合计划 (Implementation Plan)

1.  **后端 (`excel_engine.py`):**

      * 一次性添加上述所有**新**的 `Engine 方法` (`concatenate_columns`, `split_column`, `change_case`, `extract_date_part`, `drop_duplicates`, `sort_by_column`, `drop_columns`, `group_by_aggregate`)。
      * **单元测试:** 强烈建议使用 `test.py` 对这些新方法进行“引擎测试”，确保它们在不依赖 AI 的情况下 100% 工作正常。

2.  **后端 (`ai_translator.py`):**

      * **AI 路由:** 你需要**升级你的“路由”**。
          * 创建新的“专家”分类，例如 `SCHEMA_TEXT_TOOLS` (合并, 拆分, 大小写), `SCHEMA_DATE_TOOLS` (提取日期), `SCHEMA_STRUCTURE_TOOLS` (删除重复, 排序, 删列)。
          * 修改你的 `SCHEMA_ROUTER`，添加新的“路由” `route_to_text_expert` 等。
      * **专家 Schema:** 将所有新的 JSON Schema 添加到对应的“专家”列表中。

3.  **前端 (`frontend/`):**

      * **魔法棒:** 更新 `frontend/app.js` 中的 `featureTree` 对象。
      * 添加新的分类，例如 **"5. 文本处理"**，**"6. 日期工具"**，**"7. 表格结构"**。
      * 把你 `v0.0.1` 的"统计分析" 示例更新为 `group_by_aggregate` 的指令（例如 `"按'区域'统计'销售额'总和"`）。

-----

### 📋 v0.0.4-alpha 实施总结

**发布日期:** 2025-11-06
**实施人员:** TJxiaobao（开发）+ AI Assistant（协助）

#### ✅ 已完成项

1. **代码质量提升**
   - 所有代码文件（excel_engine.py, ai_translator.py, main.py, config.py, utils.py, test.py, setup.py, frontend/app.js）添加作者信息和 MIT License 声明

2. **3个核心功能实现**
   - ✅ `concatenate_columns`: 合并多列为一列（支持自定义分隔符）
   - ✅ `extract_date_part`: 从日期列提取年/月/日/星期/季度（星期几显示为中文）
   - ✅ `group_by_aggregate`: 分组聚合统计（支持平均值/总和/计数，只统计不修改表格）

3. **AI 翻译模块升级 (ai_translator.py)**
   - 新增 `text` 工具组（关键词：合并、拆分、连接等）
   - 新增 `date` 工具组（关键词：日期、年份、月份等）
   - 扩展 `analysis` 工具组（新增：分组、聚合、平均、求和等关键词）
   - 添加 3个新工具的 JSON Schema 定义
   - 更新 system prompt 和帮助信息

4. **后端调度逻辑 (main.py)**
   - 新增 3个工具的调度逻辑
   - 特殊处理 `group_by_aggregate`（分析类工具不保存文件）

5. **前端界面更新 (frontend/index.html)**
   - 新增"文本处理"分类（2个示例）
   - 新增"日期工具"分类（3个示例）
   - 统计分析分类新增分组聚合示例

6. **文档更新**
   - VERSION: 更新至 v0.0.4-alpha，详细说明新功能
   - README.md: 更新版本号、典型场景、产品路线图
   - product.md: 添加实施方案、开发建议总结、实施总结

#### 🎯 技术亮点

1. **健壮性设计**
   - `concatenate_columns`: 自动将所有源列转为字符串，避免类型错误
   - `extract_date_part`: 使用 `pd.to_datetime(errors='coerce')` 健壮地解析日期，提供无法解析的数量警告
   - `group_by_aggregate`: 数值聚合前自动转换为数字类型

2. **用户体验优化**
   - 星期几显示为中文（星期一~星期日）而非数字
   - 分析类工具直接返回结果，无需下载文件
   - 清晰的日志输出和错误提示

3. **代码规范**
   - 统一的返回格式（Dict with success, message, error）
   - 详细的 docstring 注释
   - 合理的类型注解（Type Hints）

#### 🧪 测试建议

由于 v0.0.4-alpha 是首个 alpha 版本，建议进行以下测试：

1. **引擎测试（不依赖 AI）**
```bash
python test.py engine
```

2. **完整测试（含 AI）**
```bash
python test.py quick  # 单个指令快速测试
```

3. **前端集成测试**
```bash
./start_frontend.sh
# 手动测试新功能示例
```

#### 📌 已知限制

1. `group_by_aggregate` 当前只支持单列聚合，未来可考虑支持多列聚合
2. `extract_date_part` 对于无法解析的日期会返回 NaN，但不会停止执行
3. `concatenate_columns` 会将所有类型强制转为字符串，数字列会失去数字格式

#### 🚀 后续计划（v0.0.4-beta）

按照原定计划，v0.0.4-beta 将新增以下 4个功能：
1. `split_column`: 拆分列（已在 product.md 中详细设计）
2. `change_case`: 大小写转换
3. `drop_duplicates`: 删除重复行
4. `sort_by_column`: 排序

预计开发周期：1-2周

#### 💡 总结

v0.0.4-alpha 成功实现了方案A的 3个核心功能，代码质量和用户体验均有提升。分阶段发布策略降低了风险，为后续的 beta 版本和正式版奠定了良好基础。

---

### 📋 v0.0.4-beta 实施总结

**发布日期:** 2025-11-06
**实施人员:** TJxiaobao（开发）+ AI Assistant（协助）

#### ✅ 已完成项

1. **4个新功能实现**
   - ✅ `split_column`: 拆分列（按分隔符将一列拆分为多列）
   - ✅ `change_case`: 大小写转换（upper/lower/proper）
   - ✅ `drop_duplicates`: 删除重复行（支持全表或指定列）
   - ✅ `sort_by_column`: 按列排序（升序/降序）

2. **AI 翻译模块升级 (ai_translator.py)**
   - 新增 `structure` 工具组（关键词：删除重复、去重、排序、升序、降序、从高到低、从低到高）
   - 扩展 `text` 工具组（新增 split_column 和 change_case，关键词：拆分、按...拆分、转为大写、转为小写等）
   - 添加 4个新工具的 JSON Schema 定义
   - 更新 system prompt 和帮助信息

3. **后端调度逻辑 (main.py)**
   - 新增 4个工具的调度逻辑
   - sort_by_column 支持布尔值参数智能转换

4. **前端界面更新 (frontend/index.html)**
   - 新增"🏗️ 表格结构"分类（4个示例）
   - 扩展"文本处理"分类（新增 2个 beta 示例）

5. **文档更新**
   - VERSION: 更新至 v0.0.4-beta，详细说明新功能和技术改进
   - README.md: 更新版本号、典型场景、产品路线图，新增 v0.0.5 规划
   - product.md: 添加 beta 实施总结

#### 🎯 技术亮点

1. **健壮性设计**
   - `split_column`: 智能补全/截断列名，用户友好的警告提示
   - `change_case`: 完整支持 upper/lower/proper 三种模式
   - `drop_duplicates`: 支持全表或指定列去重，自动重置索引
   - `sort_by_column`: 排序后自动重置索引，保持数据整洁

2. **用户体验优化**
   - 所有工具都有清晰的中文描述（如"已将XX列转为大写"）
   - drop_duplicates 返回删除数量和剩余行数
   - split_column 智能处理列名数量不匹配的情况
   - 统一的错误处理和返回格式

3. **代码质量**
   - 统一的返回格式（Dict with success, message, error）
   - 详细的 docstring 注释
   - 合理的类型注解（Type Hints）
   - 工具映射表清晰标注版本（v0.0.4-beta）

#### 🧪 测试结果

**引擎测试（不依赖 AI）- 100% 通过 ✅**

测试场景：
1. **split_column**: 将"客户信息"（张三-13800000000）拆分为"姓名"和"电话" ✅
2. **change_case**: 将产品编码从"sku001"转为"SKU001" ✅
3. **drop_duplicates**: 删除重复的"张三"行（4行→3行） ✅
4. **sort_by_column**: 按销售额降序排序（5000→3000→1000） ✅

测试数据流：
```
初始数据（4行）
  ↓ split_column
+ 添加"姓名"和"电话"两列
  ↓ change_case
+ 产品编码全部大写
  ↓ drop_duplicates
- 删除 1 行重复数据（3行）
  ↓ sort_by_column
+ 按销售额降序排序
  ↓
最终结果：3行，6列，已排序
```

#### 📊 v0.0.4 全版本成果总结

**工具增长:**
- v0.0.3: 9 个工具
- v0.0.4-alpha: +3 个工具（12个）
- v0.0.4-beta: +4 个工具（**16个**） ⭐️

**分组增长:**
- v0.0.3: 4 个分组
- v0.0.4-alpha: +2 个分组（text, date）
- v0.0.4-beta: +1 个分组（structure）= **7 个分组** ⭐️

**功能分类完整性:**
- ✅ 数据填充（4个工具）
- ✅ 数学计算（1个工具）
- ✅ 数据清洗（3个工具）
- ✅ 文本处理（3个工具）⭐️ 新增分类
- ✅ 日期工具（1个工具）⭐️ 新增分类
- ✅ 表格结构（2个工具）⭐️ 新增分类
- ✅ 统计分析（2个工具）

#### 📌 已知限制

1. `split_column` 当前不支持正则表达式分隔符，仅支持固定字符串
2. `change_case` 的 proper 模式使用 Pandas 的 `title()`，对某些特殊情况可能不完美
3. `drop_duplicates` 固定保留首次出现的行，未来可考虑支持保留最后一次出现
4. `sort_by_column` 当前仅支持单列排序，未来可考虑多列复合排序

#### 🚀 后续计划（v0.0.5）

根据 product.md 和 README.md 规划，v0.0.5 将聚焦"结构扩展"：
1. `drop_columns`: 删除列（已在 product.md 中详细设计）
2. `rename_column`: 重命名列
3. `insert_column`: 插入新列
4. `convert_type`: 数据类型转换

预计开发周期：1-2周

#### 💡 总结

v0.0.4-beta 成功完成了"全功能工具箱"的目标：
- ✅ 完整实现了 7 个新工具（alpha 3个 + beta 4个）
- ✅ 建立了文本处理、日期工具、表格结构 3 个新的功能分类
- ✅ 工具总数从 9 个增长到 16 个，增长率 77.8%
- ✅ 所有新工具测试通过，功能稳定

**亮点:**
- 代码质量持续提升（完善的错误处理、类型注解、docstring）
- 用户体验优化（中文提示、智能警告、友好的返回信息）
- 架构设计合理（统一的工具映射、清晰的分组路由）

**建议:**
- 在生产环境使用前，建议进行更全面的集成测试
- 可以考虑添加单元测试框架（pytest）
- 性能优化：大文件（10万+行）的去重和排序性能

---

**文档作者:** TJxiaobao  
**最后更新:** 2025-11-06 (v0.0.4-beta)
