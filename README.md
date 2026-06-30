# CRM 接口自动化测试框架

AI + MCP 驱动的企业 CRM 系统 API 接口自动化测试框架。支持 YAML 数据驱动、多账号角色切换、业务依赖链管理、AI 用例智能生成、语义断言、自愈引擎、根因分析、企业微信通知，集成 DeepSeek / 通义千问 / 智谱 / Kimi / 豆包 / 混元等国产大模型。

## 架构总览

```
┌──────────────────────────────────────────────────────────────┐
│                   AI 智能决策层 (LLM Agent)                    │
│  ┌───────────┐ ┌───────────┐ ┌───────────┐ ┌──────────────┐ │
│  │ 用例智能   │ │ 语义断言   │ │ 根因分析   │ │ Self-Healing │ │
│  │ 生成引擎   │ │ 推理引擎   │ │ 引擎      │ │ 自愈引擎     │ │
│  └─────┬─────┘ └─────┬─────┘ └─────┬─────┘ └──────┬───────┘ │
│        └─────────────┴──────┬──────┴───────────────┘         │
│                    ┌────────▼────────┐                       │
│                    │   LLM 统一客户端  │                       │
│                    │ (国产大模型适配)  │                       │
│                    └────────┬────────┘                       │
└─────────────────────────────┼────────────────────────────────┘
                              │ MCP 协议
┌─────────────────────────────┼────────────────────────────────┐
│                  MCP 服务层                                    │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐         │
│  │ ApiPost MCP  │ │  数据库 MCP   │ │  报告 MCP    │         │
│  │ ·接口元数据   │ │ ·CRM业务数据  │ │ ·执行结果     │         │
│  │ ·接口调试     │ │ ·测试数据池   │ │ ·趋势分析     │         │
│  └──────┬───────┘ └──────┬───────┘ │ ·企业微信推送  │         │
└─────────┴────────────────┴─────────┴─────────────────────────┘
                              │
┌─────────────────────────────┼────────────────────────────────┐
│                测试执行引擎层 (pytest)                          │
│  ┌────────────┐ ┌───────────▼──────────┐ ┌──────────────┐   │
│  │ 测试调度器  │ │  pytest + conftest   │ │  结果收集器   │   │
│  └────────────┘ └──────────────────────┘ └──────────────┘   │
└──────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────┼────────────────────────────────┐
│                持续反馈层                                      │
│  ┌──────────────┐ ┌─────────▼────────┐ ┌──────────────┐     │
│  │ HTML 报告    │ │  AI 分析报告       │ │ 企业微信通知  │     │
│  └──────────────┘ └────────────────────┘ └──────────────┘     │
└──────────────────────────────────────────────────────────────┘
```

## 项目结构

```
auto_api_rmp_new/
├── conftest.py                 # pytest 全局 fixture (登录/账号工厂/会话上下文/AI/DB/通知)
├── pytest.ini                  # pytest 配置
├── run.py                      # 运行入口 (支持 --all/--file/--list-cases/--list-accounts)
│
├── test_cases/                 # 测试用例 (pytest)
│   ├── test_login.py           # 登录接口测试 (YAML 数据驱动)
│   ├── test_clue.py            # 线索接口测试 (YAML 数据驱动)
│   ├── test_ai_add_clue.py     # 线索接口测试 (Python 编程模式 + DataFactory)
│   └── demo1.py / demo2.py     # 历史示例
│
├── datas/                      # 测试数据
│   ├── yaml_cases/             # YAML 数据驱动用例 (推荐)
│   │   ├── login_cases.yaml    # 登录接口用例数据
│   │   └── clue_cases.yaml     # 线索接口用例数据
│   ├── case_data.xlsx          # Excel 接口用例数据 (历史)
│   └── ai_case_registry.json   # AI 生成用例注册表
│
├── common/                     # 公共模块
│   ├── my_request.py           # HTTP 请求封装 (requests.Session)
│   ├── session_context.py      # 会话上下文 + 响应数据提取器 (依赖链核心)
│   ├── data_factory.py         # 动态数据工厂 (@xxx 标签 / ${xxx} 引用)
│   ├── yaml_runner.py          # YAML 用例执行引擎 (断言/提取/数据解析)
│   ├── get_config.py           # 配置文件读取 (环境切换/多账号角色)
│   ├── do_excel.py             # Excel 读写操作 (openpyxl)
│   ├── Log_packing.py          # 日志模块 (按日滚动)
│   ├── contants.py             # 项目路径常量
│   ├── query_data.py           # 数据库查询 (pymysql)
│   ├── feedback.py             # 持续反馈层 (AI 分析报告 + 趋势)
│   └── Email.py                # 邮件发送
│
├── ai/                         # AI 能力层
│   ├── config.py               # AI 配置管理 (YAML, 多模型切换)
│   ├── llm_client.py           # 统一 LLM 客户端 (8家国产大模型)
│   ├── case_generator.py       # AI 用例智能生成引擎 (支持 YAML + Python 双模式)
│   ├── smart_assert.py         # 语义断言引擎
│   ├── self_healing.py         # Self-Healing 自愈引擎
│   ├── root_cause.py           # 失败根因分析引擎
│   └── prompts/                # Prompt 模板
│       ├── case_gen.py         # 用例生成 prompt (四维度测试设计)
│       ├── assert_gen.py       # 断言生成 prompt
│       └── analysis.py         # 分析 prompt
│
├── mcp_servers/                # MCP 服务层
│   ├── apipost_server.py       # ApiPost MCP (接口元数据/调试/变更检测)
│   ├── database_server.py      # 数据库 MCP (SQL查询/表结构/数据比对)
│   └── report_server.py        # 报告 MCP (结果收集/历史趋势/JSON导出/企业微信推送)
│
├── config/                     # 配置文件
│   ├── test.ini                # 环境配置 / 日志级别 / 数据库 / 通知
│   ├── ai_config.yaml          # AI 模型配置 (多 provider)
│   └── users.yaml              # 多账号角色配置 (销售/助理/管理员/市场)
│
├── logs/                       # 运行日志 (自动生成, 按日滚动)
└── reports/                    # 测试报告 (自动生成 HTML)
```

## 环境要求

- Python 3.8+
- 依赖包：

```
pytest
requests
openpyxl
pymysql
pytest-testreport
openai
pyyaml
```

安装依赖：

```bash
pip install pytest requests openpyxl pymysql pytest-testreport openai pyyaml
```

## 快速开始

### 1. 配置环境

编辑 `config/test.ini`，配置环境和通知：

```ini
[env]
# 当前激活环境: test / gray / prod (只改这一行即可切换环境)
active=test

[host]
test=https://test-api.example.com
gray=https://gray-api.example.com
prod=https://api.example.com
```

切换环境只需修改 `active` 值，无需改动任何代码。

### 2. 配置测试账号

编辑 `config/users.yaml`，配置不同角色的测试账号（所有账号统一在此管理，与代码分离）：

```yaml
default:
  user: admin
  pwd: admin123
  role: "default"

sale_account_1:
  user: sale001
  pwd: password123
  role: "sale"
  department: "销售一部"

assistant_account:
  user: assistant001
  pwd: password123
  role: "assistant"
  department: "销售助理"
```

### 3. 配置企业微信通知（可选）

在 `config/test.ini` 的 `[notify]` 段配置：

```ini
[notify]
# 企业微信群机器人 Webhook 地址
wecom_webhook=https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=你的key
# 消息类型: markdown / text / template_card
wecom_msg_type=markdown
# @ 的 userid 列表 (逗号分隔, @all 为所有人)
wecom_mentioned_list=zhangsan,lisi
# @ 的手机号列表 (仅 text 类型支持, 逗号分隔)
wecom_mentioned_mobile=13800001111
```

不配置 `wecom_webhook` 则不推送，不影响原有功能。

### 4. 配置 AI 模型（可选）

编辑 `config/ai_config.yaml`，填入 API Key：

```yaml
llm:
  provider: deepseek
  model: deepseek-chat
  api_key: "sk-xxx"
```

### 5. 运行测试

```bash
# 运行全部用例
python run.py --all

# 运行指定文件
python run.py --file test_clue.py

# 按关键字过滤
python run.py --all -k login

# 列出所有 YAML 测试数据
python run.py --list-cases

# 列出所有可用测试账号
python run.py --list-accounts
```

或使用 pytest 命令：

```bash
pytest test_cases/ -v                           # 运行全部
pytest test_cases/test_clue.py -v               # 运行指定文件
pytest test_cases/test_clue.py -k "add_clue" -v # 按关键字过滤
```

### 6. 查看报告

测试完成后在 `reports/` 目录下生成 HTML 报告，浏览器打开即可查看。

如配置了企业微信通知，测试结束后会自动推送结果到群聊。

---

## 用例编写方式

框架支持两种用例编写模式：

### 模式一：YAML 数据驱动（推荐）

适用于标准 CRUD 接口、表单提交、列表查询。测试人员只需维护 YAML 文件，无需编写 Python 代码。

**步骤：**
1. 在 `datas/yaml_cases/` 创建 `<模块>_cases.yaml`
2. 在 `test_cases/` 创建对应的 `test_<模块>.py`（使用标准模板）

**YAML 用例格式：**

```yaml
# 正向用例：添加线索
add_clue:
  name: "添加线索"
  api: /api/admin/customer-clue/add
  method: post
  account: sale_account_1            # 使用哪个账号
  data:
    customer_name: "@company"        # 动态生成随机企业名
    business_license_code: "@license" # 动态生成随机信用代码
    phone: "@phone"                  # 动态生成随机手机号
    province: "@province"            # 动态生成联动省市区
    city: "@city"
    town: "@town"
    remark: "@remark"
    sale_user_id: "${sale_user_id}"  # 从会话上下文引用
  extract:
    clue_id: data.id                 # 从响应中提取值存入上下文
    clue_name: data.customer_name
  assert:
    - path: code
      operator: in
      expect: [200, 0]
    - path: data.id
      operator: not_null
  skip: false

# 逆向用例：缺少必填字段
add_clue_missing_name:
  name: "缺少客户名称"
  api: /api/admin/customer-clue/add
  method: post
  account: default
  data:
    # customer_name 不传
    business_license_code: "@license"
    remark: "@remark"
  assert:
    - path: message
      operator: contains
      expect: "不能为空"

# 依赖链：用上游返回的 ID 查询
query_clue_detail:
  name: "查询线索详情"
  api: /api/admin/customer-clue/get-one-clue
  method: get
  account: sale_account_1
  params:
    clue_id: "${clue_id}"            # 引用 add_clue 提取的 ID
  assert:
    - path: code
      operator: in
      expect: [200, 0]
```

**动态数据标签（@xxx）：**

| 标签 | 说明 | 示例输出 |
|------|------|----------|
| `@company` | 随机企业名 | `自动化测试企业_123456789` |
| `@company_short` | 短企业名 | `测试企123` |
| `@nickname` / `@name` | 随机昵称/联系人 | `测试联系人_4567123` |
| `@phone` | 随机手机号 | `13812345678` |
| `@license` | 随机信用代码（18位） | `91440100ABC1234567` |
| `@province` / `@city` / `@town` | 联动省市区 | `广东省` / `深圳市` / `南山区` |
| `@address` | 随机地址 | `测试地址_A栋12楼` |
| `@remark` | 带时间戳备注 | `自动化测试_20260515_093000` |
| `@now` / `@today` | 当前时间/日期 | `2026-05-15 09:30:00` |
| `@int` / `@int_100_500` | 随机数值 | `42` / `256` |
| `@email` | 随机邮箱 | `test_123456@example.com` |
| `@choice:a,b,c` | 随机选择 | `b` |
| `@random:N` | N位随机数字 | `384729` |
| `${key}` | 引用上下文中 extract 提取的值 | 实际值 |

**断言操作符：**

| 操作符 | 说明 | expect 示例 |
|--------|------|-------------|
| `eq` | 等于 | `200` |
| `ne` | 不等于 | `null` |
| `in` | 值在列表中 | `[200, 0]` |
| `not_in` | 值不在列表中 | `[200]` |
| `not_null` | 非空非null | 无需 expect |
| `contains` | 字符串包含 | `"成功"` |
| `gt` / `lt` / `gte` / `lte` | 大小比较 | `0` |

### 模式二：Python 编程模式

适用于复杂业务流程、多步骤联动、条件判断、数据唯一性验证等场景。

```python
import sys
import os
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from common.Log_packing import Log
from common.data_factory import ClueDataFactory

log = Log()


class TestAddClue:

    def test_add_success(self, login_client_factory, host):
        client, ctx = login_client_factory.get_client("sale_account_1")

        factory = ClueDataFactory(ctx)
        data = factory.build()

        url = host + "/api/admin/customer-clue/add"
        response = client.my_request(url, "post", data=data)

        assert response is not None
        assert response.status_code == 200
        resp_data = response.json()
        assert resp_data.get("code") in [200, 0], f"业务错误: {resp_data}"

    @pytest.mark.parametrize("missing", ["customer_name", "business_license_code"])
    def test_missing_required(self, logged_in_client, host, missing):
        factory = ClueDataFactory()
        data = factory.build_invalid(missing_fields=[missing])

        url = host + "/api/admin/customer-clue/add"
        response = logged_in_client.my_request(url, "post", data=data)

        assert response is not None
        resp_data = response.json()
        assert resp_data.get("code") not in [200, 0]
```

---

## 核心组件说明

### 会话上下文（SessionContext + DataExtractor）

解决接口业务依赖的核心组件。上游接口返回的数据（如 ID、token）可自动传递给下游接口。

```python
from common.session_context import SessionContext, DataExtractor

ctx = SessionContext()

ctx.set("token", "eyJhbGc...")
ctx.set("customer_id", 12345)

token = ctx.get("token")

data = {"customer_id": "${customer_id}"}
resolved = ctx.resolve(data)  # {"customer_id": "12345"}

extractor = DataExtractor(ctx)
extracted = extractor.extract(response, {
    "clue_id": "data.id",
    "token": "data.access_token",
})
```

### 动态数据工厂（DataFactory）

解决测试数据写死的问题，每次运行生成唯一值。

```python
from common.data_factory import DataFactory

factory = DataFactory(session_context)

data = factory.generate({
    "customer_name": "@company",
    "phone": "@phone",
    "province": "@province",
    "city": "@city",
    "town": "@town",
    "remark": "@remark",
    "sale_user_id": "${sale_user_id}",
})

from common.data_factory import ClueDataFactory
clue_factory = ClueDataFactory(ctx)
full_data = clue_factory.build()
minimal_data = clue_factory.build_minimal()
invalid_data = clue_factory.build_invalid(
    missing_fields=["customer_name"],
    empty_fields=["business_license_code"],
    wrong_type_fields={"phone": "not_a_phone"},
)
```

### 多账号管理（LoginClientFactory）

支持多个测试账号同时在线，每个账号独立登录、独立会话上下文。日志同时输出角色键名和实际用户名（如 `sale_account_1 (ca-zouxp)`）。

```python
def test_example(self, login_client_factory, host):
    sale1_client, sale1_ctx = login_client_factory.get_client("sale_account_1")
    asst_client, asst_ctx = login_client_factory.get_client("assistant_account")
    new_client, new_ctx = login_client_factory.get_client("sale_account_1", create_new=True)
```

**可用账号角色（config/users.yaml）：**

| 键名 | 角色 | 用途 |
|------|------|------|
| `default` | 默认 | 默认测试账号 |
| `sale_account_1` / `sale_account_2` | 销售 | 销售角色操作测试 |
| `assistant_account` | 助理 | 助理角色权限测试 |
| `admin_account` | 管理员 | 管理员权限测试 |
| `marketing_account` | 市场 | 市场部角色测试 |

### 环境切换（GetConfig）

通过 `config/test.ini` 的 `[env] active` 字段一键切换环境，无需改代码：

```python
from common.get_config import GetConfig

config = GetConfig()
print(config.get_active_env())     # "test"
print(config.get_host())           # "https://test-api.example.com"
print(config.list_available_envs()) # {"test": "...", "gray": "...", "prod": "..."}
```

### Pytest Fixtures

| Fixture | 作用域 | 说明 |
|---------|--------|------|
| `config` | session | 配置对象 (`GetConfig`) |
| `host` | session | 当前环境 host 地址 |
| `api_client` | session | 未登录的 HTTP 请求客户端 (`MyRequest`) |
| `logged_in_client` | session | 已登录的默认账号客户端 |
| `login_client_factory` | session | 多账号工厂，按角色获取客户端 |
| `session_context` | session | 全局会话上下文 |
| `data_extractor` | session | 响应数据提取器 |
| `data_factory` | session | 动态数据工厂 |
| `db_client` | session | 数据库客户端（需配置） |
| `report_client` | session | 报告收集 + 企业微信通知推送 |
| `smart_assert` | session | 语义断言引擎 |
| `self_healing` | session | 自愈引擎 |
| `root_cause_analyzer` | session | 根因分析引擎 |

---

## 企业微信通知

测试结束后自动推送结果到企业微信群机器人，支持三种消息类型：

### 消息类型

| 类型 | @成员方式 | 展示效果 | 适用场景 |
|------|-----------|----------|----------|
| `markdown` (默认) | `<@userid>` | 标题/加粗/颜色/引用 | 日常使用 |
| `text` | `mentioned_list` + `mentioned_mobile_list` | 纯文本 | 需要按手机号@人 |
| `template_card` | 不支持 | 卡片/高亮数据/信息列表 | 正式报告 |

### 配置方式

在 `config/test.ini` 的 `[notify]` 段配置，不配置则不推送：

```ini
[notify]
wecom_webhook=https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=你的key
wecom_msg_type=markdown
wecom_mentioned_list=zhangsan,lisi
wecom_mentioned_mobile=13800001111
```

### 推送效果

**markdown 类型：**
```
### CRM 接口自动化测试报告 全部通过
> 执行时间：2026-05-19 14:05:45
> 测试环境：test
> 总用例数：10 | 通过：6 | 失败：2 | 错误：0 | 跳过：2
> 通过率：60.00% | 耗时：7.55s
<@zhangsan> <@lisi>
```

**template_card 类型：** 展示为卡片样式，含关键数据高亮、水平信息列表、失败用例引用区域。

### 手动调用

```python
from mcp_servers.report_server import ReportMCPClient

report = ReportMCPClient(
    wecom_webhook="https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=xxx",
    wecom_mentioned_list=["zhangsan"],
    wecom_mentioned_mobile_list=["13800001111"],
)

report.collect_result("test_login", "pass", duration=0.5)
report.save_to_history()

# 推送 markdown 类型
report.notify_wecom(env_name="test", msg_type="markdown")

# 推送 text 类型 (支持手机号@)
report.notify_wecom(env_name="test", msg_type="text")

# 推送模板卡片类型
report.notify_wecom(env_name="test", msg_type="template_card")
```

---

## 支持的大模型

所有模型均通过 OpenAI 兼容协议统一接入，无需安装额外 SDK：

| 提供商 | Provider ID | 推荐模型 | 说明 |
|--------|------------|---------|------|
| **DeepSeek** | `deepseek` | `deepseek-chat` | 默认推荐，代码能力强 |
| **通义千问** | `qwen` | `qwen-plus` | 阿里云，性价比高 |
| **智谱** | `zhipu` | `glm-5` | 速度快成本低 |
| **Kimi** | `moonshot` | `moonshot-v1-8k` | 长上下文支持 |
| **豆包** | `doubao` | `doubao-pro-4k` | 字节跳动 |
| **腾讯混元** | `hunyuan` | `hunyuan-lite` | 有免费额度 |
| **硅基流动** | `siliconflow` | `Qwen/Qwen2.5-72B-Instruct` | 聚合平台 |
| **OpenAI** | `openai` | `gpt-4o` | 国际模型 |

---

## AI 能力使用

### LLM 客户端

```python
from ai.llm_client import LLMClient

client = LLMClient(provider="deepseek", api_key="sk-xxx")
result = client.chat([{"role": "user", "content": "帮我生成登录接口测试用例"}])
```

### 通过配置文件切换模型

```python
from ai.config import AIConfig

config = AIConfig()
config.switch_provider("qwen", model="qwen-max")
client = config.create_llm_client()
```

### AI 用例生成（YAML 模式，推荐）

从 ApiPost 接口元数据自动生成 YAML 用例 + Python 测试文件：

```python
from ai.case_generator import CaseGenerator

gen = CaseGenerator()

result = gen.generate_from_apipost_yaml(keyword="客户线索")
print(result["yaml_file"])  # datas/yaml_cases/customer_clue_cases.yaml
print(result["py_file"])    # test_cases/test_customer_clue.py
```

### AI 用例生成（Python 模式）

```python
from ai.case_generator import CaseGenerator

gen = CaseGenerator()

api_metadata = {
    "name": "登录接口",
    "method": "POST",
    "path": "/api/admin/login",
    "request": {"params": [{"name": "account", "required": True}]},
}

code = gen.generate(api_metadata)
gen.save_to_file(code, "test_login_generated.py")
```

### 语义断言

```python
from ai.smart_assert import SmartAssert

sa = SmartAssert()

passed, msg = sa.semantic_assert(response, "登录成功后应返回有效token和用户信息")
passed, diffs = sa.schema_assert(response, api_schema)
passed, missing = sa.structure_assert(response, ["code", "msg", "data"])
```

### Self-Healing 自愈

```python
from ai.self_healing import SelfHealingEngine

engine = SelfHealingEngine()
result = engine.analyze_failure("test_login", error_info, api_metadata, response)
print(result["healable"])
print(result["suggestion"])
```

### 根因分析

```python
from ai.root_cause import RootCauseAnalyzer

analyzer = RootCauseAnalyzer()
report = analyzer.analyze(failure_record)
reports = analyzer.batch_analyze(failure_records)
suggestion = analyzer.generate_regression_suggestion(reports)
```

---

## MCP 服务使用

### 数据库 MCP

```python
from mcp_servers.database_server import DatabaseMCPClient

db = DatabaseMCPClient(host="xxx", user="xxx", password="xxx", database="crm")
rows = db.query("SELECT * FROM users WHERE id = %s", [1])
schema = db.get_table_schema("users")
result = db.compare_data("users", {"id": 1}, {"status": "active"})
db.close()
```

### 报告 MCP

```python
from mcp_servers.report_server import ReportMCPClient

report = ReportMCPClient()
report.collect_result("test_login", "pass", duration=0.5)
print(report.get_summary())
report.save_to_history()
filepath = report.export_json_report()

# 企业微信推送 (需配置 webhook)
report.notify_wecom(env_name="test", msg_type="markdown")
```

---

## 框架设计要点

| 设计点 | 说明 |
|--------|------|
| **YAML 数据驱动** | 测试数据与代码分离，YAML 定义用例，Python 模板自动执行，降低维护成本 |
| **动态数据工厂** | `@xxx` 标签自动生成唯一测试数据（企业名/手机号/信用代码等），避免数据冲突 |
| **会话上下文** | `SessionContext` + `DataExtractor` 自动传递接口间依赖数据，支持 CRUD 完整流程 |
| **多账号角色** | `LoginClientFactory` 支持多角色账号并发登录，日志同时显示角色键名和实际用户名 |
| **一键环境切换** | `test.ini` 中 `active=test/gray/prod` 一行配置切换环境，无需改代码 |
| **配置分离** | 环境配置 `test.ini` + AI 配置 `ai_config.yaml` + 账号配置 `users.yaml` 独立管理 |
| **企业微信通知** | 测试结束自动推送结果，支持 markdown / text / 模板卡片三种消息类型 |
| **统一 LLM 接入** | 8 家国产大模型通过 OpenAI 兼容协议统一接入，配置切换即可换模型 |
| **AI 用例生成** | 接口元数据 → LLM 四维度分析（边界值/必填校验/依赖链/场景）→ 自动生成用例 |
| **语义断言** | AI 理解业务含义进行校验，不再硬编码 `assert code==200` |
| **Self-Healing** | 接口字段变更时自动检测 → AI 推荐修复方案 → 自动更新测试代码 |
| **MCP 协议** | ApiPost/数据库/报告均通过 MCP 标准化接口暴露，AI Agent 可直接调用 |
