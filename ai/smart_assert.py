import json
import re

from .config import AIConfig
from .llm_client import LLMClient
from .prompts.assert_gen import build_assert_prompt


class SmartAssert:
    """
    语义断言引擎 — AI 驱动的智能断言组件
    
    核心能力:
    1. 语义断言: 用自然语言描述期望行为，AI 自动判断响应是否符合预期
    2. Schema 断言: 对比响应结构与接口文档定义的字段
    3. 结构断言: 验证响应是否包含必需的字段
    
    使用方式:
        sa = SmartAssert()
        
        # AI 语义断言
        passed, msg = sa.semantic_assert(response, "登录成功后应返回有效token和用户信息")
        
        # Schema 断言
        passed, diffs = sa.schema_assert(response, api_schema)
        
        # 结构断言
        passed, missing = sa.structure_assert(response, ["code", "msg", "data"])
    """

    def __init__(self, config=None, llm_client=None, apipost_client=None):
        self.config = config or AIConfig()
        if llm_client is None:
            if self.config.get("llm.api_key"):
                self.llm_client = self.config.create_llm_client()
            else:
                self.llm_client = None
        else:
            self.llm_client = llm_client
        self.apipost_client = apipost_client

    def semantic_assert(self, response, description):
        resp_data = self._extract_response_data(response)

        if self.llm_client is None:
            return self._rule_based_assert(resp_data, description)

        prompt = build_assert_prompt(resp_data, description)
        try:
            if isinstance(self.llm_client, LLMClient):
                answer = self.llm_client.chat(
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.1,
                    max_tokens=1024,
                )
            else:
                result = self.llm_client.chat.completions.create(
                    model=self.config.get("llm.model", "deepseek-chat"),
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.1,
                    max_tokens=1024,
                )
                answer = result.choices[0].message.content
            passed = "PASS" in answer.upper() or "通过" in answer
            return passed, answer
        except Exception as e:
            return False, f"LLM 断言失败: {e}"

    def schema_assert(self, response, api_schema):
        resp_data = self._extract_response_data(response)
        if isinstance(resp_data, str):
            try:
                resp_data = json.loads(resp_data)
            except (json.JSONDecodeError, TypeError):
                return False, {"error": "响应不是有效 JSON"}

        expected_fields = {}
        if api_schema and "response" in api_schema:
            for field in api_schema["response"].get("fields", []):
                expected_fields[field["name"]] = field

        differences = []
        for name, field_def in expected_fields.items():
            if field_def.get("required", False) and name not in resp_data:
                differences.append({
                    "type": "missing_required_field",
                    "field": name,
                    "expected_type": field_def.get("type", "unknown"),
                })

        for key in resp_data:
            if key not in expected_fields:
                differences.append({
                    "type": "unexpected_field",
                    "field": key,
                    "actual_value": resp_data[key],
                })

        return len(differences) == 0, differences

    def structure_assert(self, response, required_fields=None):
        resp_data = self._extract_response_data(response)
        if isinstance(resp_data, str):
            try:
                resp_data = json.loads(resp_data)
            except (json.JSONDecodeError, TypeError):
                return False, {"error": "响应不是有效 JSON"}

        if required_fields is None:
            required_fields = ["code", "msg"]

        missing = []
        for field in required_fields:
            if field not in resp_data:
                missing.append(field)

        return len(missing) == 0, missing

    @staticmethod
    def _extract_response_data(response):
        if hasattr(response, "json"):
            try:
                return response.json()
            except Exception:
                return response.text if hasattr(response, "text") else str(response)
        return response

    @staticmethod
    def _rule_based_assert(resp_data, description):
        if isinstance(resp_data, str):
            try:
                resp_data = json.loads(resp_data)
            except (json.JSONDecodeError, TypeError):
                return False, "响应不是有效 JSON"

        checks = []

        if "成功" in description or "success" in description.lower():
            code = resp_data.get("code")
            if code is not None:
                if str(code) in ("200", "0", "1"):
                    checks.append(("code 检查", True))
                else:
                    checks.append((f"code={code}, 期望成功", False))

        if "token" in description.lower():
            data = resp_data.get("data", {})
            token_keys = [k for k in data.keys() if "token" in k.lower()]
            if token_keys:
                token_value = data[token_keys[0]]
                if token_value:
                    checks.append((f"token 字段 {token_keys[0]} 存在且非空", True))
                else:
                    checks.append((f"token 字段 {token_keys[0]} 为空", False))
            else:
                checks.append(("未找到 token 相关字段", False))

        if "用户信息" in description or "user" in description.lower():
            data = resp_data.get("data", {})
            user_keys = [k for k in data.keys() if "user" in k.lower() or "info" in k.lower()]
            if user_keys:
                checks.append(("用户信息字段存在", True))
            else:
                checks.append(("未找到用户信息相关字段", False))

        all_passed = all(c[1] for c in checks)
        message = "\n".join([f"[{'✓' if p else '✗'}] {n}" for n, p in checks])
        return all_passed, message
