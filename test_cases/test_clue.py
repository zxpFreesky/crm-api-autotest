
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

YAML_FILE = os.path.join(yaml_cases_dir, "clue_cases.yaml")


def _load_yaml_cases():
    if not os.path.exists(YAML_FILE):
        return []
    cases = YamlCaseRunner.load_cases(YAML_FILE)
    return [(k, v) for k, v in cases.items()]



_yaml_cases = _load_yaml_cases()
_case_ids = [f"{k}: {v.get('name', k)}" for k, v in _yaml_cases]


def _resolve_data(data, ctx):
    """直接解析 YAML data 中的 @xxx 和 ${xxx}, 不与模板合并"""
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


class TestClueDataDriven:
    """
    线索接口数据驱动测试

    数据来源: datas/yaml_cases/clue_cases.yaml
    YAML data 字段直接作为请求参数, @xxx 动态生成, ${xxx} 从 session 取
    不与 ClueDataFactory.TEMPLATE 合并, YAML 里写了什么就发什么
    """

    @pytest.mark.parametrize("case_key,case_def", _yaml_cases, ids=_case_ids)
    def test_clue_case(self, case_key, case_def, login_client_factory, host):
        name = case_def.get("name", case_key)
        
        if case_def.get("skip", False):
            pytest.skip(f"用例 {name} 标记为跳过")
        
        account = case_def.get("account") or "default"
        client, ctx = login_client_factory.get_client(account)

        api = case_def.get("api", "")
        method = (case_def.get("method") or "get").lower()
        url = host.rstrip("/") + api

        log.info(f"[{case_key}] 用例标题: {name}")
        log.info(f"[{case_key}] 账号: {account} ({ctx.get('current_account', '?')}), 请求: {method.upper()} {api}")

        data = _resolve_data(case_def.get("data"), ctx)
        params = _resolve_params(case_def.get("params"), ctx)

        if data:
            log.info(f"[{case_key}] 请求参数: {json.dumps(data, ensure_ascii=False)}")
        if params:
            log.info(f"[{case_key}] Query参数: {json.dumps(params, ensure_ascii=False)}")

        expects = [a.get("expect") for a in (case_def.get("assert") or [])]
        log.info(f"[{case_key}] 期望结果: {expects}")

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
