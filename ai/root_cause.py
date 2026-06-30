import json
import re
import os
from datetime import datetime

from .config import AIConfig
from .llm_client import LLMClient
from .prompts.analysis import build_root_cause_prompt


class RootCauseAnalyzer:
    """
    结构化诊断引擎 — 分析测试失败原因，提供可操作的诊断信息

    核心思路:
    不做"猜测性分析"，而是提供结构化诊断数据，帮助测试工程师快速定位问题:
    1. 失败分类: 基于实际响应数据分类（不是 traceback 关键字）
    2. 请求/响应快照: 展示实际发送了什么、服务端返回了什么
    3. 断言对比: 期望值 vs 实际值的精确对比
    4. 历史对比: 这个用例上次是否通过（需要历史数据）
    5. AI 分析: 有 LLM 时调用，没有时不输出废话

    使用方式:
        analyzer = RootCauseAnalyzer()

        # 传入结构化失败数据（report_client 收集的）
        report = analyzer.diagnose(failure_record)

        # 批量诊断
        reports = analyzer.batch_diagnose(failure_records)

        # 生成诊断摘要（用于日志/通知）
        summary = analyzer.format_diagnosis_summary(reports)
    """

    def __init__(self, config=None, llm_client=None, db_client=None, apipost_client=None):
        self.config = config or AIConfig()
        if llm_client is None:
            if self.config.get("llm.api_key"):
                self.llm_client = self.config.create_llm_client()
            else:
                self.llm_client = None
        else:
            self.llm_client = llm_client
        self.db_client = db_client
        self.apipost_client = apipost_client
        self._history_dir = os.path.join(
            os.path.dirname(os.path.dirname(__file__)), "reports"
        )

    def diagnose(self, failure_record, context=None):
        """
        结构化诊断单条失败用例

        :param failure_record: report_client.collect_result() 收集的失败记录
            必须包含: test_name, status, error_msg
            建议包含: request_info, response
        :return: 诊断结果 dict
        """
        test_name = failure_record.get("test_name", "unknown")
        error_msg = failure_record.get("error_msg", "")

        category = self._classify_from_error(error_msg)

        diagnosis = {
            "test_name": test_name,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "category": category,
            "category_label": self._category_label(category),
            "risk_level": self._assess_risk(category),
            "assertion_detail": self._extract_assertion_detail(error_msg),
            "request_snapshot": self._extract_request_snapshot(failure_record),
            "response_snapshot": self._extract_response_snapshot(failure_record),
            "suggestion": self._generate_suggestion(category, error_msg),
            "history_status": self._check_history(test_name),
        }

        if self.llm_client and category in ("assertion_failure", "interface_changed", "server_error"):
            diagnosis["ai_analysis"] = self._get_ai_analysis(failure_record, diagnosis)

        return diagnosis

    def batch_diagnose(self, failure_records, context=None):
        results = []
        for record in failure_records:
            results.append(self.diagnose(record, context))
        return results

    def format_diagnosis_summary(self, diagnosis_results):
        """
        格式化诊断摘要，用于日志和企业微信通知

        :param diagnosis_results: batch_diagnose() 的返回值
        :return: 格式化的摘要文本
        """
        if not diagnosis_results:
            return ""

        lines = []
        for d in diagnosis_results:
            lines.append(f"**{d['test_name']}**")
            lines.append(f"  分类: {d['category_label']} | 风险: {d['risk_label'] if 'risk_label' in d else d['risk_level']}")

            if d.get("assertion_detail"):
                lines.append(f"  断言: {d['assertion_detail']}")

            if d.get("response_snapshot"):
                lines.append(f"  响应: {d['response_snapshot']}")

            if d.get("suggestion"):
                lines.append(f"  建议: {d['suggestion']}")

            if d.get("history_status"):
                lines.append(f"  历史: {d['history_status']}")

            lines.append("")

        return "\n".join(lines)

    # ── 分类逻辑 ──────────────────────────────────────────────────

    @staticmethod
    def _classify_from_error(error_msg):
        """
        基于错误信息分类失败原因

        优先从实际业务数据判断，而非 traceback 关键字
        """
        err = str(error_msg)

        if "assert" in err.lower() or "AssertionError" in err:
            if "not_in" in err:
                return "assertion_failure_reverse"
            return "assertion_failure"

        status_code = re.search(r"状态码[=:]\s*(\d{3})", err)
        if status_code:
            code = int(status_code.group(1))
            if code in (401, 403):
                return "auth_error"
            if code >= 500:
                return "server_error"

        if "请求失败，响应为空" in err:
            return "network_error"
        if "Timeout" in err or "timed out" in err.lower():
            return "timeout"

        resp_match = re.search(r'["\']code["\']\s*:\s*(\d+)', err)
        if resp_match:
            code = int(resp_match.group(1))
            if code in (401, 403):
                return "auth_error"
            if code >= 500:
                return "server_error"
            if code in (400, 422):
                return "business_rejection"

        return "unknown"

    @staticmethod
    def _category_label(category):
        labels = {
            "assertion_failure": "断言失败（正向）",
            "assertion_failure_reverse": "断言失败（逆向用例通过了，说明服务端没做校验）",
            "server_error": "服务端错误",
            "auth_error": "认证/权限失败",
            "network_error": "网络/连接错误",
            "timeout": "请求超时",
            "business_rejection": "业务校验拒绝",
            "interface_changed": "接口变更",
            "unknown": "未分类",
        }
        return labels.get(category, category)

    @staticmethod
    def _assess_risk(category):
        high = {"server_error", "interface_changed", "auth_error"}
        medium = {"assertion_failure_reverse", "business_rejection", "network_error", "timeout"}
        if category in high:
            return "high"
        if category in medium:
            return "medium"
        return "low"

    # ── 信息提取 ──────────────────────────────────────────────────

    @staticmethod
    def _extract_assertion_detail(error_msg):
        """
        从错误信息中提取断言对比详情

        例: "code in [200, 0], 实际=401" → "code 期望 in [200, 0], 实际=401"
        """
        err = str(error_msg)

        match = re.search(
            r"(\w[\w.]*)\s+(eq|ne|in|not_in|not_null|contains|gt|lt|gte|lte)\s+(.*?),\s*实际[=:](.*)",
            err,
        )
        if match:
            path, op, expect, actual = match.groups()
            op_labels = {
                "eq": "等于", "ne": "不等于", "in": "在列表中",
                "not_in": "不在列表中", "not_null": "非空",
                "contains": "包含", "gt": "大于", "lt": "小于",
            }
            op_label = op_labels.get(op, op)
            return f"{path} 期望{op_label} {expect.strip()}, 实际={actual.strip()}"

        short = err[:200].replace("\n", " ").strip()
        return short if short else None

    @staticmethod
    def _extract_request_snapshot(failure_record):
        """
        从失败记录中提取请求快照
        """
        req = failure_record.get("request_info")
        if not req:
            return None
        if isinstance(req, dict):
            method = req.get("method", "?")
            url = req.get("url", "?")
            data = req.get("data")
            if data and isinstance(data, dict):
                keys = list(data.keys())[:5]
                return f"{method} {url} | 字段: {', '.join(keys)}..."
            return f"{method} {url}"
        return str(req)[:100]

    @staticmethod
    def _extract_response_snapshot(failure_record):
        """
        从失败记录中提取响应快照
        """
        resp = failure_record.get("response")
        if not resp:
            return None
        if isinstance(resp, dict):
            code = resp.get("code", "?")
            message = resp.get("message", "")
            if message:
                return f"code={code}, message={message}"
            return f"code={code}"
        return str(resp)[:100]

    # ── 建议生成 ──────────────────────────────────────────────────

    @staticmethod
    def _generate_suggestion(category, error_msg):
        """
        基于分类生成可操作的建议（不是废话）
        """
        err = str(error_msg)

        if category == "assertion_failure":
            if "not_in" in err and "200" in err:
                return "逆向用例的期望值可能需要更新，服务端对该场景已放行"
            match = re.search(r"实际[=:](\d+)", err)
            if match and match.group(1) in ("401", "403"):
                return "检查测试账号是否过期或被锁定"
            if match and int(match.group(1)) >= 500:
                return "服务端报错，提Bug给后端排查"
            return "对比期望值和实际值，确认是测试数据问题还是接口行为变更"

        if category == "assertion_failure_reverse":
            return "逆向用例期望失败但实际通过了，说明服务端未对该场景做校验，需确认是否为预期行为"

        if category == "server_error":
            return "服务端返回5xx，提Bug给后端，附带请求参数和响应日志"

        if category == "auth_error":
            return "检查 users.yaml 中账号密码是否正确，或账号是否被锁定/过期"

        if category == "business_rejection":
            match = re.search(r"message['\"]?\s*[:=]\s*['\"]?([^'\"}\n,]+)", err)
            msg = match.group(1).strip() if match else ""
            if msg:
                return f"服务端拒绝: {msg}，检查测试数据是否符合业务规则"
            return "服务端业务校验拒绝，检查请求参数是否符合业务规则"

        if category == "network_error":
            return "检查网络连接和目标环境是否可用"

        if category == "timeout":
            return "接口响应超时，检查服务端性能或网络延迟"

        return "查看日志中的请求参数和响应详情"

    # ── 历史对比 ──────────────────────────────────────────────────

    def _check_history(self, test_name):
        """
        检查该用例在历史执行中的状态

        :return: 如 "上次通过" / "连续3次失败" / None
        """
        history_file = os.path.join(self._history_dir, "history.json")
        if not os.path.exists(history_file):
            return None

        try:
            with open(history_file, "r", encoding="utf-8") as f:
                history = json.load(f)
        except Exception:
            return None

        if not history:
            return None

        recent = history[-5:]
        consecutive_fails = 0
        last_pass = False

        for run in reversed(recent):
            results = run.get("results", [])
            matched = [r for r in results if r.get("test_name") == test_name]
            if matched:
                status = matched[-1].get("status")
                if status in ("fail", "error"):
                    consecutive_fails += 1
                else:
                    last_pass = True
                    break

        if consecutive_fails >= 3:
            return f"连续{consecutive_fails}次失败，疑似服务端Bug"
        if consecutive_fails >= 2:
            return f"近期连续{consecutive_fails}次失败"
        if last_pass:
            return "上次通过，本次新增失败"
        if consecutive_fails == 1:
            return "首次失败"

        return None

    # ── AI 分析（有 LLM 时才调用）──────────────────────────────────

    def _get_ai_analysis(self, failure_record, diagnosis):
        if self.llm_client is None:
            return None

        prompt = build_root_cause_prompt(failure_record, diagnosis, None)
        try:
            if isinstance(self.llm_client, LLMClient):
                return self.llm_client.chat(
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.2,
                    max_tokens=1024,
                )
            else:
                result = self.llm_client.chat.completions.create(
                    model=self.config.get("llm.model", "deepseek-chat"),
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.2,
                    max_tokens=1024,
                )
                return result.choices[0].message.content
        except Exception:
            return None

    # ── 向后兼容 ──────────────────────────────────────────────────

    def analyze(self, failure_record, context=None):
        return self.diagnose(failure_record, context)

    def batch_analyze(self, failure_records, context=None):
        return self.batch_diagnose(failure_records, context)
