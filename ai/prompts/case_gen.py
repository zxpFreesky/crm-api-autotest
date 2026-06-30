import json


def build_yaml_case_prompt(api_metadata, gen_config, existing_cases=None, business_rules=None):
    existing_section = ""
    if existing_cases:
        existing_section = f"""
## 已有测试用例 (参考数据格式, 避免重复)
{json.dumps(existing_cases, ensure_ascii=False, indent=2)}
"""

    rules_section = ""
    if business_rules:
        rules_section = f"""
## 业务规则
{json.dumps(business_rules, ensure_ascii=False, indent=2)}
"""

    enable_boundary = gen_config.get("enable_boundary", True)
    enable_negative = gen_config.get("enable_negative", True)

    boundary_section = ""
    if enable_boundary:
        boundary_section = """
### 维度三: 字段边界值
针对关键字段测试边界:
- 字符串: 最大长度、超长、特殊字符
- 数值型: 0、负数、超上限
- 枚举型: 非法枚举值
- 手机号: 少位、多位、非数字
- 信用代码: 非法格式
"""

    negative_section = ""
    if enable_negative:
        negative_section = """
### 维度二: 必填校验 (每个必填字段单独一条用例)
对每个必填字段分别生成:
- missing 用例: 整个字段不传(key 不存在)
- empty 用例: 字段传空字符串
原则: 每个必填字段至少一条缺失用例, 不要合并多个必填字段
"""

    return f"""你是一位专业的 CRM 接口测试工程师。请根据接口元数据，生成 YAML 格式的测试用例数据。

## 接口元数据
{json.dumps(api_metadata, ensure_ascii=False, indent=2)}
{existing_section}
{rules_section}

## YAML 用例格式规范
每个用例是一个顶层 key，格式如下:
```yaml
case_key:
  name: "用例名称"
  api: /api/path
  method: post
  account: sale_account_1
  data:
    field1: "固定值"
    field2: "@动态标签"
    field3: "${{上下文引用}}"
  params:
    page: "1"
  extract:
    context_key: json.path
  assert:
    - path: code
      operator: in
      expect: [200, 0]
  skip: false
```

## 动态数据标签
- @company: 随机企业名
- @nickname / @name: 随机昵称/联系人
- @phone: 随机手机号
- @license: 随机信用代码(18位)
- @province / @city / @town: 联动省市区
- @address: 随机地址
- @remark: 带时间戳备注
- @now / @today / @today_iso / @timestamp: 时间
- @int / @int_100_500 / @float_area: 随机数值
- @yes_no: 随机 0/1
- @email: 随机邮箱
- @uuid: 唯一ID
- @random:N: N位随机数字
- @choice:a,b,c: 随机选择
- @prefix_xxx: 带前缀唯一值
- ${{key}}: 引用上下文中 extract 提取的值

## 断言操作符
eq(等于) / ne(不等于) / in(值在列表中) / not_in(值不在列表中) / not_null(非空) / contains(包含) / gt / lt / gte / lte

## 可用账号
default / sale_account_1 / sale_account_2 / assistant_account / admin_account / marketing_account

## 测试设计要求 — 必须从四个维度系统性设计用例

### 维度一: 正向 + CRUD 业务依赖链
1. 创建用例(add_<entity>): 正常参数创建成功, extract 提取返回的 ID
2. 查询详情(query_<entity>_detail): 用 ${{entity_id}} 引用创建返回的 ID
3. 编辑更新(update_<entity>): 用 ${{entity_id}} 引用, 修改部分字段
4. 更新后查询(query_<entity>_after_update): 验证修改字段生效
5. 列表查询(query_<entity>_list): 分页参数, 验证返回结构
6. 删除(delete_<entity>): 用 ${{entity_id}} 引用
7. 删除后查询(query_<entity>_after_delete): 验证已不存在
{negative_section}
{boundary_section}
### 维度四: 场景测试
- 权限场景: 不同账号操作同一数据
- 重复操作: 唯一性字段重复创建
- 列表筛选: 组合筛选条件

## 输出要求
1. 只输出合法的 YAML 内容, 不要输出任何其他文字说明
2. 用例 key 命名: <操作>_<实体>[_<变体>], 如 add_customer / add_customer_missing_name
3. YAML 中所有字符串值必须用引号包裹
4. data 字段中的值, 字符串类型用引号, 数值类型不用引号
5. 不要重复已有用例已覆盖的场景
"""


def build_python_runner_template(module_name):
    class_name = "".join(word.capitalize() for word in module_name.split("_"))

    template = (
        "import sys\n"
        "import os\n"
        "import json\n"
        "import re\n"
        "import pytest\n"
        "import html as html_module\n"
        "\n"
        "sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))\n"
        "\n"
        "from common.Log_packing import Log\n"
        "from common.data_factory import DataFactory\n"
        "from common.yaml_runner import YamlCaseRunner\n"
        "from common.contants import yaml_cases_dir\n"
        "\n"
        "log = Log()\n"
        "\n"
        'YAML_FILE = os.path.join(yaml_cases_dir, "MODULE_cases.yaml")\n'
        "\n"
        "\n"
        "def _load_yaml_cases():\n"
        "    if not os.path.exists(YAML_FILE):\n"
        "        return []\n"
        "    cases = YamlCaseRunner.load_cases(YAML_FILE)\n"
        "    return [(k, v) for k, v in cases.items() if not v.get('skip', False)]\n"
        "\n"
        "\n"
        "_yaml_cases = _load_yaml_cases()\n"
        '_case_ids = [f"{k}: {v.get(\'name\', k)}" for k, v in _yaml_cases]\n'
        "\n"
        "\n"
        "def _resolve_data(data, ctx):\n"
        "    if not data:\n"
        "        return data\n"
        "    factory = DataFactory(ctx)\n"
        "    return factory.generate(data)\n"
        "\n"
        "\n"
        "def _resolve_params(params, ctx):\n"
        "    if not params:\n"
        "        return params\n"
        "    resolved = {}\n"
        "    for k, v in params.items():\n"
        '        if isinstance(v, str) and "${" in v:\n'
        r'            for m in re.findall(r"\$\{(\w+)\}", v):' + "\n"
        '                val = ctx.get(m, "")\n'
        '                v = v.replace(f"${{{m}}}", str(val))\n'
        "        resolved[k] = v\n"
        "    return resolved\n"
        "\n"
        "\n"
        "class TestCLASSNAMEDataDriven:\n"
        "\n"
        '    @pytest.mark.parametrize("case_key,case_def", _yaml_cases, ids=_case_ids)\n'
        "    def test_MODULE_case(self, case_key, case_def, login_client_factory, host):\n"
        '        name = case_def.get("name", case_key)\n'
        '        account = case_def.get("account") or "default"\n'
        "        client, ctx = login_client_factory.get_client(account)\n"
        "\n"
        '        api = case_def.get("api", "")\n'
        "        method = (case_def.get('method') or 'get').lower()\n"
        '        url = host.rstrip("/") + api\n'
        "\n"
        '        log.info(f"[{case_key}] 用例标题: {name}")\n'
        '        log.info(f"[{case_key}] 账号: {account} ({ctx.get(\'current_account\', \'?\')}), 请求: {method.upper()} {api}")\n'
        "\n"
        "        data = _resolve_data(case_def.get('data'), ctx)\n"
        "        params = _resolve_params(case_def.get('params'), ctx)\n"
        "\n"
        "        if data:\n"
        '            log.info(f"[{case_key}] 请求参数: {json.dumps(data, ensure_ascii=False)}")\n'
        "        if params:\n"
        '            log.info(f"[{case_key}] Query参数: {json.dumps(params, ensure_ascii=False)}")\n'
        "\n"
        "        extra_headers = {\n"
        '            "X-Request-Source": "pc",\n'
        '            "X-Request-Referer": "rmp",\n'
        '            "Accept": "application/json, text/plain, */*",\n'
        "        }\n"
        "\n"
        '        if method == "get":\n'
        "            if params:\n"
        '                query = "&".join(f"{k}={v}" for k, v in params.items())\n'
        '                url += ("&" if "?" in url else "?") + query\n'
        '            response = client.my_request(url, "get", headers=extra_headers)\n'
        '        elif method == "delete":\n'
        "            if params:\n"
        '                query = "&".join(f"{k}={v}" for k, v in params.items())\n'
        '                url += ("&" if "?" in url else "?") + query\n'
        '            response = client.my_request(url, "delete", headers=extra_headers)\n'
        "        else:\n"
        "            response = client.my_request(url, method, data=data, headers=extra_headers)\n"
        "\n"
        '        assert response is not None, f"[{case_key}] 请求失败，响应为空"\n'
        "\n"
        "        resp_data = {}\n"
        "        try:\n"
        "            resp_data = response.json()\n"
        "        except Exception:\n"
        "            raw_text = response.text[:500]\n"
        '            if raw_text.strip().startswith("<!DOCTYPE") or raw_text.strip().startswith("<html"):\n'
        r'                clean = re.sub(r"<[^>]+>", "", raw_text)' + "\n"
        r'                clean = re.sub(r"\s+", " ", clean).strip()[:200]' + "\n"
        '                resp_data = {"raw": f"[HTML响应已清理] {clean}"}\n'
        "            else:\n"
        '                resp_data = {"raw": raw_text}\n'
        "\n"
        '        log.info(f"[{case_key}] 实际响应: 状态码={response.status_code}, body={html_module.escape(json.dumps(resp_data, ensure_ascii=False)[:500])}")\n'
        "\n"
        "        extract = case_def.get('extract')\n"
        "        if extract:\n"
        "            from common.session_context import DataExtractor\n"
        "            extractor = DataExtractor(ctx)\n"
        "            extracted = extractor.extract(response, extract)\n"
        '            log.info(f"[{case_key}] 提取数据: {extracted}")\n'
        "\n"
        "        asserts = case_def.get('assert') or []\n"
        "        for assertion in asserts:\n"
        '            a_path = assertion.get("path", "")\n'
        '            a_op = assertion.get("operator", "eq")\n'
        '            a_expect = assertion.get("expect")\n'
        "\n"
        "            actual = YamlCaseRunner._get_by_path(resp_data, a_path)\n"
        "            passed = YamlCaseRunner._do_assert(actual, a_op, a_expect)\n"
        "\n"
        "            if passed:\n"
        '                log.info(f"[{case_key}] 断言通过: {a_path} {a_op} {a_expect}, 实际={actual}")\n'
        "            else:\n"
        '                log.error(f"[{case_key}] 断言失败: {a_path} {a_op} {a_expect}, 实际={actual}")\n'
        '            assert passed, f"{a_path} {a_op} {a_expect}, 实际={actual}"\n'
        "\n"
        "\n"
        'if __name__ == "__main__":\n'
        '    pytest.main([__file__, "-v", "-s"])\n'
    )

    return template.replace("MODULE", module_name).replace("CLASSNAME", class_name)


def build_case_gen_prompt(api_metadata, gen_config, existing_cases=None, business_rules=None):
    existing_section = ""
    if existing_cases:
        existing_section = f"""
## 已有测试用例 (来自 Excel 测试数据, 请参考这些数据的格式和业务场景)
{json.dumps(existing_cases, ensure_ascii=False, indent=2)}
"""

    rules_section = ""
    if business_rules:
        rules_section = f"""
## 业务规则
{json.dumps(business_rules, ensure_ascii=False, indent=2)}
"""

    return f"""你是一位专业的 CRM 接口测试工程师。请根据接口元数据生成 pytest 测试代码。

## 接口元数据
{json.dumps(api_metadata, ensure_ascii=False, indent=2)}
{existing_section}
{rules_section}
## 生成要求
1. 使用 pytest 框架, 类名 TestXxx, 方法名 test_xxx
2. 使用 pytest.mark.parametrize 进行参数化
3. 包含正向测试用例
4. 使用 requests.Session 发送请求
5. 使用 assert 进行断言
6. 添加清晰的 docstring
7. 请求参数要基于已有用例的数据格式, 保持一致
8. 如果有业务规则, 必须覆盖业务规则中的约束条件

## 输出格式
请只输出 Python 代码, 不要输出其他内容。
"""


def build_negative_case_prompt(api_metadata, gen_config, existing_cases=None, business_rules=None):
    existing_section = ""
    if existing_cases:
        existing_section = f"""
## 已有测试用例 (参考数据格式, 避免重复)
{json.dumps(existing_cases, ensure_ascii=False, indent=2)}
"""

    rules_section = ""
    if business_rules:
        rules_section = f"""
## 业务规则 (需要验证这些规则是否被正确校验)
{json.dumps(business_rules, ensure_ascii=False, indent=2)}
"""

    return f"""你是一位专业的 CRM API 安全测试工程师。请根据接口元数据生成异常/逆向测试用例。

## 接口元数据
{json.dumps(api_metadata, ensure_ascii=False, indent=2)}
{existing_section}
{rules_section}
## 生成要求
1. 使用 pytest 框架
2. 生成以下类型的异常测试:
   - 必填字段为空
   - 字段类型错误
   - 边界值测试 (最大长度/最小值)
   - SQL 注入测试
   - XSS 注入测试
   - 越权访问测试 (如适用)
   - 业务规则违反测试 (如有业务规则)
3. 每个用例使用 @pytest.mark.parametrize
4. 添加清晰的 docstring 说明测试目的
5. 不要重复已有用例已覆盖的场景
6. 请求参数格式要与已有用例保持一致

## 输出格式
请只输出 Python 代码, 不要输出其他内容。
"""
