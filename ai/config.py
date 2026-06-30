import os

import yaml


class AIConfig:
    _instance = None

    def __init__(self, config_path=None):
        if config_path is None:
            config_path = os.path.join(
                os.path.dirname(os.path.dirname(__file__)),
                "config", "ai_config.yaml"
            )
        self.config_path = config_path
        self._config = self._load()

    def _load(self):
        if not os.path.exists(self.config_path):
            return self._defaults()
        with open(self.config_path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}

    @staticmethod
    def _defaults():
        return {
            "llm": {
                "provider": "deepseek",
                "model": "deepseek-chat",
                "api_key": "",
                "base_url": "https://api.deepseek.com",
                "temperature": 0.3,
                "max_tokens": 4096,
            },
            "providers": {},
            "case_generation": {
                "enable_negative": True,
                "enable_boundary": True,
                "enable_security": True,
                "max_cases_per_api": 10,
            },
            "self_healing": {
                "enabled": True,
                "auto_fix": False,
                "max_retries": 3,
            },
            "assertion": {
                "semantic_check": True,
                "schema_check": True,
            },
        }

    def get(self, key, default=None):
        keys = key.split(".")
        value = self._config
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
            else:
                return default
            if value is None:
                return default
        return value

    @property
    def llm_config(self):
        return self._config.get("llm", {})

    @property
    def case_gen_config(self):
        return self._config.get("case_generation", {})

    @property
    def self_healing_config(self):
        return self._config.get("self_healing", {})

    def create_llm_client(self, provider=None):
        """
        根据 AI 配置创建 LLM 客户端
        :param provider: 指定 provider (如 "deepseek", "qwen"), 为空则用配置文件中的默认值
        :return: LLMClient 实例
        """
        from .llm_client import LLMClient

        target = provider or self.get("llm.provider", "deepseek")

        provider_overrides = self.get(f"providers.{target}", {})

        api_key = (
            provider_overrides.get("api_key")
            or self.get("llm.api_key", "")
        )
        base_url = (
            provider_overrides.get("base_url")
            or self.get("llm.base_url", "")
        )

        return LLMClient(
            provider=target,
            api_key=api_key,
            model=self.get("llm.model"),
            base_url=base_url,
            temperature=self.get("llm.temperature", 0.3),
            max_tokens=self.get("llm.max_tokens", 4096),
        )

    def switch_provider(self, provider, model=None, api_key=None):
        """
        切换 LLM 提供商
        :param provider: 提供商名称 (deepseek/qwen/zhipu/moonshot/doubao/hunyuan/siliconflow/openai)
        :param model: 模型名称 (可选, 不传则使用该 provider 的默认模型)
        :param api_key: API Key (可选, 不传则使用配置文件中的值)
        """
        from .llm_client import PROVIDER_PRESETS

        preset = PROVIDER_PRESETS.get(provider, {})
        provider_config = self.get(f"providers.{provider}", {})

        self._config["llm"]["provider"] = provider
        self._config["llm"]["base_url"] = (
            provider_config.get("base_url") or preset.get("base_url", "")
        )

        if model:
            self._config["llm"]["model"] = model
        elif preset.get("models"):
            self._config["llm"]["model"] = list(preset["models"].keys())[0]

        if api_key:
            self._config["llm"]["api_key"] = api_key
        elif provider_config.get("api_key"):
            self._config["llm"]["api_key"] = provider_config["api_key"]

    def list_providers(self):
        """
        列出所有支持的 LLM 提供商及其模型
        """
        from .llm_client import PROVIDER_PRESETS
        return PROVIDER_PRESETS
