
import sys
import os
import json
import base64
import pytest

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from common.my_request import MyRequest
from common.get_config import GetConfig
from common.Log_packing import Log
from common.session_context import SessionContext, DataExtractor
from common.data_factory import DataFactory
from mcp_servers.database_server import DatabaseMCPClient
from mcp_servers.report_server import ReportMCPClient
from ai.smart_assert import SmartAssert
from ai.self_healing import SelfHealingEngine
from ai.root_cause import RootCauseAnalyzer


def _decode_jwt_payload(token):
    """解码 JWT token 的 payload 部分, 获取 uid 等信息"""
    try:
        payload_b64 = token.split(".")[1]
        padding = 4 - len(payload_b64) % 4
        if padding != 4:
            payload_b64 += "=" * padding
        payload = base64.b64decode(payload_b64)
        return json.loads(payload)
    except Exception:
        return {}


def _extract_login_data(response, ctx, extractor):
    """登录成功后提取 token 和 user_id (从 JWT 解码)"""
    extracted = extractor.extract(response, {"token": "data.access_token"})
    token = extracted.get("token")
    if not token:
        return extracted

    jwt_data = _decode_jwt_payload(token)
    uid = jwt_data.get("data", {}).get("uid") or jwt_data.get("uid")
    if uid:
        ctx.set("user_id", str(uid))
        ctx.set("sale_user_id", str(uid))
        extracted["user_id"] = uid
        extracted["sale_user_id"] = uid

    return extracted


@pytest.fixture(scope="session")
def config():
    return GetConfig()


@pytest.fixture(scope="session")
def host(config):
    return config.get_host()


@pytest.fixture(scope="session")
def api_client():
    client = MyRequest()
    yield client
    client.clear_history()


@pytest.fixture(scope="session")
def session_context():
    ctx = SessionContext()
    yield ctx
    log = Log()
    log.info(ctx.summary())


@pytest.fixture(scope="session")
def data_extractor(session_context):
    return DataExtractor(session_context)


@pytest.fixture(scope="session")
def logged_in_client(api_client, host, config, session_context, data_extractor):
    yield from _logged_in_client_impl(api_client, host, config, session_context, data_extractor, "default")


class LoginClientFactory:

    def __init__(self, host, config, session_context, data_extractor):
        self.host = host
        self.config = config
        self.session_context = session_context
        self.data_extractor = data_extractor
        self._clients_cache = {}
        self._context_cache = {}
        self._log = Log()

    def get_client(self, role_key="default", create_new=False):
        user = self.config.get_user_by_role(role_key)
        user_name = user.get("user", "?")

        if not create_new and role_key in self._clients_cache:
            self._log.info(f"使用缓存的账号: {role_key} ({user_name})")
            return self._clients_cache[role_key], self._context_cache[role_key]

        self._log.info(f"登录账号: {role_key} ({user_name})")
        ctx = SessionContext()
        client = MyRequest()

        login_url = self.host + "/api/admin/login"
        self._log.info(f"登录 URL: {login_url}")

        response = client.my_request(
            login_url, "post",
            data={
                "account": user["user"],
                "password": user["pwd"],
                "identity_type": 0,
                "remember_pwd": False,
                "verify_code": "",
                "using_email_verify": 0,
                "fingerprint": f"auto_api_{role_key}",
                "is_pc_login": 1,
                "RSApassword": 0,
            },
            headers={
                "X-Request-Path": "/login",
                "X-Request-Source": "3d",
                "Accept": "application/json,text/plain, */*",
            }
        )

        if response and response.status_code == 200:
            try:
                extractor = DataExtractor(ctx)
                extracted = _extract_login_data(response, ctx, extractor)
                if extracted.get("token"):
                    client.set_token(extracted["token"])
                    ctx.set("token", extracted["token"])
                    self._log.info(f"账号 {role_key} ({user_name}) 登录成功，token 已注入, uid={ctx.get('user_id')}")
                    ctx.set("current_account", user["user"])
                    ctx.set("current_role_key", role_key)
                    ctx.record_step(f"登录-{role_key}", login_url)
            except Exception as e:
                self._log.error(f"登录响应解析失败: {e}")
        else:
            self._log.warning(f"账号 {role_key} ({user_name}) 登录失败（状态码: {response.status_code if response else 'None'}）")

        self._clients_cache[role_key] = client
        self._context_cache[role_key] = ctx
        return client, ctx


@pytest.fixture(scope="session")
def login_client_factory(host, config, session_context, data_extractor):
    return LoginClientFactory(host, config, session_context, data_extractor)


def _logged_in_client_impl(api_client, host, config, session_context, data_extractor, role_key):
    log = Log()
    user = config.get_user_by_role(role_key)
    login_url = host + "/api/admin/login"
    log.info(f"[依赖链] 开始登录: {user['user']} (角色: {role_key})")

    response = api_client.my_request(
        login_url, "post",
        data={
            "account": user["user"],
            "password": user["pwd"],
            "identity_type": 0,
            "remember_pwd": False,
            "verify_code": "",
            "using_email_verify": 0,
            "fingerprint": "auto_api_rmp_framework",
            "is_pc_login": 1,
            "RSApassword": 0,
        },
        headers={
            "X-Request-Path": "/login",
            "X-Request-Source": "3d",
            "Accept": "application/json,text/plain, */*",
        }
    )

    if response and response.status_code == 200:
        try:
            resp_data = response.json()
            data_extractor.extract(response, {
                "token": "data.access_token",
            })
            extracted = _extract_login_data(response, session_context, data_extractor)
            token = session_context.get("token")
            if token:
                api_client.set_token(token)
                log.info(f"[依赖链] 登录成功，token 已注入")
            else:
                log.warning("[依赖链] 登录成功但未提取到 token")
        except Exception as e:
            log.error(f"[依赖链] 登录响应解析失败: {e}")
    else:
        log.warning(f"[依赖链] 登录失败（状态码: {response.status_code if response else 'None'}）")

    session_context.record_step(f"登录-{role_key}", login_url)
    yield api_client


@pytest.fixture(scope="session")
def db_client(config):
    db_config = config.get_database_config()
    if db_config.get("host"):
        client = DatabaseMCPClient(
            host=db_config.get("host"),
            user=db_config.get("usename"),
            password=db_config.get("pwd"),
            database=db_config.get("database", ""),
        )
        yield client
        client.close()
    else:
        yield None


@pytest.fixture(scope="session")
def report_client(config):
    webhook = ""
    msg_type = "markdown"
    mentioned_list = []
    mentioned_mobile = []

    try:
        webhook = config.get_value("notify", "wecom_webhook").strip()
    except Exception:
        pass
    try:
        msg_type = config.get_value("notify", "wecom_msg_type").strip() or "markdown"
    except Exception:
        pass
    try:
        raw = config.get_value("notify", "wecom_mentioned_list").strip()
        if raw:
            mentioned_list = [m.strip() for m in raw.split(",") if m.strip()]
    except Exception:
        pass
    try:
        raw = config.get_value("notify", "wecom_mentioned_mobile").strip()
        if raw:
            mentioned_mobile = [m.strip() for m in raw.split(",") if m.strip()]
    except Exception:
        pass

    client = ReportMCPClient(
        wecom_webhook=webhook if webhook else None,
        wecom_mentioned_list=mentioned_list,
        wecom_mentioned_mobile_list=mentioned_mobile,
    )
    yield client

    client.save_to_history()

    failed_details = client.get_failed_details()
    analysis_results = []

    diagnosis_enabled = False
    try:
        diagnosis_enabled = config.get_value("ai", "diagnosis").strip().lower() == "true"
    except Exception:
        pass

    if failed_details and diagnosis_enabled:
        log = Log()
        log.info(f"[诊断] 发现 {len(failed_details)} 条失败用例，开始结构化诊断...")
        try:
            analyzer = RootCauseAnalyzer()
            analysis_results = analyzer.batch_diagnose(failed_details)

            high_risk = [r for r in analysis_results if r.get("risk_level") == "high"]
            medium_risk = [r for r in analysis_results if r.get("risk_level") == "medium"]

            log.info(f"[诊断] 诊断完成: 高风险 {len(high_risk)} 条, 中风险 {len(medium_risk)} 条")
            for r in analysis_results:
                log.info(
                    f"[诊断] {r['test_name']}: "
                    f"分类={r['category_label']}, "
                    f"风险={r['risk_level']}"
                )
                if r.get("assertion_detail"):
                    log.info(f"[诊断]   断言: {r['assertion_detail']}")
                if r.get("suggestion"):
                    log.info(f"[诊断]   建议: {r['suggestion']}")
                if r.get("history_status"):
                    log.info(f"[诊断]   历史: {r['history_status']}")
        except Exception as e:
            log.warning(f"[诊断] 诊断失败: {e}")

    if webhook:
        env_name = config.get_active_env()
        result = client.notify_wecom(
            env_name=env_name, msg_type=msg_type,
            analysis_results=analysis_results,
        )
        log = Log()
        if result["success"]:
            log.info(f"[企业微信] 测试报告推送成功 (类型: {msg_type})")
        else:
            log.warning(f"[企业微信] 推送失败: {result['response']}")


@pytest.fixture(scope="session")
def smart_assert(config):
    enabled = False
    try:
        enabled = config.get_value("ai", "smart_assert").strip().lower() == "true"
    except Exception:
        pass
    if not enabled:
        return None
    return SmartAssert()


@pytest.fixture(scope="session")
def self_healing(config):
    enabled = False
    try:
        enabled = config.get_value("ai", "self_healing").strip().lower() == "true"
    except Exception:
        pass
    if not enabled:
        return None
    return SelfHealingEngine()


@pytest.fixture(scope="session")
def root_cause_analyzer():
    return RootCauseAnalyzer()


@pytest.fixture(scope="session")
def data_factory(session_context):
    return DataFactory(session_context)


@pytest.fixture(autouse=True)
def log_test_info(request):
    log = Log()
    node_name = request.node.name.encode('utf-8').decode('unicode_escape') if '\\u' in repr(request.node.name) else request.node.name
    log.info(f"{'=' * 60}")
    log.info(f"开始执行: {node_name}")
    yield
    log.info(f"执行完成: {node_name}")
    log.info(f"{'=' * 60}")


@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item, call):
    """
    收集测试结果，包括跳过的用例
    
    pytest-testreport 插件依赖此钩子来统计测试结果。
    如果缺少此钩子或实现不正确，跳过的用例可能不会被正确统计。
    
    此钩子会将报告对象保存到 item 上，供后续的 fixture 使用
    """
    outcome = yield
    report = outcome.get_result()
    
    if report.when == 'call':
        # 将报告对象保存到 item，供 collect_test_result fixture 使用
        item.report = report
        
        log = Log()
        node_name = item.name.encode('utf-8').decode('unicode_escape') if '\\u' in repr(item.name) else item.name
        
        if report.skipped:
            log.info(f"[SKIP] {node_name}: {report.longreprtext if report.longrepr else '跳过'}")
        elif report.failed:
            log.error(f"[FAIL] {node_name}: {report.longreprtext if report.longrepr else '失败'}")
        else:
            log.info(f"[PASS] {node_name}")


@pytest.fixture(autouse=True)
def collect_test_result(request, report_client):
    """
    自动收集每个测试用例的结果到报告客户端
    
    确保所有状态（pass/fail/error/skip）的用例都被正确统计
    
    注意：pytest-testreport 插件会将 report.duration 修改为字符串类型，
    需要进行类型转换后再使用
    """
    node_name = request.node.name.encode('utf-8').decode('unicode_escape') if '\\u' in repr(request.node.name) else request.node.name
    
    yield
    
    try:
        # 获取 pytest_runtest_makereport 钩子保存的报告对象
        if hasattr(request.node, 'report'):
            report = request.node.report
            status = "pass"
            error_msg = None
            
            if report.skipped:
                status = "skip"
                error_msg = str(report.longrepr) if report.longrepr else "跳过"
            elif report.failed:
                status = "error" if report.when != 'call' else "fail"
                error_msg = str(report.longrepr) if report.longrepr else "失败"
            
            # 处理 duration：pytest-testreport 插件会将其改为字符串类型
            duration = 0
            if hasattr(report, 'duration'):
                try:
                    duration = float(report.duration)
                except (ValueError, TypeError):
                    duration = 0
            
            report_client.collect_result(
                test_name=node_name,
                status=status,
                duration=duration,
                error_msg=error_msg
            )
    except Exception as e:
        log = Log()
        log.warning(f"收集测试结果失败: {e}")
