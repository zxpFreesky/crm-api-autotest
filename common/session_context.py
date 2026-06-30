import json
import re

from .Log_packing import Log


class SessionContext:
    """
    会话状态管理器 — 解决接口业务依赖的核心组件

    解决的问题:
    - 登录获取的 token, 后续所有接口都要用
    - 创建客户返回的 customer_id, 创建订单时要用
    - 创建订单返回的 order_id, 支付/退款时要用
    - 整条业务链的数据需要自动传递

    使用方式:
        ctx = SessionContext()

        # 存储数据 (通常从接口响应中提取)
        ctx.set("token", "eyJhbGc...")
        ctx.set("customer_id", 12345)

        # 获取数据 (后续接口使用)
        token = ctx.get("token")
        cid = ctx.get("customer_id")

        # 在请求参数中自动替换占位符
        data = {"customer_id": "${customer_id}", "token": "${token}"}
        resolved = ctx.resolve(data)  # 自动替换为实际值
    """

    def __init__(self):
        self._store = {}
        self._logger = Log()
        self._dependency_chain = []

    def set(self, key, value):
        self._store[key] = value
        self._logger.debug(f"[SessionContext] SET {key} = {str(value)[:100]}")

    def get(self, key, default=None):
        return self._store.get(key, default)

    def has(self, key):
        return key in self._store

    def remove(self, key):
        if key in self._store:
            del self._store[key]

    def clear(self):
        self._store.clear()
        self._dependency_chain.clear()

    def all(self):
        return dict(self._store)

    def resolve(self, data):
        """
        递归替换数据中的 ${key} 占位符为实际值
        支持 dict / list / str 类型
        """
        if isinstance(data, str):
            return self._resolve_string(data)
        elif isinstance(data, dict):
            return {k: self.resolve(v) for k, v in data.items()}
        elif isinstance(data, list):
            return [self.resolve(item) for item in data]
        return data

    def _resolve_string(self, s):
        pattern = r"\$\{(\w+)\}"
        matches = re.findall(pattern, s)
        if not matches:
            return s
        for key in matches:
            if key in self._store:
                value = str(self._store[key])
                s = s.replace(f"${{{key}}}", value)
            else:
                self._logger.warning(f"[SessionContext] 占位符 ${{{key}}} 未找到对应值")
        return s

    def record_step(self, step_name, api_name, request_data=None, response_data=None):
        self._dependency_chain.append({
            "step": step_name,
            "api": api_name,
            "extracted": {
                k: str(v)[:80] for k, v in self._store.items()
            },
        })

    def get_chain(self):
        return list(self._dependency_chain)

    def summary(self):
        lines = ["[会话状态摘要]", "-" * 40]
        for k, v in self._store.items():
            lines.append(f"  {k} = {str(v)[:100]}")
        if self._dependency_chain:
            lines.append(f"\n[依赖链 ({len(self._dependency_chain)} 步)]")
            for step in self._dependency_chain:
                lines.append(f"  {step['step']} → {step['api']}")
        return "\n".join(lines)


class DataExtractor:
    """
    响应数据提取器 — 从接口响应中提取业务数据存入 SessionContext

    解决的问题:
    - 从登录响应中提取 token
    - 从创建客户响应中提取 customer_id
    - 从任意响应中按 JSONPath / 字段路径提取值
    """

    def __init__(self, context):
        self._context = context
        self._logger = Log()

    def extract(self, response, mapping):
        """
        从响应中提取数据并存入 SessionContext
        :param response: requests.Response 对象
        :param mapping: 提取映射 {"context_key": "json_path", ...}
                        json_path 支持点号分隔: "data.token", "data.user_info.id"
        :return: 提取结果的字典
        """
        if response is None:
            self._logger.error("[DataExtractor] 响应为 None, 无法提取")
            return {}

        try:
            resp_json = response.json()
        except (json.JSONDecodeError, ValueError):
            self._logger.error("[DataExtractor] 响应不是有效 JSON")
            return {}

        extracted = {}
        for context_key, json_path in mapping.items():
            value = self._get_by_path(resp_json, json_path)
            if value is not None:
                self._context.set(context_key, value)
                extracted[context_key] = value
                self._logger.info(f"[提取] {context_key} ← {json_path} = {str(value)[:100]}")
            else:
                self._logger.warning(f"[提取失败] {json_path} 路径不存在")

        return extracted

    def extract_from_text(self, response, mapping):
        """
        从响应文本中用正则提取数据
        :param mapping: {"context_key": "regex_pattern", ...}
        """
        if response is None:
            return {}

        text = response.text
        extracted = {}
        for context_key, pattern in mapping.items():
            match = re.search(pattern, text)
            if match:
                value = match.group(1) if match.groups() else match.group(0)
                self._context.set(context_key, value)
                extracted[context_key] = value
                self._logger.info(f"[正则提取] {context_key} = {str(value)[:100]}")

        return extracted

    def extract_headers(self, response, mapping):
        """
        从响应头中提取数据 (如 Set-Cookie 中的 token)
        :param mapping: {"context_key": "header_name", ...}
        """
        if response is None:
            return {}

        extracted = {}
        for context_key, header_name in mapping.items():
            value = response.headers.get(header_name)
            if value:
                self._context.set(context_key, value)
                extracted[context_key] = value
                self._logger.info(f"[Header提取] {context_key} ← {header_name}")

        return extracted

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
