import json
import re
import os

from .config import AIConfig
from .llm_client import LLMClient
from .prompts.analysis import build_healing_prompt


class SelfHealingEngine:
    """
    Self-Healing 自愈引擎 — 自动检测并修复测试用例失败
    
    核心能力:
    1. 失败原因分类: 自动识别错误类型（字段变更、响应结构变化、状态码变化等）
    2. 可自愈判断: 判断失败是否可自动修复
    3. AI 修复建议: 调用 LLM 获取修复方案
    4. 自动修复: 自动更新测试代码（需配置 auto_fix: true）
    
    使用方式:
        engine = SelfHealingEngine()
        
        # 分析失败原因
        result = engine.analyze_failure("test_login", error_info, api_metadata, response)
        print(result["healable"])    # 是否可自愈
        print(result["suggestion"])  # AI 修复建议
        
        # 自动修复
        engine.auto_fix("case/test_login.py", result)
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
        self.healing_config = self.config.self_healing_config
        self._healing_log = []

    def analyze_failure(self, test_name, error_info, api_metadata=None, response=None):
        analysis = {
            "test_name": test_name,
            "error_info": str(error_info),
            "root_cause": self._classify_error(error_info),
            "healable": False,
            "suggestion": None,
            "fix_code": None,
        }

        cause = analysis["root_cause"]

        if cause in ("field_name_changed", "field_added", "field_removed"):
            analysis["healable"] = True
            if self.apipost_client and api_metadata:
                changes = self.apipost_client.detect_api_changes(
                    api_metadata.get("id"), api_metadata.get("baseline")
                )
                analysis["detected_changes"] = changes

        if cause in ("response_structure_changed", "status_code_changed"):
            analysis["healable"] = True

        if analysis["healable"] and self.llm_client:
            suggestion = self._get_ai_suggestion(error_info, api_metadata, response)
            analysis["suggestion"] = suggestion.get("suggestion", "")
            analysis["fix_code"] = suggestion.get("fix_code", "")

        self._healing_log.append(analysis)
        return analysis

    def auto_fix(self, test_file, analysis_result):
        if not self.healing_config.get("auto_fix", False):
            return False

        if not analysis_result.get("healable"):
            return False

        fix_code = analysis_result.get("fix_code")
        if not fix_code:
            return False

        try:
            with open(test_file, "r", encoding="utf-8") as f:
                content = f.read()

            old_field = self._extract_old_field(analysis_result["error_info"])
            new_field = self._extract_new_field(fix_code)

            if old_field and new_field:
                content = content.replace(old_field, new_field)
                with open(test_file, "w", encoding="utf-8") as f:
                    f.write(content)
                return True
        except Exception:
            return False

        return False

    def get_healing_log(self):
        return self._healing_log

    def _classify_error(self, error_info):
        error_str = str(error_info).lower()

        if "keyerror" in error_str or "attributeerror" in error_str:
            return "field_name_changed"
        if "assertionerror" in error_str or "assert" in error_str:
            if "status" in error_str:
                return "status_code_changed"
            return "assertion_failed"
        if "timeout" in error_str:
            return "timeout"
        if "connection" in error_str:
            return "connection_error"
        if "json" in error_str and "decode" in error_str:
            return "response_structure_changed"
        if "typeerror" in error_str:
            return "type_mismatch"

        return "unknown"

    def _get_ai_suggestion(self, error_info, api_metadata, response):
        if self.llm_client is None:
            return {"suggestion": "请配置 LLM 以获取修复建议", "fix_code": ""}

        prompt = build_healing_prompt(error_info, api_metadata, response)
        try:
            if isinstance(self.llm_client, LLMClient):
                content = self.llm_client.chat(
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.2,
                    max_tokens=2048,
                )
            else:
                result = self.llm_client.chat.completions.create(
                    model=self.config.get("llm.model", "deepseek-chat"),
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.2,
                    max_tokens=2048,
                )
                content = result.choices[0].message.content
            return {"suggestion": content, "fix_code": ""}
        except Exception as e:
            return {"suggestion": f"AI 分析失败: {e}", "fix_code": ""}

    @staticmethod
    def _extract_old_field(error_info):
        match = re.search(r"KeyError\(['\"](\w+)['\"]\)", str(error_info))
        return match.group(1) if match else None

    @staticmethod
    def _extract_new_field(fix_code):
        match = re.search(r"['\"](\w+)['\"]", str(fix_code))
        return match.group(1) if match else None
