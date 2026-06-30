import sys
import os
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from common.do_excel import OperationExcel
from common.contants import case_file, report_dir
from common.Log_packing import Log
from mcp_servers.report_server import ReportMCPClient

mylog = Log()
my_data = OperationExcel(case_file)
login_data = my_data.read_data('登录')

report_client = ReportMCPClient(report_dir=report_dir)


class TestLogin:
    """登录接口测试 - AI + MCP 架构"""

    def setup_class(self):
        self.report = report_client

    def _run_interface(self, api_client, host, datas, sheet_name=None):
        mylog.info(f"第{datas.case_id}条用例，标题为{datas.title}，请求参数:{datas.data}")

        url = host + datas.url
        start_time = time.time()
        s = api_client.my_request(
            url, datas.method,
            data=datas.data,
            headers={
                "X-Request-Path": "/login",
                "X-Request-Source": "3d",
                "Accept": "application/json,text/plain, */*",
            }
        )
        duration = time.time() - start_time

        if s is None:
            self.report.collect_result(
                test_name=datas.title, status="error",
                duration=duration, error_msg="请求返回None"
            )
            pytest.fail(f"请求失败: {datas.title}")

        try:
            assert datas.expect in s.text
            self.report.collect_result(
                test_name=datas.title, status="pass",
                duration=duration, response=s.text[:500]
            )
        except AssertionError as e:
            self.report.collect_result(
                test_name=datas.title, status="fail",
                duration=duration, error_msg=str(e), response=s.text[:500]
            )
            mylog.error(f'断言出错了:【{e}】')
            raise
        finally:
            if sheet_name:
                my_data.write_data(sheet_name, datas.case_id + 1, 7, s.text)

    @pytest.mark.parametrize("datas", login_data)
    def test_login(self, api_client, host, datas):
        self._run_interface(api_client, host, datas, '登录')

    def teardown_class(self):
        self.report.save_to_history()


if __name__ == "__main__":
    pytest.main([__file__, '-v', '-s'])
