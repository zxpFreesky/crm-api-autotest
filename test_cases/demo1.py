# coding=utf-8
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import unittest
from common.my_ddt import ddt, data
from common import contants

from common.my_request import MyRequest
from common.do_excel import Operation_excel
from common.get_config import GetConfig
from common.Log_packing import Log
from common.my_log import logger
from common.query_data import Sql

# 创建日志对象
mylog = logger()
# 实例化配置对象
cf = GetConfig()
host = cf.get_value('host', 'url')  # 读取主机地址
file = 'datas/case_data.xlsx'
my_data = Operation_excel(file)
res_data = my_data.readData('注册')
login_data = my_data.readData('登录')
rech_data = my_data.readData('充值')


def uqtate_phone_number():  # 更新注册成功的用例手机号
    db = Sql("test.lemonban.com", "test", "test", "future")
    # 查询最大手机号
    max_num = db.query("select max(MobilePhone) from member")
    new_num = int(*max_num[0]) + 1
    for i in res_data:
        if "注册成功" in i.expect:
            i.data["mobilephone"] = new_num
            my_data.writeData("注册", i.case_id + 1, 5, str(i.data))  # 写回最新号码
    return my_data.readData("注册")


@ddt
class TestInterfaces(unittest.TestCase):
    """接口测试类"""

    @classmethod
    def setUpClass(cls):
        cls.rq = MyRequest()
        print('---开始测试---')

    @classmethod
    def tearDownClass(cls):
        print('---测试线束---')

    # @data(*case_data)
    # @unpack

    def interface(self, datas, sheet_name=None):

        # mylog.info("第{}条用例，标题为{}".format(datas.case_id, datas.title))
        # if sheet_name == "注册":
        #     db = Sql("test.lemonban.com", "test", "test", "future")
        #     # 查询最大手机号
        #     max_num = db.query("select max(MobilePhone) from member")
        #     new_num = int(*max_num[0]) + 1
        #     for i in res_data:
        #         if "注册成功" in i.expect:
        #             i.data["mobilephone"] = new_num
        #             my_data.writeData("注册", i.case_id + 1, 5, str(i.data))
        #             datas.data = i.data
        url = host + datas.url
        s = self.rq.my_request(url, datas.method, data=datas.data)
        try:
            res = 'Pass'
            self.assertIn(datas.expect, s.text)
        except Exception as e:
            res = "Fail"
            mylog.error('断言出错了:【%s】' % e)
            raise e
        finally:
            self.ex.writeData(sheet_name, datas.case_id + 1, 7, s.text)  # 写回结果
            self.ex.writeData(sheet_name, datas.case_id + 1, 8, res)

    @data(*res_data)
    def test_res(self, datas):
        self.interface(datas, '注册')

    @data(*login_data)
    def test_login(self, datas):
        self.interface(datas, '登录')

    @data(*rech_data)
    def test_rech(self, datas):
        self.interface(datas, '充值')


if __name__ == '__main__':
    print(*rech_data)
    suite = unittest.TestSuite()
    loder = unittest.TestLoader()
    suite.addTests(loder.loadTestsFromName('test_demo'))
    # discover = unittest.defaultTestLoader.discover(r'../case/',pattern='test*.py')
    # print(suite)
    # r = unittest.TextTestRunner()
    # r.run(suite)
