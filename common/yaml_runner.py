
import os
import yaml
import json
import pytest

from common.Log_packing import Log
from common.data_factory import DataFactory
from common.session_context import DataExtractor


class YamlCaseRunner:
    """
    YAML 用例执行引擎

    读取 YAML 文件中的用例定义，自动执行并断言。
    测试人员只需维护 YAML 文件，无需编写 Python 代码。

    YAML 用例格式:
        case_key:
          name: 用例名称
          api: /path/to/api
          method: post
          account: sale_account_1
          data: { ... }          # post/put body
          params: { ... }        # get/query 参数
          extract: { ctx_key: json_path }
          assert:
            - path: code
              operator: in
              expect: [200, 0]
          skip: false
    """

    def __init__(self, login_client_factory, host, session_contexts=None):
        self._factory = login_client_factory
        self._host = host
        self._contexts = session_contexts or {}
        self._log = Log()
        self._data_factory = DataFactory()
        self._shared_context = {}
        self._results = []

    @staticmethod
    def load_cases(yaml_path):
        with open(yaml_path, "r", encoding="utf-8") as f:
            cases = yaml.safe_load(f)
        return cases

    def run_case(self, case_key, case_def):
        name = case_def.get("name", case_key)
        api = case_def.get("api", "")
        method = (case_def.get("method") or "get").lower()
        account = case_def.get("account") or "default"
        extract = case_def.get("extract") or {}
        asserts = case_def.get("assert") or []
        skip = case_def.get("skip", False)

        result = {
            "case_key": case_key,
            "name": name,
            "status": "skip",
            "message": "",
            "assertions": [],
        }

        if skip:
            result["message"] = "用例标记为跳过"
            self._log.info(f"[SKIP] {name}: 用例标记为跳过")
            pytest.skip(f"用例 {name} 标记为跳过")
            return result

        client, ctx = self._factory.get_client(account)
        extractor = DataExtractor(ctx)

        url = self._host + api
        self._log.info(f"[RUN] {name} | {method.upper()} {api} | 账号: {account} ({ctx.get('current_account', '?')})")

        data = case_def.get("data")
        params = case_def.get("params")

        if data:
            self._data_factory.set_session_context(ctx)
            data = self._data_factory.generate(data)

        if params:
            resolved_params = {}
            for k, v in params.items():
                if isinstance(v, str) and "${" in v:
                    val = v
                    import re
                    for match in re.findall(r"\$\{(\w+)\}", v):
                        ctx_val = ctx.get(match) or self._shared_context.get(match, "")
                        val = val.replace(f"${{{match}}}", str(ctx_val))
                    resolved_params[k] = val
                else:
                    resolved_params[k] = v
            params = resolved_params

        try:
            if method == "get":
                if params:
                    query = "&".join(f"{k}={v}" for k, v in params.items())
                    url = url + ("&" if "?" in url else "?") + query
                response = client.my_request(url, "get")
            elif method == "delete":
                if params:
                    query = "&".join(f"{k}={v}" for k, v in params.items())
                    url = url + ("&" if "?" in url else "?") + query
                response = client.my_request(url, "delete")
            elif method in ("post", "put", "patch"):
                kwargs = {}
                if data:
                    kwargs["data"] = data
                response = client.my_request(url, method, **kwargs)
            else:
                response = client.my_request(url, method, data=data)
        except Exception as e:
            result["status"] = "error"
            result["message"] = str(e)
            self._log.error(f"[ERROR] {name}: 请求异常 - {e}")
            return result

        if response is None:
            result["status"] = "error"
            result["message"] = "响应为空"
            self._log.error(f"[FAIL] {name}: 响应为空")
            return result

        try:
            resp_data = response.json()
        except Exception:
            resp_data = {"raw": response.text}

        self._log.info(f"[RESP] {name}: status={response.status_code}, data={json.dumps(resp_data, ensure_ascii=False)[:200]}")

        if extract:
            extracted = extractor.extract(response, extract)
            for k, v in extracted.items():
                self._shared_context[k] = v
            self._log.info(f"[EXTRACT] {name}: {extracted}")

        all_passed = True
        for assertion in asserts:
            a_path = assertion.get("path", "")
            a_op = assertion.get("operator", "eq")
            a_expect = assertion.get("expect")

            actual = self._get_by_path(resp_data, a_path)

            passed = self._do_assert(actual, a_op, a_expect)
            assertion_result = {
                "path": a_path,
                "operator": a_op,
                "expect": a_expect,
                "actual": actual,
                "passed": passed,
            }
            result["assertions"].append(assertion_result)

            if not passed:
                all_passed = False
                self._log.warning(
                    f"[ASSERT FAIL] {name}: {a_path} {a_op} {a_expect}, 实际值={actual}"
                )
            else:
                self._log.info(f"[ASSERT OK] {name}: {a_path} {a_op} {a_expect}")

        result["status"] = "pass" if all_passed else "fail"
        result["response_code"] = response.status_code

        if all_passed:
            self._log.info(f"[PASS] {name}")
        else:
            self._log.error(f"[FAIL] {name}: 断言失败")

        self._results.append(result)
        return result

    @staticmethod
    def _do_assert(actual, operator, expect):
        if operator == "eq":
            return actual == expect
        elif operator == "ne":
            return actual != expect
        elif operator == "in":
            return actual in expect
        elif operator == "not_in":
            return actual not in expect
        elif operator == "not_null":
            return actual is not None and actual != ""
        elif operator == "contains":
            return expect in str(actual) if actual else False
        elif operator == "gt":
            return actual is not None and actual > expect
        elif operator == "lt":
            return actual is not None and actual < expect
        elif operator == "gte":
            return actual is not None and actual >= expect
        elif operator == "lte":
            return actual is not None and actual <= expect
        return False

    @staticmethod
    def _get_by_path(data, path):
        keys = path.split(".")
        current = data
        for key in keys:
            if isinstance(current, dict):
                current = current.get(key)
            elif isinstance(current, list):
                try:
                    current = current[int(key)]
                except (ValueError, IndexError):
                    return None
            else:
                return None
            if current is None:
                return None
        return current

    def get_results(self):
        return self._results

    def get_summary(self):
        total = len(self._results)
        passed = sum(1 for r in self._results if r["status"] == "pass")
        failed = sum(1 for r in self._results if r["status"] == "fail")
        errored = sum(1 for r in self._results if r["status"] == "error")
        skipped = sum(1 for r in self._results if r["status"] == "skip")
        return {
            "total": total,
            "passed": passed,
            "failed": failed,
            "errored": errored,
            "skipped": skipped,
        }
