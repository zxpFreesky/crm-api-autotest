
import sys
import os
import json
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from common.Log_packing import Log
from common.data_factory import ClueDataFactory

log = Log()


class TestAddClue:
    """
    添加线索接口测试用例

    数据策略: 每次运行都通过 DataFactory 动态生成唯一测试数据
    - customer_name: 自动生成唯一企业名 (时间戳+随机数)
    - business_license_code: 自动生成唯一信用代码
    - phone: 自动生成随机手机号
    - sale_user_id: 从 session_context 取 (依赖登录返回)
    """

    def test_add_clue_001_success(self, login_client_factory, host, data_factory):
        """
        正向用例: 动态数据添加线索成功
        """
        sale_client, sale_ctx = login_client_factory.get_client("sale_account_1")

        factory = ClueDataFactory(sale_ctx)
        data = factory.build()

        log.info(f"动态生成的线索数据:")
        log.info(f"  customer_name: {data['customer_name']}")
        log.info(f"  license_code:  {data['business_license_code']}")
        log.info(f"  phone:         {data.get('address', '')}")
        log.info(f"  province:      {data['province']}")

        url = host + "/admin.php/api/admin/customer-clue/add"
        response = sale_client.my_request(url, "post", data=data)

        assert response is not None, "请求失败，响应为空"
        assert response.status_code == 200, f"状态码错误: {response.status_code}"

        resp_data = response.json()
        log.info(f"响应: code={resp_data.get('code')}, msg={resp_data.get('message', '')}")
        assert resp_data.get("code") in [200, 0], f"业务错误: {resp_data}"

        from common.session_context import DataExtractor
        extractor = DataExtractor(sale_ctx)
        extracted = extractor.extract(response, {
            "clue_id": "data.id",
            "clue_name": "data.customer_name",
        })
        log.info(f"提取线索 ID: {extracted.get('clue_id')}")

    def test_add_clue_002_minimal_data(self, login_client_factory, host, data_factory):
        """
        正向用例: 最小必填字段也能添加成功
        """
        sale_client, sale_ctx = login_client_factory.get_client("sale_account_1")

        factory = ClueDataFactory(sale_ctx)
        data = factory.build_minimal()

        log.info(f"最小字段数: {len(data)}")

        url = host + "/admin.php/api/admin/customer-clue/add"
        response = sale_client.my_request(url, "post", data=data)

        assert response is not None
        assert response.status_code == 200

        resp_data = response.json()
        log.info(f"最小字段响应: code={resp_data.get('code')}")

    def test_add_clue_003_different_region(self, login_client_factory, host, data_factory):
        """
        正向用例: 指定地区覆盖
        """
        sale_client, sale_ctx = login_client_factory.get_client("sale_account_1")

        factory = ClueDataFactory(sale_ctx)
        data = factory.build(overrides={
            "province": "北京市",
            "city": "北京市",
            "town": "朝阳区",
        })

        assert data["province"] == "北京市"
        log.info(f"覆盖后 province={data['province']}, customer_name={data['customer_name']}")

        url = host + "/admin.php/api/admin/customer-clue/add"
        response = sale_client.my_request(url, "post", data=data)

        assert response is not None
        assert response.status_code == 200

    def test_add_clue_004_another_account(self, login_client_factory, host, data_factory):
        """
        正向用例: 不同账号各自生成独立数据
        """
        sale_client, sale_ctx = login_client_factory.get_client("sale_account_2")

        factory = ClueDataFactory(sale_ctx)
        data = factory.build()

        log.info(f"账号2数据: customer_name={data['customer_name']}")

        url = host + "/admin.php/api/admin/customer-clue/add"
        response = sale_client.my_request(url, "post", data=data)

        assert response is not None
        assert response.status_code == 200

    @pytest.mark.parametrize("missing", [
        "customer_name",
        "business_license_code",
    ])
    def test_add_clue_005_missing_required(self, logged_in_client, host, data_factory, missing):
        """
        逆向用例: 缺少必填字段 (参数化)
        """
        factory = ClueDataFactory()
        data = factory.build_invalid(missing_fields=[missing])

        assert missing not in data
        log.info(f"移除字段: {missing}, 剩余字段数: {len(data)}")

        url = host + "/admin.php/api/admin/customer-clue/add"
        response = logged_in_client.my_request(url, "post", data=data)

        assert response is not None
        resp_data = response.json()
        log.info(f"缺少 {missing} 响应: code={resp_data.get('code')}")

    def test_add_clue_006_empty_required(self, logged_in_client, host, data_factory):
        """
        逆向用例: 必填字段传空字符串
        """
        factory = ClueDataFactory()
        data = factory.build_invalid(empty_fields=["customer_name", "business_license_code"])

        assert data["customer_name"] == ""
        assert data["business_license_code"] == ""

        url = host + "/admin.php/api/admin/customer-clue/add"
        response = logged_in_client.my_request(url, "post", data=data)

        assert response is not None
        resp_data = response.json()
        log.info(f"空字段响应: code={resp_data.get('code')}")

    def test_add_clue_007_invalid_license(self, logged_in_client, host, data_factory):
        """
        逆向用例: 无效信用代码
        """
        factory = ClueDataFactory()
        data = factory.build_invalid(wrong_type_fields={
            "business_license_code": "INVALID_12345"
        })

        assert data["business_license_code"] == "INVALID_12345"

        url = host + "/admin.php/api/admin/customer-clue/add"
        response = logged_in_client.my_request(url, "post", data=data)

        assert response is not None
        resp_data = response.json()
        log.info(f"无效信用代码响应: code={resp_data.get('code')}")

    def test_add_clue_008_data_uniqueness(self, login_client_factory, host, data_factory):
        """
        验证用例: 连续生成两条数据应完全不同
        """
        factory = ClueDataFactory()

        data1 = factory.build()
        data2 = factory.build()

        assert data1["customer_name"] != data2["customer_name"], "两次生成的企业名不应相同"
        assert data1["business_license_code"] != data2["business_license_code"], "两次生成的信用代码不应相同"

        log.info(f"数据1: name={data1['customer_name']}, license={data1['business_license_code']}")
        log.info(f"数据2: name={data2['customer_name']}, license={data2['business_license_code']}")


class TestMultiAccountDynamic:
    """
    多账号 + 动态数据 组合场景
    """

    def test_two_accounts_independent_data(self, login_client_factory, host):
        """
        两个账号各自用动态数据添加线索, 数据完全独立
        """
        factory1 = ClueDataFactory()
        factory2 = ClueDataFactory()

        data1 = factory1.build()
        data2 = factory2.build(overrides={"province": "上海市", "city": "上海市"})

        assert data1["customer_name"] != data2["customer_name"]
        assert data2["province"] == "上海市"

        log.info(f"账号1: {data1['customer_name']} / {data1['province']}")
        log.info(f"账号2: {data2['customer_name']} / {data2['province']}")

        sale1_client, _ = login_client_factory.get_client("sale_account_1")
        sale2_client, _ = login_client_factory.get_client("sale_account_2")

        url = host + "/admin.php/api/admin/customer-clue/add"

        resp1 = sale1_client.my_request(url, "post", data=data1)
        resp2 = sale2_client.my_request(url, "post", data=data2)

        assert resp1 is not None and resp2 is not None
        assert resp1.status_code == 200
        assert resp2.status_code == 200

        log.info("两个账号独立添加线索成功")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
