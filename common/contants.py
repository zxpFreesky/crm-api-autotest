import os

"""
项目路径常量定义

所有路径均基于项目根目录计算，确保跨平台兼容性
"""

base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

data_dir = os.path.join(base_dir, "datas")
case_file = os.path.join(data_dir, "case_data.xlsx")

conf_dir = os.path.join(base_dir, "config")
test_conf = os.path.join(conf_dir, "test.ini")
ai_conf = os.path.join(conf_dir, "ai_config.yaml")

log_dir = os.path.join(base_dir, "logs")
report_dir = os.path.join(base_dir, "reports")
case_dir = os.path.join(base_dir, "test_cases")
yaml_cases_dir = os.path.join(data_dir, "yaml_cases")
