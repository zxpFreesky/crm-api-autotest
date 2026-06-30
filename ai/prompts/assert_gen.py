import json


def build_assert_prompt(response_data, description):
    return f"""你是一个 API 测试验证专家。请验证以下接口响应是否符合业务语义描述。

## 业务语义描述
{description}

## 接口响应数据
{json.dumps(response_data, ensure_ascii=False, indent=2) if isinstance(response_data, dict) else response_data}

## 验证要求
请逐项检查:
1. 响应结构是否完整 (有 code/msg/data 等必要字段)
2. 数据内容是否符合业务语义描述
3. 字段值是否合法 (如 token 格式、ID 格式等)
4. 是否存在字段名变更 (如 token→access_token 的语义等价)

## 输出格式
如果验证通过, 第一行输出: PASS
如果验证失败, 第一行输出: FAIL
然后说明具体原因。
"""
