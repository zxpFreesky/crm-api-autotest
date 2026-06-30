
import sys
import os
import json
import re
import pytest
import html as html_module

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from common.Log_packing import Log
from common.yaml_runner import YamlCaseRunner
from common.contants import yaml_cases_dir

log = Log()

YAML_FILE = os.path.join(yaml_cases_dir, "login_cases.yaml")


def _load_yaml_cases():
    if not os.path.exists(YAML_FILE):
        return []
    cases = YamlCaseRunner.load_cases(YAML_FILE)
    return [(k, v) for k, v in cases.items() ]


_yaml_cases = _load_yaml_cases()
_case_ids = [f"{k}: {v.get('name', k)}" for k, v in _yaml_cases]


class TestLogin:
    """
    登录接口测试 - 数据驱动

    数据来源: datas/yaml_cases/login_cases.yaml
    """

    @pytest.mark.parametrize("case_key,case_def", _yaml_cases, ids=_case_ids)
    def test_login(self, case_key, case_def, api_client, host, session_context):
        name = case_def.get("name", case_key)
        
        if case_def.get("skip", False):
            pytest.skip(f"用例 {name} 标记为跳过")
        
        api = case_def.get("api", "")
        method = (case_def.get("method") or "post").lower()
        url = host + api
        data = case_def.get("data")
        expects = [a.get("expect") for a in (case_def.get("assert") or [])]

        log.info(f"[{case_key}] 用例标题: {name}")
        log.info(f"[{case_key}] 请求方式: {method.upper()}, 请求地址: {api}")
        log.info(f"[{case_key}] 请求参数: {json.dumps(data, ensure_ascii=False)}")
        log.info(f"[{case_key}] 期望结果: {expects}")

        response = api_client.my_request(
            url, method,
            data=data,
            headers={
                "X-Request-Path": "/login",
                "X-Request-Source": "3d",
                "Accept": "application/json,text/plain, */*",
            }
        )

        assert response is not None, f"[{case_key}] 请求失败"

        resp_data = {}
        if response.status_code == 200:
            try:
                resp_data = response.json()
            except Exception:
                resp_data = {}
        else:
            try:
                resp_data = response.json()
            except Exception:
                raw_text = response.text[:200]
                if raw_text.strip().startswith("<!DOCTYPE") or raw_text.strip().startswith("<html"):
                    clean = re.sub(r"<[^>]+>", "", raw_text)
                    clean = re.sub(r"\s+", " ", clean).strip()[:200]
                    resp_data = {"message": f"[HTML响应已清理] {clean}"}
                else:
                    resp_data = {"message": raw_text}

        log.info(f"[{case_key}] 实际响应: 状态码={response.status_code}, body={html_module.escape(json.dumps(resp_data, ensure_ascii=False)[:500])}")

        extract = case_def.get("extract")
        if extract:
            from common.session_context import DataExtractor
            extractor = DataExtractor(session_context)
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
