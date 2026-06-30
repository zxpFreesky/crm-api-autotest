import sys
import os
import glob

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pytest
from common.yaml_runner import YamlCaseRunner


class RunTestCase:
    """
    测试运行器 — 统一的测试执行入口
    
    支持的命令:
        python run.py --all                    # 运行全部用例
        python run.py --file test_clue.py      # 运行指定文件
        python run.py --all -k login           # 按关键字过滤
        python run.py --list-cases             # 列出所有 YAML 测试数据
        python run.py --list-accounts          # 列出所有测试账号
    
    生成的报告:
        reports/_report.html - HTML 格式测试报告
    """

    def __init__(self, case_path='test_cases/', report_path='reports/',
                 title='CRM接口自动化测试报告',
                 tester='zouxp', desc='CRM项目接口自动化回归'):
        self.root_dir = os.path.dirname(os.path.abspath(__file__))
        self.case_path = os.path.abspath(case_path)
        self.report_path = os.path.abspath(report_path)
        self.title = title
        self.tester = tester
        self.desc = desc
        os.makedirs(self.report_path, exist_ok=True)

    def _base_args(self):
        return [
            '-v', '-s',
            '--report=_report.html',
            f'--title={self.title}',
            f'--tester={self.tester}',
            f'--desc={self.desc}',
            '--template=2',
            '-W', 'ignore:Module already imported:pytest.PytestWarning',
        ]

    def run_all(self, keyword=None, markers=None):
        args = [self.case_path] + self._base_args()
        if keyword:
            args.extend(['-k', keyword])
        if markers:
            args.extend(['-m', markers])
        pytest.main(args)

    def run_file(self, file_name, keyword=None):
        file_path = os.path.join(self.case_path, file_name)
        args = [file_path] + self._base_args()
        if keyword:
            args.extend(['-k', keyword])
        pytest.main(args)

    def run_module(self, module_name):
        self.run_all(keyword=module_name)

    def list_yaml_cases(self):
        from common.contants import yaml_cases_dir
        if not os.path.isdir(yaml_cases_dir):
            print("未找到 YAML 数据目录: datas/yaml_cases/")
            return
        yaml_files = sorted(glob.glob(os.path.join(yaml_cases_dir, "*.yaml")))
        if not yaml_files:
            print("没有 YAML 数据文件")
            return
        print("=" * 60)
        print("YAML 测试数据列表")
        print("=" * 60)
        for yaml_file in yaml_files:
            filename = os.path.basename(yaml_file)
            cases = YamlCaseRunner.load_cases(yaml_file)
            print(f"\n  [{filename}]")
            for case_key, case_def in cases.items():
                skip_mark = " [SKIP]" if case_def.get("skip") else ""
                print(f"    - {case_key}: {case_def.get('name', '')}{skip_mark}")
        print()

    def list_accounts(self):
        from common.get_config import GetConfig
        config = GetConfig()
        accounts = config.list_available_users()
        print("=" * 60)
        print("可用测试账号 (config/users.yaml)")
        print("=" * 60)
        for key in accounts:
            user = config.get_user_by_role(key)
            print(f"  - {key}: {user['user']} ({user.get('role', '')})")
        print()


if __name__ == '__main__':
    import argparse

    r = RunTestCase()

    parser = argparse.ArgumentParser(description='CRM 接口自动化测试框架')
    parser.add_argument('--all', action='store_true', help='运行全部用例')
    parser.add_argument('--file', type=str, help='运行指定 py 文件')
    parser.add_argument('-k', '--keyword', type=str, help='按关键字过滤')
    parser.add_argument('--list-cases', action='store_true', help='列出所有 YAML 测试数据')
    parser.add_argument('--list-accounts', action='store_true', help='列出所有测试账号')

    args = parser.parse_args()

    if args.list_cases:
        r.list_yaml_cases()
    elif args.list_accounts:
        r.list_accounts()
    elif args.file:
        r.run_file(args.file, keyword=args.keyword)
    elif args.all:
        r.run_all(keyword=args.keyword)
    else:
        r.run_all()
