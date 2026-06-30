import json


def build_healing_prompt(error_info, api_metadata, response):
    api_info = json.dumps(api_metadata, ensure_ascii=False, indent=2) if api_metadata else "无"
    resp_info = json.dumps(response, ensure_ascii=False, indent=2) if response else "无"

    return f"""你是一个 API 测试自愈引擎。分析以下测试失败信息，判断是否为接口变更导致，并给出修复建议。

## 错误信息
{error_info}

## 接口文档 (当前定义)
{api_info}

## 实际响应
{resp_info}

## 分析要求
1. 判断失败原因: 是接口变更、数据问题、还是代码Bug?
2. 如果是接口变更 (如字段名改变), 请给出具体的字段映射关系
3. 给出修复建议和修复后的代码片段

## 输出格式
- 原因分析: ...
- 修复建议: ...
- 修复代码: ```python ... ```
"""


def build_root_cause_prompt(failure_record, analysis, context):
    ctx_info = json.dumps(context, ensure_ascii=False, indent=2) if context else "无"

    return f"""你是一个 API 测试根因分析专家。请深入分析以下测试失败的根本原因。

## 失败记录
{json.dumps(failure_record, ensure_ascii=False, indent=2)}

## 初步分析
{json.dumps(analysis, ensure_ascii=False, indent=2)}

## 附加上下文
{ctx_info}

## 分析要求
1. 不要只看错误堆栈，要分析业务层面的根因
2. 判断是否与最近的代码变更/接口变更相关
3. 评估影响范围 (仅影响此用例还是影响整个模块)
4. 给出优先级建议 (P0-P3)
5. 给出具体的修复或排查步骤

## 输出格式
请以结构化的方式输出分析报告。
"""
