import json
import os
import re
import yaml
import hashlib
from datetime import datetime

from .config import AIConfig
from .llm_client import LLMClient
from .prompts.case_gen import (
    build_yaml_case_prompt,
    build_python_runner_template,
    build_case_gen_prompt,
    build_negative_case_prompt,
)


class CaseGenerator:
    """
    AI 用例智能生成引擎 — 核心组件，支持两种生成模式
    
    核心能力:
    1. YAML 数据驱动模式 (推荐): 生成 YAML 测试数据 + Python 运行器模板
    2. Python 编程模式 (向后兼容): 直接生成完整的 Python 测试代码
    
    生成流程:
        API 元数据 → LLM 分析 → 四维度测试用例 → 输出文件
    
    四维度测试设计:
        - 维度一: 正向 + CRUD 业务依赖链
        - 维度二: 必填校验 (每个必填字段单独验证)
        - 维度三: 字段边界值 (字符串长度/数值范围/枚举非法/手机号格式等)
        - 维度四: 场景测试 (权限隔离/重复操作/列表筛选等)
    
    使用方式:
        gen = CaseGenerator()
        
        # YAML 模式 (推荐)
        result = gen.generate_from_apipost_yaml(keyword="客户线索")
        print(result["yaml_file"])   # datas/yaml_cases/clue_cases.yaml
        print(result["py_file"])     # test_cases/test_clue.py
        
        # Python 模式 (向后兼容)
        result = gen.generate_from_apipost(keyword="登录")
        print(result["file"])        # test_cases/test_ai_login.py
    """

    def __init__(self, config=None, llm_client=None, apipost_client=None, excel_reader=None):
        self.config = config or AIConfig()
        if llm_client is None:
            if self.config.get("llm.api_key"):
                self.llm_client = self.config.create_llm_client()
            else:
                self.llm_client = None
        elif isinstance(llm_client, LLMClient):
            self.llm_client = llm_client
        else:
            self.llm_client = llm_client
        self.apipost_client = apipost_client
        self.excel_reader = excel_reader
        self._root_dir = os.path.dirname(os.path.dirname(__file__))
        self._output_dir = os.path.join(self._root_dir, "test_cases")
        self._yaml_dir = os.path.join(self._root_dir, "datas", "yaml_cases")
        self._registry_file = os.path.join(
            self._root_dir, "datas", "ai_case_registry.json"
        )
        self._registry = self._load_registry()

    def fetch_api_metadata(self, api_name=None, api_id=None, keyword=None):
        """
        从 ApiPost MCP 拉取接口元数据 (LLM 生成的核心数据源)
        
        :param api_name: 接口名称
        :param api_id: 接口 ID
        :param keyword: 搜索关键字
        :return: 接口元数据字典，包含接口名称、路径、方法、请求参数、响应结构等
        """
        if self.apipost_client is None:
            return None
        if api_name:
            return self.apipost_client.get_api_detail(api_name=api_name)
        if api_id:
            return self.apipost_client.get_api_detail(api_id=api_id)
        if keyword:
            apis = self.apipost_client.get_api_list(keyword=keyword)
            return apis[0] if apis else None
        return None

    def fetch_existing_cases(self, sheet_name):
        """
        从 Excel 读取已有测试用例数据, 作为 LLM 的参考上下文
        
        :param sheet_name: Excel 工作表名称
        :return: 用例列表，每个用例包含 title、url、method、data、expect
        """
        if self.excel_reader is None:
            return None
        cases = self.excel_reader.read_data(sheet_name)
        result = []
        for c in cases:
            result.append({
                "title": c.title,
                "url": c.url,
                "method": c.method,
                "data": c.data,
                "expect": c.expect,
            })
        return result

    def _extract_module_name(self, api_metadata, api_name=None):
        """
        从接口元数据中提取模块名称，用于生成文件名
        
        :param api_metadata: 接口元数据
        :param api_name: 可选的接口名称覆盖
        :return: 规范化的模块名称（小写、下划线分隔）
        """
        if api_name:
            name = api_name
        else:
            name = api_metadata.get("name", "unknown")

        name = name.replace("/", "_").replace(" ", "_").replace("-", "_")
        name = re.sub(r"_+", "_", name).strip("_")
        name = re.sub(r"[^a-zA-Z0-9_\u4e00-\u9fff]", "", name)

        parts = name.split("_")
        filtered = [p for p in parts if p and not p.isdigit()]
        if filtered:
            name = "_".join(filtered)
        return name.lower() if name else "api"

    def _clean_yaml_output(self, raw_output):
        """
        清理 LLM 返回的 YAML 输出，去除 markdown 代码块标记
        
        :param raw_output: LLM 返回的原始输出
        :return: 纯净的 YAML 字符串
        """
        cleaned = raw_output.strip()
        if cleaned.startswith("```yaml"):
            cleaned = cleaned[7:]
        elif cleaned.startswith("```"):
            cleaned = cleaned[3:]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
        cleaned = cleaned.strip()
        try:
            parsed = yaml.safe_load(cleaned)
            if isinstance(parsed, dict):
                return cleaned
        except yaml.YAMLError:
            pass
        yaml_match = re.search(
            r"^([a-zA-Z_][\w]*:\s*\n(?:[ \t]+.+\n?)*)",
            cleaned,
            re.MULTILINE,
        )
        if yaml_match:
            return yaml_match.group(0)
        return cleaned

    # ── YAML 数据驱动生成 (推荐) ─────────────────────────────────

    def generate_yaml_cases(self, api_metadata, options=None, existing_cases=None, business_rules=None):
        """
        生成 YAML 格式的测试用例数据
        
        :param api_metadata: 接口元数据
        :param options: 生成选项
        :param existing_cases: 已有用例（避免重复）
        :param business_rules: 业务规则约束
        :return: YAML 格式的测试用例字符串
        """
        opts = options or {}
        gen_config = self.config.case_gen_config

        prompt = build_yaml_case_prompt(
            api_metadata, gen_config, existing_cases, business_rules
        )
        raw_yaml = self._call_llm(prompt)
        cleaned_yaml = self._clean_yaml_output(raw_yaml)

        try:
            yaml.safe_load(cleaned_yaml)
        except yaml.YAMLError as e:
            cleaned_yaml = f"# YAML 解析失败, 请人工检查\n# 错误: {e}\n\n{cleaned_yaml}"

        return cleaned_yaml

    def generate_from_apipost_yaml(self, api_name=None, api_id=None, keyword=None,
                                   excel_sheet=None, business_rules=None):
        """
        完整链路: ApiPost 拉取元数据 → LLM 生成 YAML + Python 双文件
        
        :param api_name: 接口名称
        :param api_id: 接口 ID
        :param keyword: 搜索关键字
        :param excel_sheet: Excel 工作表名称（可选，用于参考已有用例）
        :param business_rules: 业务规则约束
        :return: 包含状态、文件路径等信息的结果字典
        """
        api_metadata = self.fetch_api_metadata(
            api_name=api_name, api_id=api_id, keyword=keyword
        )
        if api_metadata is None or "error" in api_metadata:
            return {
                "status": "error",
                "message": "无法从 ApiPost 获取接口元数据, 请检查 ApiPost MCP 配置",
                "yaml_file": None,
                "py_file": None,
            }

        existing_cases = None
        if excel_sheet:
            existing_cases = self.fetch_existing_cases(excel_sheet)

        module_name = self._extract_module_name(api_metadata, api_name)

        yaml_content = self.generate_yaml_cases(
            api_metadata, existing_cases=existing_cases, business_rules=business_rules
        )
        yaml_filepath = self._save_yaml_file(module_name, yaml_content)

        py_content = build_python_runner_template(module_name)
        py_filepath = self._save_py_file(module_name, py_content)

        api_name_val = api_metadata.get("name", api_name or "unknown")
        self._register_case(
            filename=f"{module_name}_cases.yaml",
            filepath=yaml_filepath,
            source="apipost_yaml",
            api_name=api_name_val,
            has_existing_cases=existing_cases is not None,
            code_hash=hashlib.md5(yaml_content.encode()).hexdigest()[:8],
        )
        self._register_case(
            filename=f"test_{module_name}.py",
            filepath=py_filepath,
            source="apipost_yaml_runner",
            api_name=api_name_val,
            has_existing_cases=existing_cases is not None,
            code_hash=hashlib.md5(py_content.encode()).hexdigest()[:8],
        )

        return {
            "status": "success",
            "api_name": api_name_val,
            "module_name": module_name,
            "yaml_file": yaml_filepath,
            "py_file": py_filepath,
            "yaml_content": yaml_content,
        }

    def generate_from_excel_yaml(self, sheet_name, api_metadata=None, business_rules=None):
        """
        从 Excel 用例数据出发: 读取已有用例 → LLM 补充生成 YAML + Python 双文件
        
        :param sheet_name: Excel 工作表名称
        :param api_metadata: 接口元数据（可选，若不传则从 Excel 推断）
        :param business_rules: 业务规则约束
        :return: 包含状态、文件路径等信息的结果字典
        """
        existing_cases = self.fetch_existing_cases(sheet_name)
        if not existing_cases:
            return {
                "status": "error",
                "message": f"Excel sheet '{sheet_name}' 无用例数据",
                "yaml_file": None,
                "py_file": None,
            }

        if api_metadata is None:
            sample = existing_cases[0]
            api_metadata = {
                "name": sheet_name,
                "method": sample.get("method", "POST"),
                "path": sample.get("url", ""),
                "existing_data_samples": existing_cases[:3],
            }

        module_name = self._extract_module_name(api_metadata, sheet_name)

        yaml_content = self.generate_yaml_cases(
            api_metadata, existing_cases=existing_cases, business_rules=business_rules
        )
        yaml_filepath = self._save_yaml_file(module_name, yaml_content)

        py_content = build_python_runner_template(module_name)
        py_filepath = self._save_py_file(module_name, py_content)

        self._register_case(
            filename=f"{module_name}_cases.yaml",
            filepath=yaml_filepath,
            source="excel_yaml",
            api_name=sheet_name,
            has_existing_cases=True,
            code_hash=hashlib.md5(yaml_content.encode()).hexdigest()[:8],
        )

        return {
            "status": "success",
            "api_name": sheet_name,
            "module_name": module_name,
            "yaml_file": yaml_filepath,
            "py_file": py_filepath,
            "existing_case_count": len(existing_cases),
            "yaml_content": yaml_content,
        }

    # ── Python 模式生成 (向后兼容) ────────────────────────────────

    def generate(self, api_metadata, options=None, existing_cases=None, business_rules=None):
        """
        生成 Python 格式的测试代码（向后兼容模式）
        
        :param api_metadata: 接口元数据
        :param options: 生成选项
        :param existing_cases: 已有用例（避免重复）
        :param business_rules: 业务规则约束
        :return: Python 测试代码字符串
        """
        gen_config = self.config.case_gen_config

        prompt = build_case_gen_prompt(
            api_metadata, gen_config, existing_cases, business_rules
        )
        code = self._call_llm(prompt)

        if gen_config.get("enable_negative", True):
            neg_prompt = build_negative_case_prompt(
                api_metadata, gen_config, existing_cases, business_rules
            )
            neg_code = self._call_llm(neg_prompt)
            code = code + "\n\n" + neg_code

        return code

    def generate_from_apipost(self, api_name=None, api_id=None, keyword=None,
                              excel_sheet=None, business_rules=None):
        api_metadata = self.fetch_api_metadata(
            api_name=api_name, api_id=api_id, keyword=keyword
        )
        if api_metadata is None or "error" in api_metadata:
            return {
                "status": "error",
                "message": "无法从 ApiPost 获取接口元数据, 请检查 ApiPost MCP 配置",
                "code": None,
            }

        existing_cases = None
        if excel_sheet:
            existing_cases = self.fetch_existing_cases(excel_sheet)

        code = self.generate(
            api_metadata, existing_cases=existing_cases, business_rules=business_rules
        )

        api_name_val = api_metadata.get("name", api_name or "unknown")
        filename = f"test_ai_{api_name_val.replace('/', '_').replace(' ', '_')}.py"
        filepath = self.save_to_file(
            code, filename, source="apipost",
            api_name=api_name_val,
            existing_cases=existing_cases is not None,
        )

        return {
            "status": "success",
            "api_name": api_name_val,
            "file": filepath,
            "code": code,
        }

    def generate_from_excel(self, sheet_name, api_metadata=None, business_rules=None):
        existing_cases = self.fetch_existing_cases(sheet_name)
        if not existing_cases:
            return {
                "status": "error",
                "message": f"Excel sheet '{sheet_name}' 无用例数据",
                "code": None,
            }

        if api_metadata is None:
            sample = existing_cases[0]
            api_metadata = {
                "name": sheet_name,
                "method": sample.get("method", "POST"),
                "path": sample.get("url", ""),
                "existing_data_samples": existing_cases[:3],
            }

        code = self.generate(
            api_metadata, existing_cases=existing_cases, business_rules=business_rules
        )

        filename = f"test_ai_{sheet_name}.py"
        filepath = self.save_to_file(
            code, filename, source="excel",
            api_name=sheet_name, existing_cases=True,
        )

        return {
            "status": "success",
            "api_name": sheet_name,
            "file": filepath,
            "existing_case_count": len(existing_cases),
            "code": code,
        }

    # ── 文件保存 ──────────────────────────────────────────────────

    def _save_yaml_file(self, module_name, content):
        """
        保存 YAML 测试用例文件到 datas/yaml_cases/
        
        :param module_name: 模块名称
        :param content: YAML 内容
        :return: 文件路径
        """
        os.makedirs(self._yaml_dir, exist_ok=True)
        filepath = os.path.join(self._yaml_dir, f"{module_name}_cases.yaml")
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)
        return filepath

    def _save_py_file(self, module_name, content):
        """
        保存 Python 测试运行器文件到 test_cases/
        
        :param module_name: 模块名称
        :param content: Python 代码内容
        :return: 文件路径
        """
        os.makedirs(self._output_dir, exist_ok=True)
        filepath = os.path.join(self._output_dir, f"test_{module_name}.py")
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)
        return filepath

    def save_to_file(self, code, filename, source="manual", api_name=None, existing_cases=False):
        """
        保存测试代码文件并注册到用例注册表
        
        :param code: 代码内容
        :param filename: 文件名
        :param source: 来源标识 (manual/apipost/excel/apipost_yaml/excel_yaml)
        :param api_name: 接口名称
        :param existing_cases: 是否有已有用例参考
        :return: 文件路径
        """
        filepath = os.path.join(self._output_dir, filename)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(code)

        self._register_case(
            filename=filename,
            filepath=filepath,
            source=source,
            api_name=api_name,
            has_existing_cases=existing_cases,
            code_hash=hashlib.md5(code.encode()).hexdigest()[:8],
        )
        return filepath

    # ── 用例管理 ──────────────────────────────────────────────────

    def _register_case(self, filename, filepath, source, api_name, has_existing_cases, code_hash):
        """
        注册用例到注册表，记录用例来源、生成时间等信息
        
        :param filename: 文件名
        :param filepath: 文件完整路径
        :param source: 来源标识
        :param api_name: 接口名称
        :param has_existing_cases: 是否有已有用例参考
        :param code_hash: 代码内容哈希值
        """
        entry = {
            "filename": filename,
            "source": source,
            "api_name": api_name,
            "has_existing_cases": has_existing_cases,
            "code_hash": code_hash,
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }
        self._registry[filename] = entry
        self._save_registry()

    def get_ai_cases(self):
        """
        获取所有 AI 生成的用例（排除手动编写的）
        
        :return: AI 生成用例字典
        """
        return {k: v for k, v in self._registry.items() if v["source"] != "manual"}

    def get_manual_cases(self):
        """
        获取所有手动编写的用例（不在注册表中或来源为 manual）
        
        :return: 手动编写用例文件名集合
        """
        all_case_files = set()
        for f in os.listdir(self._output_dir):
            if f.startswith("test_") and f.endswith(".py"):
                all_case_files.add(f)
        ai_cases = set(self._registry.keys())
        return all_case_files - ai_cases

    def get_case_info(self, filename):
        """
        获取指定用例的详细信息
        
        :param filename: 文件名
        :return: 用例信息字典
        """
        return self._registry.get(filename)

    def get_registry(self):
        """
        获取完整的用例注册表
        
        :return: 注册表字典
        """
        return self._registry

    def _load_registry(self):
        """
        从文件加载用例注册表
        
        :return: 注册表字典
        """
        if os.path.exists(self._registry_file):
            with open(self._registry_file, "r", encoding="utf-8") as f:
                return json.load(f)
        return {}

    def _save_registry(self):
        """保存用例注册表到文件"""
        os.makedirs(os.path.dirname(self._registry_file), exist_ok=True)
        with open(self._registry_file, "w", encoding="utf-8") as f:
            json.dump(self._registry, f, ensure_ascii=False, indent=2)

    # ── LLM 调用 ──────────────────────────────────────────────────

    def _call_llm(self, prompt):
        """
        调用 LLM 生成测试用例
        
        :param prompt: 提示词
        :return: LLM 生成的内容，若无 LLM 配置则返回模板代码
        """
        if self.llm_client is None:
            return self._generate_template(prompt)

        try:
            if isinstance(self.llm_client, LLMClient):
                return self.llm_client.chat(
                    messages=[{"role": "user", "content": prompt}]
                )
            else:
                response = self.llm_client.chat.completions.create(
                    model=self.config.get("llm.model", "deepseek-chat"),
                    messages=[{"role": "user", "content": prompt}],
                    temperature=self.config.get("llm.temperature", 0.3),
                    max_tokens=self.config.get("llm.max_tokens", 4096),
                )
                return response.choices[0].message.content
        except Exception as e:
            return f"# LLM 调用失败: {e}\n# 请检查 AI 配置\n"

    @staticmethod
    def _generate_template(prompt_data):
        """
        生成测试用例模板（当 LLM 未配置时使用）
        
        :param prompt_data: 提示词数据（未使用）
        :return: 占位符测试模板代码
        """
        return (
            "# AI 生成的测试用例模板\n"
            "# 请配置 LLM API Key 后使用自动生成功能\n"
            "# 当前为模板格式，需根据实际接口补充\n"
            "import pytest\n\n"
            "class TestGenerated:\n"
            "    def test_placeholder(self):\n"
            "        pass\n"
        )
