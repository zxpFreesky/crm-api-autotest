from openai import OpenAI


PROVIDER_PRESETS = {
    "deepseek": {
        "base_url": "https://api.deepseek.com",
        "models": {
            "deepseek-chat": "DeepSeek-V3 通用模型，推荐用于用例生成、断言分析",
            "deepseek-reasoner": "DeepSeek-R1 推理模型，适合复杂根因分析",
        },
    },
    "qwen": {
        "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "models": {
            "qwen-plus": "通义千问 Plus，性价比高，推荐日常使用",
            "qwen-turbo": "通义千问 Turbo，速度快，适合断言校验",
            "qwen-max": "通义千问 Max，能力最强，适合复杂场景",
            "qwen-coder-plus": "通义千问代码模型，适合用例生成",
        },
    },
    "zhipu": {
        "base_url": "https://open.bigmodel.cn/api/paas/v4",
        "models": {
            "glm-4-plus": "智谱 GLM-4 Plus，综合能力强",
            "glm-4-flash": "智谱 GLM-4 Flash，速度快成本低",
            "glm-4": "智谱 GLM-4 标准版",
            "codegeex-4": "智谱代码模型，适合用例生成",
        },
    },
    "moonshot": {
        "base_url": "https://api.moonshot.cn/v1",
        "models": {
            "moonshot-v1-8k": "Kimi 8K 上下文",
            "moonshot-v1-32k": "Kimi 32K 上下文",
            "moonshot-v1-128k": "Kimi 128K 长上下文",
        },
    },
    "doubao": {
        "base_url": "https://ark.cn-beijing.volces.com/api/v3",
        "models": {
            "doubao-pro-4k": "豆包 Pro，字节跳动大模型",
            "doubao-pro-32k": "豆包 Pro 32K",
            "doubao-pro-128k": "豆包 Pro 128K",
        },
    },
    "hunyuan": {
        "base_url": "https://api.hunyuan.cloud.tencent.com/v1",
        "models": {
            "hunyuan-lite": "腾讯混元 Lite，免费额度",
            "hunyuan-standard": "腾讯混元标准版",
            "hunyuan-pro": "腾讯混元 Pro",
        },
    },
    "siliconflow": {
        "base_url": "https://api.siliconflow.cn/v1",
        "models": {
            "Qwen/Qwen2.5-72B-Instruct": "硅基流动 Qwen2.5-72B",
            "deepseek-ai/DeepSeek-V3": "硅基流动 DeepSeek-V3",
            "THUDM/glm-4-9b-chat": "硅基流动 GLM-4-9B",
        },
    },
    "openai": {
        "base_url": "https://api.openai.com/v1",
        "models": {
            "gpt-4o": "GPT-4o",
            "gpt-4o-mini": "GPT-4o Mini，性价比高",
            "gpt-4-turbo": "GPT-4 Turbo",
        },
    },
}


class LLMClient:
    """
    统一 LLM 客户端适配器
    支持所有兼容 OpenAI 协议的国产大模型:
    - DeepSeek (deepseek-chat / deepseek-reasoner)
    - 通义千问 (qwen-plus / qwen-turbo / qwen-max)
    - 智谱 (glm-4-plus / glm-4-flash)
    - Kimi/Moonshot
    - 豆包/字节
    - 腾讯混元
    - 硅基流动
    - OpenAI
    """

    def __init__(self, provider="deepseek", api_key="", model=None, base_url=None,
                 temperature=0.3, max_tokens=4096, **kwargs):
        self.provider = provider
        self.api_key = api_key
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.extra_kwargs = kwargs

        preset = PROVIDER_PRESETS.get(provider, {})

        self.base_url = base_url or preset.get("base_url", "https://api.deepseek.com")

        if self.model is None:
            default_models = {
                "deepseek": "deepseek-chat",
                "qwen": "qwen-plus",
                "zhipu": "glm-4-flash",
                "moonshot": "moonshot-v1-8k",
                "doubao": "doubao-pro-4k",
                "hunyuan": "hunyuan-lite",
                "siliconflow": "Qwen/Qwen2.5-72B-Instruct",
                "openai": "gpt-4o",
            }
            self.model = default_models.get(provider, "deepseek-chat")

        self._client = OpenAI(
            api_key=self.api_key,
            base_url=self.base_url,
        )

    def chat(self, messages, model=None, temperature=None, max_tokens=None, **kwargs):
        """
        发送聊天请求 (兼容 OpenAI 协议)
        :param messages: 消息列表 [{"role": "user", "content": "..."}]
        :param model: 覆盖默认模型
        :param temperature: 覆盖默认温度
        :param max_tokens: 覆盖默认最大 token
        :return: 响应文本
        """
        merged_kwargs = {**self.extra_kwargs, **kwargs}
        response = self._client.chat.completions.create(
            model=model or self.model,
            messages=messages,
            temperature=temperature if temperature is not None else self.temperature,
            max_tokens=max_tokens or self.max_tokens,
            **merged_kwargs,
        )
        return response.choices[0].message.content

    def chat_with_usage(self, messages, **kwargs):
        """
        发送请求并返回内容和 token 用量
        """
        response = self._client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=self.temperature,
            max_tokens=self.max_tokens,
            **kwargs,
        )
        return {
            "content": response.choices[0].message.content,
            "model": response.model,
            "usage": {
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens,
            } if response.usage else None,
        }

    @property
    def raw_client(self):
        return self._client

    @staticmethod
    def list_providers():
        return {
            name: {
                "base_url": preset["base_url"],
                "models": list(preset["models"].keys()),
            }
            for name, preset in PROVIDER_PRESETS.items()
        }

    @staticmethod
    def get_provider_info(provider):
        preset = PROVIDER_PRESETS.get(provider)
        if preset is None:
            return None
        return {
            "provider": provider,
            "base_url": preset["base_url"],
            "models": preset["models"],
        }
