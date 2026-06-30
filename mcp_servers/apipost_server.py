import json
import requests


class ApiPostMCPClient:
    """
    ApiPost MCP 客户端
    暴露的能力:
    - get_api_list: 获取所有接口列表
    - get_api_detail: 获取接口详情
    - send_request: 直接调试接口
    - get_schemas: 获取数据模型
    - get_env_vars: 获取环境变量
    """

    def __init__(self, base_url=None, api_token=None, env="test"):
        self.base_url = base_url or ""
        self.api_token = api_token or ""
        self.env = env
        self._session = requests.Session()
        self._api_cache = {}

    def _request(self, method, endpoint, **kwargs):
        headers = {
            "Authorization": f"Bearer {self.api_token}",
            "Content-Type": "application/json",
        }
        headers.update(kwargs.pop("headers", {}))
        url = f"{self.base_url}{endpoint}"
        resp = self._session.request(method, url, headers=headers, **kwargs)
        resp.raise_for_status()
        return resp.json()

    def get_api_list(self, project_id=None, keyword=None):
        """
        获取接口列表
        :param project_id: 项目ID
        :param keyword: 关键词过滤 (如 "login", "customer")
        :return: 接口元数据列表
        """
        params = {}
        if project_id:
            params["project_id"] = project_id
        if keyword:
            params["keyword"] = keyword

        try:
            result = self._request("GET", "/api/apis", params=params)
            apis = result.get("data", [])
            self._api_cache = {api["name"]: api for api in apis}
            return apis
        except Exception as e:
            return {"error": str(e), "apis": []}

    def get_api_detail(self, api_id=None, api_name=None):
        """
        获取接口详情 (含请求参数、响应结构、描述)
        :param api_id: 接口ID
        :param api_name: 接口名称 (备选定位方式)
        :return: 接口完整元数据
        """
        if api_name and api_name in self._api_cache:
            api_id = self._api_cache[api_name].get("id")

        if not api_id:
            return {"error": "api_id or api_name required"}

        try:
            result = self._request("GET", f"/api/apis/{api_id}")
            return result.get("data", {})
        except Exception as e:
            return {"error": str(e)}

    def send_request(self, api_id=None, api_name=None, env=None, **overrides):
        """
        直接调试接口 (通过 MCP 发送请求)
        :param api_id: 接口ID
        :param api_name: 接口名称
        :param env: 环境 (test/uat/prod)
        :param overrides: 覆盖参数 (headers, params, body 等)
        :return: 接口响应
        """
        target_env = env or self.env
        payload = {"env": target_env}
        payload.update(overrides)

        if api_name and api_name in self._api_cache:
            api_id = self._api_cache[api_name].get("id")
        if not api_id:
            return {"error": "api_id or api_name required"}

        try:
            result = self._request("POST", f"/api/apis/{api_id}/run", json=payload)
            return result.get("data", {})
        except Exception as e:
            return {"error": str(e)}

    def get_schemas(self, project_id=None):
        """
        获取项目数据模型 (请求/响应 Schema)
        :param project_id: 项目ID
        :return: Schema 列表
        """
        params = {}
        if project_id:
            params["project_id"] = project_id

        try:
            result = self._request("GET", "/api/schemas", params=params)
            return result.get("data", [])
        except Exception as e:
            return {"error": str(e)}

    def get_env_vars(self, env=None):
        """
        获取环境变量
        :param env: 环境名称 (test/uat/prod)
        :return: 环境变量字典
        """
        target_env = env or self.env
        try:
            result = self._request("GET", "/api/envs", params={"env": target_env})
            return result.get("data", {})
        except Exception as e:
            return {"error": str(e)}

    def detect_api_changes(self, api_id, baseline=None):
        """
        检测接口变更 (对比当前定义与基线)
        :param api_id: 接口ID
        :param baseline: 基线定义 (上次的 Schema), 为空则自动获取
        :return: 变更差异列表
        """
        current = self.get_api_detail(api_id=api_id)
        if "error" in current:
            return current

        if baseline is None:
            return {"status": "no_baseline", "current": current}

        changes = self._diff_schema(baseline, current)
        return {"api_id": api_id, "changes": changes}

    @staticmethod
    def _diff_schema(baseline, current):
        diffs = []
        base_req = baseline.get("request", {})
        cur_req = current.get("request", {})
        base_resp = baseline.get("response", {})
        cur_resp = current.get("response", {})

        base_fields = {f["name"]: f for f in base_req.get("params", [])}
        cur_fields = {f["name"]: f for f in cur_req.get("params", [])}

        for name in set(base_fields) - set(cur_fields):
            diffs.append({"type": "param_removed", "field": name, "detail": base_fields[name]})
        for name in set(cur_fields) - set(base_fields):
            diffs.append({"type": "param_added", "field": name, "detail": cur_fields[name]})

        base_resp_fields = {f["name"]: f for f in base_resp.get("fields", [])}
        cur_resp_fields = {f["name"]: f for f in cur_resp.get("fields", [])}

        for name in set(base_resp_fields) - set(cur_resp_fields):
            diffs.append({"type": "response_field_removed", "field": name})
        for name in set(cur_resp_fields) - set(base_resp_fields):
            diffs.append({"type": "response_field_added", "field": name})

        return diffs
