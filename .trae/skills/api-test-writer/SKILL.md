---
name: "api-test-writer"
description: "根据项目框架规范，编写CRM接口自动化测试用例。当用户需要创建新的接口测试、添加测试用例、编写YAML/Python测试脚本时调用。"
---

# CRM 接口自动化测试编写指南

你是一位专业的 CRM 接口测试工程师。根据项目框架规范编写接口自动化测试用例。

## 项目结构

```
auto_api_rmp_new/
├── config/                # 配置
│   ├── test.ini           # 环境地址、数据库等
│   └── users.yaml         # 多账号角色配置
├── common/                # 核心库
│   ├── RequestDemo.py     # MyRequest（requests.Session 封装）
│   ├── session_context.py # SessionContext + DataExtractor（依赖链）
│   ├── data_factory.py    # DataFactory（动态数据生成 @xxx, ${xxx}）
│   ├── yaml_runner.py     # YamlCaseRunner（YAML 驱动执行引擎）
│   ├── contants.py        # 路径常量
│   └── get_config.py      # 配置读取
├── datas/yaml_cases/      # YAML 测试数据（一个模块一个文件）
├── test_cases/            # Python 测试文件（pytest）
├── conftest.py            # pytest fixtures
└── run.py                 # 测试运行入口
```

---

## 一、编写模式

### 模式一：YAML 数据驱动（推荐）

适用于：标准 CRUD 接口、表单提交、列表查询等。测试人员只需维护 YAML 文件。

**步骤：**
1. 在 `datas/yaml_cases/` 创建 `<模块>_cases.yaml`
2. 在 `test_cases/` 创建对应的 `test_<模块>.py`

### 模式二：Python 编程模式

适用于：复杂业务流程、多步骤联动、条件判断、数据唯一性验证等。

**步骤：**
1. 在 `test_cases/` 直接编写 `test_<模块>.py`

---

## 二、YAML 用例格式

```yaml
case_key:
  name: "用例名称"
  api: /api/path
  method: post
  account: sale_account_1
  data:
    field1: "固定值"
    field2: "@动态标签"
    field3: "${上下文引用}"
  params:
    page: "1"
    keyword: "${keyword}"
  extract:
    context_key: json.path
  assert:
    - path: code
      operator: in
      expect: [200, 0]
  skip: false
```

### 动态数据标签

| 标签 | 说明 |
|------|------|
| `@company` | 随机企业名 |
| `@company_short` | 短企业名 |
| `@nickname` / `@name` | 随机昵称/联系人 |
| `@phone` | 随机手机号 |
| `@license` | 随机信用代码（18位） |
| `@province` / `@city` / `@town` | 联动省市区 |
| `@address` | 随机地址 |
| `@remark` | 带时间戳备注 |
| `@now` / `@today` / `@today_iso` / `@timestamp` | 时间相关 |
| `@int` / `@int_100_500` / `@float_area` | 随机数值 |
| `@yes_no` | 随机 0/1 |
| `@email` | 随机邮箱 |
| `@uuid` | 唯一ID |
| `@random:N` | N位随机数字 |
| `@choice:a,b,c` | 随机选择 |
| `@prefix_xxx` | 带前缀唯一值 |
| `${key}` | 引用上下文中 extract 提取的值 |

### 断言操作符

| 操作符 | 说明 | expect 示例 |
|--------|------|-------------|
| `eq` | 等于 | `200` |
| `ne` | 不等于 | `null` |
| `in` | 值在列表中 | `[200, 0]` |
| `not_in` | 值不在列表中 | `[200]` |
| `not_null` | 非空非null | 无需 expect |
| `contains` | 字符串包含 | `"成功"` |
| `gt` / `lt` / `gte` / `lte` | 大小比较 | `0` |

### 可用账号

| 键名 | 角色 |
|------|------|
| `default` | 默认账号 |
| `sale_account_1` / `sale_account_2` | 销售 |
| `assistant_account` | 助理 |
| `admin_account` | 管理员 |
| `marketing_account` | 市场 |

---

## 三、测试设计维度（核心）

编写接口测试时，**必须从以下四个维度系统性设计用例**：

### 维度一：字段边界值测试

针对每个字段的数据类型和业务约束，测试其边界情况：

| 字段类型 | 边界测试项 |
|----------|------------|
| 字符串 | 最小长度（1字符）、最大长度（达到字段上限）、空字符串、超长字符串、特殊字符（`<script>`、SQL注入、emoji）、前后空格 |
| 数值型 | 最小值、最大值、0、负数、超上限、小数位、非数字字符串 |
| 枚举型 | 每个合法枚举值逐一测试、非法枚举值、空值、大小写混用 |
| 日期型 | 过去日期、当天、未来日期、跨年、非法格式（2026-13-32）、空值 |
| 数组/列表 | 空数组 `[]`、单元素、大量元素、重复元素、null |
| 手机号 | 11位正常号、少位、多位、非数字、境外号码格式、全0、全1 |
| 信用代码 | 标准18位、少位、多位、含特殊字符、全0、已存在的代码（唯一性冲突） |

**YAML 示例：**

```yaml
# 字符串最大长度边界
add_<entity>_name_max_length:
  name: "名称达到最大长度"
  data:
    name: "@prefix_xxx<填满最大长度的值>"
  assert:
    - path: code
      operator: in
      expect: [200, 0]

# 数值超上限
add_<entity>_num_exceed:
  name: "数值超过最大限制"
  data:
    num_field: "999999999"
  assert:
    - path: code
      operator: not_in
      expect: [200]

# 枚举值非法
add_<entity>_invalid_enum:
  name: "枚举字段传入非法值"
  data:
    status: "INVALID_STATUS"
  assert:
    - path: code
      operator: not_in
      expect: [200]
```

### 维度二：必填校验测试

针对每个必填字段逐一验证：

| 测试场景 | 做法 |
|----------|------|
| 缺少字段 | 整个字段不传（key 不存在） |
| 字段为空 | 传 `""` 空字符串 |
| 字段为 null | 传 `null`（视接口而定） |
| 字段为纯空格 | 传 `"   "` |

**设计原则：**
- **每个必填字段至少一条缺失用例**，不要合并多个必填字段在一条用例中（无法定位是哪个字段导致的）
- 断言验证错误信息是否明确（如 `message contains "不能为空"`）

**YAML 示例：**

```yaml
# 缺少必填字段 A
add_<entity>_missing_fieldA:
  name: "缺少必填字段-fieldA"
  data:
    # fieldA 整个不传
    fieldB: "@xxx"
    fieldC: "@xxx"
  assert:
    - path: message
      operator: contains
      expect: "fieldA"

# 必填字段 B 传空
add_<entity>_empty_fieldB:
  name: "必填字段fieldB为空"
  data:
    fieldA: "@xxx"
    fieldB: ""
    fieldC: "@xxx"
  assert:
    - path: code
      operator: not_in
      expect: [200]
```

### 维度三：业务依赖链测试

模拟真实业务流程，测试接口之间的数据传递和状态流转：

| 依赖类型 | 说明 | 示例 |
|----------|------|------|
| 数据依赖 | 下游接口需要上游接口返回的 ID | 创建 → 用创建返回的ID查询 |
| 状态依赖 | 接口改变数据状态，下游依赖新状态 | 审批通过 → 才能执行下一步 |
| 权限依赖 | 不同角色看到不同数据/执行不同操作 | 销售创建 → 助理不可见/不可改 |
| 顺序依赖 | 必须按固定顺序调用 | 先添加 → 再编辑 → 再删除 |

**CRUD 完整流程模式（推荐用例编写顺序）：**

```yaml
# 第1步：创建（提取ID给后续用例）
add_<entity>:
  method: post
  extract:
    <entity>_id: data.id
  assert:
    - path: code
      operator: in
      expect: [200, 0]
    - path: data.id
      operator: not_null

# 第2步：查询详情（使用创建返回的ID）
query_<entity>_detail:
  method: get
  params:
    id: "${<entity>_id}"
  assert:
    - path: code
      operator: in
      expect: [200, 0]
    - path: data.id
      operator: eq
      expect: "${<entity>_id}"

# 第3步：编辑更新
update_<entity>:
  method: put
  data:
    id: "${<entity>_id}"
    # 修改部分字段
  assert:
    - path: code
      operator: in
      expect: [200, 0]

# 第4步：再次查询验证修改生效
query_<entity>_after_update:
  method: get
  params:
    id: "${<entity>_id}"
  assert:
    - path: data.<修改的字段>
      operator: eq
      expect: "<新值>"

# 第5步：删除
delete_<entity>:
  method: delete
  params:
    id: "${<entity>_id}"
  assert:
    - path: code
      operator: in
      expect: [200, 0]

# 第6步：删除后查询验证已不存在
query_<entity>_after_delete:
  method: get
  params:
    id: "${<entity>_id}"
  assert:
    - path: code
      operator: not_in
      expect: [200, 0]
```

**跨模块业务依赖链：**

```yaml
# 模块A → 模块B → 模块C 的真实业务流程
# 例：创建线索 → 转客户 → 创建联系人 → 创建商机

step1_add_clue:
  extract:
    clue_id: data.id

step2_clue_to_customer:
  data:
    clue_id: "${clue_id}"
  extract:
    customer_id: data.customer_id

step3_add_contact:
  data:
    customer_id: "${customer_id}"
  extract:
    contact_id: data.id

step4_add_opportunity:
  data:
    customer_id: "${customer_id}"
    contact_id: "${contact_id}"
```

### 维度四：场景测试

模拟真实用户操作场景和异常场景：

| 场景类型 | 测试要点 | 示例 |
|----------|----------|------|
| 正向场景 | 标准业务流程走通 | 正常创建 → 正常查询 → 正常删除 |
| 权限场景 | 不同角色的数据隔离和操作权限 | 销售A看不到销售B的数据；助理不能删除 |
| 重复操作 | 重复提交、重复创建 | 同一信用代码二次创建应报错 |
| 并发冲突 | 同时操作同一条数据 | 两人同时编辑同一记录 |
| 数据状态 | 不同状态下操作 | 已删除的记录不能再次删除；已关闭的不能编辑 |
| 异常恢复 | 上游失败后下游的容错 | 创建失败时不应产生脏数据 |
| 列表筛选 | 各种筛选条件组合 | 按状态、按日期范围、按关键字、组合筛选 |
| 分页场景 | 首页、末页、超出范围、每页条数变化 | page=0、page=-1、page_rows=0、page_rows=9999 |

**YAML 示例：**

```yaml
# 权限场景：A账号创建的数据，B账号不可见
add_by_accountA:
  account: sale_account_1
  extract:
    entity_id: data.id

query_by_accountB_not_visible:
  name: "B账号查询A账号数据-应不可见"
  account: sale_account_2
  params:
    id: "${entity_id}"
  assert:
    - path: code
      operator: not_in
      expect: [200, 0]

# 重复操作：重复创建应失败
add_duplicate:
  name: "重复创建-唯一性校验"
  data:
    business_license_code: "<已存在的信用代码>"
  assert:
    - path: code
      operator: not_in
      expect: [200]

# 列表筛选组合
query_list_with_filter:
  name: "组合筛选查询"
  method: get
  params:
    page: "1"
    page_rows: "10"
    status: "1"
    keyword: "@company"
    start_date: "@today"
    end_date: "@today"
  assert:
    - path: code
      operator: in
      expect: [200, 0]
    - path: data.list
      operator: not_null
```

---

## 四、Python 测试文件模板（YAML 驱动）

每个 YAML 数据文件对应一个 Python 测试文件，放在 `test_cases/test_<模块>.py`：

```python
import sys
import os
import json
import re
import pytest
import html as html_module

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from common.Log_packing import Log
from common.data_factory import DataFactory
from common.yaml_runner import YamlCaseRunner
from common.contants import yaml_cases_dir

log = Log()

YAML_FILE = os.path.join(yaml_cases_dir, "<模块>_cases.yaml")


def _load_yaml_cases():
    if not os.path.exists(YAML_FILE):
        return []
    cases = YamlCaseRunner.load_cases(YAML_FILE)
    return [(k, v) for k, v in cases.items() if not v.get("skip", False)]


_yaml_cases = _load_yaml_cases()
_case_ids = [f"{k}: {v.get('name', k)}" for k, v in _yaml_cases]


def _resolve_data(data, ctx):
    if not data:
        return data
    factory = DataFactory(ctx)
    return factory.generate(data)


def _resolve_params(params, ctx):
    if not params:
        return params
    resolved = {}
    for k, v in params.items():
        if isinstance(v, str) and "${" in v:
            for m in re.findall(r"\$\{(\w+)\}", v):
                val = ctx.get(m, "")
                v = v.replace(f"${{{m}}}", str(val))
        resolved[k] = v
    return resolved


class Test<Module>DataDriven:

    @pytest.mark.parametrize("case_key,case_def", _yaml_cases, ids=_case_ids)
    def test_<module>_case(self, case_key, case_def, login_client_factory, host):
        name = case_def.get("name", case_key)
        account = case_def.get("account") or "default"
        client, ctx = login_client_factory.get_client(account)

        api = case_def.get("api", "")
        method = (case_def.get("method") or "get").lower()
        url = host.rstrip("/") + api

        log.info(f"[{case_key}] 用例标题: {name}")
        log.info(f"[{case_key}] 账号: {account}, 请求: {method.upper()} {api}")

        data = _resolve_data(case_def.get("data"), ctx)
        params = _resolve_params(case_def.get("params"), ctx)

        if data:
            log.info(f"[{case_key}] 请求参数: {json.dumps(data, ensure_ascii=False)}")
        if params:
            log.info(f"[{case_key}] Query参数: {json.dumps(params, ensure_ascii=False)}")

        extra_headers = {
            "X-Request-Source": "pc",
            "X-Request-Referer": "rmp",
            "Accept": "application/json, text/plain, */*",
        }

        if method == "get":
            if params:
                query = "&".join(f"{k}={v}" for k, v in params.items())
                url += ("&" if "?" in url else "?") + query
            response = client.my_request(url, "get", headers=extra_headers)
        elif method == "delete":
            if params:
                query = "&".join(f"{k}={v}" for k, v in params.items())
                url += ("&" if "?" in url else "?") + query
            response = client.my_request(url, "delete", headers=extra_headers)
        else:
            response = client.my_request(url, method, data=data, headers=extra_headers)

        assert response is not None, f"[{case_key}] 请求失败，响应为空"

        resp_data = {}
        try:
            resp_data = response.json()
        except Exception:
            raw_text = response.text[:500]
            if raw_text.strip().startswith("<!DOCTYPE") or raw_text.strip().startswith("<html"):
                clean = re.sub(r"<[^>]+>", "", raw_text)
                clean = re.sub(r"\s+", " ", clean).strip()[:200]
                resp_data = {"raw": f"[HTML响应已清理] {clean}"}
            else:
                resp_data = {"raw": raw_text}

        log.info(f"[{case_key}] 实际响应: 状态码={response.status_code}, body={html_module.escape(json.dumps(resp_data, ensure_ascii=False)[:500])}")

        extract = case_def.get("extract")
        if extract:
            from common.session_context import DataExtractor
            extractor = DataExtractor(ctx)
            extracted = extractor.extract(response, extract)
            log.info(f"[{case_key}] 提取数据: {extracted}")

        asserts = case_def.get("assert") or []
        for assertion in asserts:
            a_path = assertion.get("path", "")
            a_op = assertion.get("operator", "eq")
            a_expect = assertion.get("expect")

            actual = YamlCaseRunner._get_by_path(resp_data, a_path)
            passed = YamlCaseRunner._do_assert(actual, a_op, a_expect)

            if passed:
                log.info(f"[{case_key}] 断言通过: {a_path} {a_op} {a_expect}, 实际={actual}")
            else:
                log.error(f"[{case_key}] 断言失败: {a_path} {a_op} {a_expect}, 实际={actual}")
            assert passed, f"{a_path} {a_op} {a_expect}, 实际={actual}"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
```

---

## 五、Pytest Fixtures 速查

| Fixture | 作用域 | 用途 |
|---------|--------|------|
| `config` | session | GetConfig 实例 |
| `host` | session | 接口基础地址 |
| `api_client` | session | 未登录的请求客户端 |
| `logged_in_client` | session | 已登录的默认账号客户端 |
| `login_client_factory` | session | 多账号工厂，`get_client("角色键名")` 获取指定账号 |
| `session_context` | session | 全局会话上下文 |
| `data_extractor` | session | 响应数据提取器 |
| `data_factory` | session | 动态数据工厂 |
| `db_client` | session | 数据库客户端（如已配置） |
| `smart_assert` | session | AI 智能断言 |
| `self_healing` | session | 自修复引擎 |
| `root_cause_analyzer` | session | 根因分析 |

---

## 六、编写规范

### 命名约定

| 对象 | 格式 | 示例 |
|------|------|------|
| YAML 文件 | `<模块>_cases.yaml` | `customer_cases.yaml` |
| Python 文件 | `test_<模块>.py` | `test_customer.py` |
| 用例 key | `<操作>_<实体>[_<变体>]` | `add_customer`、`add_customer_missing_name` |
| 测试类（YAML驱动） | `Test<模块>DataDriven` | `TestCustomerDataDriven` |
| 测试类（编程模式） | `Test<功能>` | `TestCustomerFlow` |

### 通用规则

- 不写注释，除非用户明确要求
- 严格遵循已有文件的代码风格
- 需要登录的接口用 `login_client_factory`，默认账号用 `logged_in_client`
- 始终先 `assert response is not None`，再解析响应
- `response.json()` 外层加 try/except 防止非JSON响应
- 日志用 `log.info()` / `log.error()`，不用 `print()`
- YAML 中 `data` 字段写了什么就发什么，不做模板合并
- 运行命令：`python run.py --all` 或 `python run.py --file test_<模块>.py`

### 用例编写检查清单

编写任何接口测试时，按此清单逐项确认覆盖：

- [ ] **正向用例**：正常参数能否成功（code in [200, 0]）
- [ ] **必填校验**：每个必填字段是否逐一验证缺失/空值
- [ ] **边界值**：关键字段是否测试了长度、范围、格式边界
- [ ] **业务依赖链**：CRUD 完整流程是否走通（创建→查询→修改→删除）
- [ ] **权限场景**：不同角色操作是否正确隔离
- [ ] **异常场景**：重复操作、非法状态、无效数据是否处理
- [ ] **数据提取**：extract 是否正确传递给下游用例
- [ ] **断言完整**：是否同时验证了状态码和业务字段
