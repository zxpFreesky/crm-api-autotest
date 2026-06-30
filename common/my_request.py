import requests
import json
import time

from .Log_packing import Log


class MyRequest:
    """
    HTTP 请求封装类 (基于 requests.Session)
    
    核心能力:
    - 统一的请求方法封装 (get/post/put/delete/patch)
    - 自动记录请求历史和耗时
    - 支持 token 注入和自定义 headers
    - 请求异常捕获和日志记录
    
    使用方式:
        client = MyRequest()
        response = client.my_request("https://api.example.com/user", "get")
        response = client.my_request("https://api.example.com/user", "post", data={"name": "test"})
        
        # 设置认证 token
        client.set_token("eyJhbGc...")
        
        # 设置自定义 headers
        client.set_headers({"X-Request-Source": "pc"})
    """
    def __init__(self):
        self.session = requests.Session()
        self.logger = Log()
        self._response_history = []

    def my_request(self, url, method, **kwargs):
        method = method.lower()
        start_time = time.time()

        try:
            if method == "get":
                response = self.session.get(url, **kwargs)
            elif method == "post":
                response = self.session.post(url, **kwargs)
            elif method == "put":
                response = self.session.put(url, **kwargs)
            elif method == "delete":
                response = self.session.delete(url, **kwargs)
            elif method == "patch":
                response = self.session.patch(url, **kwargs)
            else:
                self.logger.error(f"不支持的请求方法: {method}")
                return None

            duration = round(time.time() - start_time, 3)
            self.logger.info(
                f"[{method.upper()}] {url} | 状态码: {response.status_code} | 耗时: {duration}s"
            )

            self._response_history.append({
                "url": url,
                "method": method,
                "status_code": response.status_code,
                "duration": duration,
                "response_text": response.text[:500],
            })

            return response

        except requests.exceptions.RequestException as e:
            duration = round(time.time() - start_time, 3)
            self.logger.error(f"请求异常: [{method.upper()}] {url} | 错误: {e} | 耗时: {duration}s")
            return None

    def set_headers(self, headers):
        self.session.headers.update(headers)

    def set_token(self, token, header_name="Authorization", prefix="Bearer "):
        self.session.headers[header_name] = f"{prefix}{token}"

    def get_history(self):
        return self._response_history

    def clear_history(self):
        self._response_history = []


if __name__ == "__main__":
    mr = MyRequest()
    resp = mr.my_request("https://httpbin.org/get", "get")
    if resp:
        print(resp.text)
