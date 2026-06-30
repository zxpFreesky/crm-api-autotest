
import time
import random
import string
import re
import json
from datetime import datetime, timedelta


class DataFactory:
    """
    动态数据工厂 — 解决测试数据写死的问题

    核心能力:
        1. 每次调用生成唯一值 (时间戳+随机数)
        2. 支持引用 session_context 中的动态值 (如 ${clue_id})
        3. 支持数据模板 + 覆盖策略
        4. 支持从上一个接口的响应中取值

    使用方式:
        factory = DataFactory()

        # 定义模板, 用 @xxx 标记动态字段
        template = {
            "customer_name": "@company",          # 随机公司名
            "business_license_code": "@license",  # 随机信用代码
            "phone": "@phone",                    # 随机手机号
            "gmt_create": "@now",                 # 当前时间
            "province": "广东省",                  # 固定值
            "sale_user_id": "${sale_user_id}",    # 从 session 取
        }

        # 生成数据
        data = factory.generate(template)

        # 带覆盖 (指定某些字段用特定值)
        data = factory.generate(template, overrides={"province": "北京市"})
    """

    REGIONS = {
        "广东省": {
            "广州市": ["天河区", "白云区", "番禺区", "花都区", "南沙区"],
            "深圳市": ["南山区", "福田区", "宝安区", "龙岗区", "龙华区"],
            "东莞市": ["长安镇", "虎门镇", "厚街镇", "塘厦镇", "常平镇"],
            "佛山市": ["顺德区", "南海区", "禅城区", "三水区", "高明区"],
        },
        "北京市": {
            "北京市": ["朝阳区", "海淀区", "丰台区", "东城区", "西城区", "大兴区", "通州区"],
        },
        "上海市": {
            "上海市": ["浦东新区", "闵行区", "徐汇区", "静安区", "杨浦区", "松江区"],
        },
        "江苏省": {
            "苏州市": ["工业园区", "吴中区", "姑苏区", "虎丘区", "相城区"],
            "南京市": ["江宁区", "鼓楼区", "玄武区", "建邺区", "栖霞区"],
            "无锡市": ["锡山区", "惠山区", "滨湖区", "新吴区", "梁溪区"],
        },
        "浙江省": {
            "杭州市": ["西湖区", "余杭区", "萧山区", "滨江区", "拱墅区"],
            "宁波市": ["鄞州区", "海曙区", "镇海区", "北仑区", "江北区"],
            "温州市": ["鹿城区", "龙湾区", "瓯海区", "乐清市", "瑞安市"],
        },
        "四川省": {
            "成都市": ["武侯区", "锦江区", "青羊区", "高新区", "金牛区"],
        },
        "湖北省": {
            "武汉市": ["洪山区", "武昌区", "江汉区", "汉阳区", "江岸区"],
        },
        "湖南省": {
            "长沙市": ["岳麓区", "雨花区", "天心区", "芙蓉区", "开福区"],
        },
        "福建省": {
            "福州市": ["鼓楼区", "台江区", "仓山区", "晋安区", "马尾区"],
            "厦门市": ["思明区", "湖里区", "集美区", "海沧区", "同安区"],
        },
    }

    def __init__(self, session_context=None):
        self._session_context = session_context
        self._counter = 0
        self._region_cache = {}

    def set_session_context(self, ctx):
        self._session_context = ctx

    def random_region(self):
        """联动生成 省/市/区 组合, 保证数据一致性"""
        province = random.choice(list(self.REGIONS.keys()))
        cities = self.REGIONS[province]
        city = random.choice(list(cities.keys()))
        town = random.choice(cities[city])
        return province, city, town

    def generate(self, template, overrides=None):
        """
        根据模板生成动态数据
        :param template: 数据模板, @xxx 表示动态, ${xxx} 表示从 session 取
        :param overrides: 覆盖字段
        """
        self._counter += 1
        ts = str(int(time.time() * 1000))[-6:]
        rand = str(random.randint(100, 999))

        self._region_cache = {}

        result = {}
        for key, value in template.items():
            if isinstance(value, str):
                result[key] = self._resolve_value(value, ts, rand)
            elif isinstance(value, (list, dict)):
                result[key] = value
            else:
                result[key] = value

        if overrides:
            for key, value in overrides.items():
                if isinstance(value, str):
                    result[key] = self._resolve_value(value, ts, rand)
                else:
                    result[key] = value

        return result

    def _get_region_part(self, part):
        if not self._region_cache:
            self._region_cache = self.random_region()
        if part == "province":
            return self._region_cache[0]
        elif part == "city":
            return self._region_cache[1]
        elif part == "town":
            return self._region_cache[2]
        return ""

    def _resolve_value(self, value, ts, rand):
        if not isinstance(value, str):
            return value

        generators = {
            "@company": lambda: f"自动化测试企业_{ts}{rand}",
            "@company_short": lambda: f"测试企{rand}",
            "@name": lambda: f"测试联系人_{ts[-4:]}{rand}",
            "@nickname": lambda: f"测试昵称_{ts[-4:]}{rand}",
            "@phone": lambda: self._gen_phone(),
            "@landline": lambda: f"0{random.choice(['10','20','21','755','769'])}-{random.randint(10000000,99999999)}",
            "@email": lambda: f"test_{ts}{rand}@example.com",
            "@license": lambda: self._gen_license_code(),
            "@now": lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "@today": lambda: datetime.now().strftime("%Y-%m-%d"),
            "@today_iso": lambda: datetime.now().strftime("%Y-%m-%dT%H:%M:%S.000Z"),
            "@timestamp": lambda: str(int(time.time())),
            "@uuid": lambda: f"{ts}{rand}{random.randint(1000,9999)}",
            "@address": lambda: f"测试地址_{random.choice(['A栋','B栋','C栋'])}{random.randint(1,99)}楼",
            "@remark": lambda: f"自动化测试_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "@int": lambda: str(random.randint(1, 100)),
            "@int_100_500": lambda: str(random.randint(100, 500)),
            "@float_area": lambda: f"{random.uniform(10.0, 200.0):.2f}",
            "@yes_no": lambda: str(random.choice([0, 1])),
            "@province": lambda: self._get_region_part("province"),
            "@city": lambda: self._get_region_part("city"),
            "@town": lambda: self._get_region_part("town"),
        }

        if value in generators:
            return generators[value]()

        # @random:N 随机 N 位数字
        m = re.match(r"^@random:(\d+)$", value)
        if m:
            n = int(m.group(1))
            return "".join([str(random.randint(0, 9)) for _ in range(n)])

        # @choice:a,b,c 随机选一个
        m = re.match(r"^@choice:(.+)$", value)
        if m:
            options = m.group(1).split(",")
            return random.choice(options)

        # @prefix_xxx  带前缀的唯一值
        m = re.match(r"^@prefix_(\w+)$", value)
        if m:
            return f"{m.group(1)}_{ts}{rand}"

        # 字符串内嵌的 @xxx 替换 (如 docking_person 中的 @nickname)
        if re.search(r"@\w+", value):
            for pattern, gen in generators.items():
                if pattern in value:
                    value = value.replace(pattern, gen())
            for m_choice in re.finditer(r"@choice:([\w,]+)", value):
                opts = m_choice.group(1).split(",")
                value = value.replace(m_choice.group(0), random.choice(opts), 1)
            for m_rand in re.finditer(r"@random:(\d+)", value):
                n = int(m_rand.group(1))
                value = value.replace(m_rand.group(0), "".join([str(random.randint(0, 9)) for _ in range(n)]), 1)

        if "${" in value:
            return self._resolve_session_refs(value)

        return value

    def _resolve_session_refs(self, value):
        if self._session_context is None:
            return value
        pattern = r"\$\{(\w+)\}"
        matches = re.findall(pattern, value)
        for key in matches:
            ctx_value = self._session_context.get(key)
            if ctx_value is not None:
                value = value.replace(f"${{{key}}}", str(ctx_value))
        return value

    @staticmethod
    def _gen_phone():
        prefixes = ["130", "131", "132", "133", "135", "136", "137", "138", "139",
                     "150", "151", "152", "155", "156", "157", "158", "159",
                     "170", "176", "177", "178", "180", "181", "182", "183",
                     "185", "186", "187", "188", "189"]
        prefix = random.choice(prefixes)
        suffix = "".join([str(random.randint(0, 9)) for _ in range(8)])
        return prefix + suffix

    @staticmethod
    def _gen_license_code():
        """
        生成 18 位统一社会信用代码 (模拟)
        格式: 91 + 6位地区码 + 10位随机
        """
        region_codes = ["440100", "440300", "440900", "310100", "110100",
                        "320500", "330100", "510100", "420100", "370100"]
        region = random.choice(region_codes)
        body = "".join(random.choices("0123456789ABCDEFGHJKLMNPQRTUWXY", k=10))
        return "91" + region + body


class ClueDataFactory(DataFactory):
    """
    线索数据工厂 — 预定义线索接口的动态数据模板

    用法:
        factory = ClueDataFactory(session_context)

        # 生成一条完整的线索数据
        data = factory.build()

        # 覆盖部分字段
        data = factory.build(overrides={"province": "北京市"})

        # 生成最小必填数据
        data = factory.build_minimal()

        # 生成异常数据 (用于逆向测试)
        data = factory.build_invalid(missing_fields=["customer_name"])
    """

    TEMPLATE = {
        "customer_id": "0",
        "nickname": "@nickname",
        "customer_name": "@company",
        "business_license_code": "@license",
        "customer_short_name": "@company_short",
        "customer_fixed_line": "",
        "legal_person": "@name",
        "gmt_establish": "",
        "regist_amount": "",
        "insure": "@int",
        "province": "@province",
        "city": "@city",
        "town": "@town",
        "area": "",
        "address": "@address",
        "gmt_create": "@now",
        "ground_name": "",
        "project_area": "@float_area",
        "day_settlement_time": "@today_iso",
        "daily_settle_time": "@timestamp",
        "normal_wait_time_limit": "30",
        "night_shift": "@yes_no",
        "third_month_avg_settle": "0",
        "bc_shift_num_val": "50:100",
        "night_shift_start": "21:00:00",
        "night_shift_end": "08:00:00",
        "scale": "@int_100_500",
        "worker_scale": "@int_100_500",
        "temporary_wages": "@int",
        "temporary_scale": "@int",
        "device": "",
        "model": "",
        "sale_user_id": "${sale_user_id}",
        "assistant_user_id": "${assistant_user_id}",
        "source": "@choice:1,2,3,4,5,6,7",
        "technology_type": "",
        "technology_remark": "",
        "industry": "",
        "industry_remark": "",
        "product": "",
        "intention_degree": "@choice:0,1,2,3",
        "automation_degree": "@choice:0,1,2,3",
        "estimate_num": "@int_100_500",
        "remark": "@remark",
        "supple_remark": "",
        "external_remark": "",
        "scene_remark": "",
        "product_remark": "",
        "workmanship_remark": "",
        "recommend_remark": "",
        "external_media_archive_id": "",
        "scene_media_archive_id": "",
        "product_media_archive_id": "",
        "workmanship_media_archive_id": "",
        "recommend_work_station_archive_id": ""
    }

    MINIMAL_TEMPLATE = {
        "customer_id": "0",
        "nickname": "@nickname",
        "customer_name": "@company",
        "business_license_code": "@license",
        "province": "@province",
        "city": "@city",
        "town": "@town",
        "address": "@address",
        "gmt_create": "@now",
        "sale_user_id": "${sale_user_id}",
        "assistant_user_id": "${assistant_user_id}",
        "source": "7",
        "remark": "@remark",
    }

    def build(self, overrides=None):
        return self.generate(self.TEMPLATE, overrides)

    def build_minimal(self, overrides=None):
        return self.generate(self.MINIMAL_TEMPLATE, overrides)

    def build_invalid(self, missing_fields=None, empty_fields=None, wrong_type_fields=None):
        """
        生成异常测试数据
        :param missing_fields: 要移除的字段列表
        :param empty_fields: 要置空的字段列表
        :param wrong_type_fields: 要设置错误类型值的字段 {"field": "wrong_value"}
        """
        data = self.generate(self.TEMPLATE)

        if missing_fields:
            for field in missing_fields:
                data.pop(field, None)

        if empty_fields:
            for field in empty_fields:
                data[field] = ""

        if wrong_type_fields:
            for field, value in wrong_type_fields.items():
                data[field] = value

        return data
