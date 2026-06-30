# 测试报告目录

本目录存放测试运行生成的报告，每次执行自动覆盖或追加。

## 报告类型

```
reports/
├── _report.html              # pytest-testreport 生成的 HTML 报告（默认）
├── history.json              # 历史执行结果汇总（用于趋势分析）
└── 2026-05-20_14_22_58_report.json   # JSON 结构化报告（按时间戳命名）
```

## 报告生成方式

### HTML 报告

由 `pytest.ini` 中的 `addopts` 配置自动生成：

```ini
[pytest]
addopts = -v -s --report=_report.html --title=测试报告 --tester=zouxp --template=3
```

支持的 template：
- `template=1`: 简洁样式
- `template=2`: 标准样式
- `template=3`: 详细样式（含跳过筛选，推荐）

### JSON 报告

由 `ReportMCPClient.export_json_report()` 生成，结构：

```json
{
  "summary": {
    "total": 10,
    "passed": 6,
    "failed": 2,
    "skipped": 2,
    "pass_rate": "60.00",
    "total_duration": 7.553
  },
  "results": [
    {
      "test_name": "add_clue",
      "status": "pass",
      "duration": 0.342,
      "timestamp": "2026-05-20 13:59:07"
    }
  ]
}
```

### 历史趋势

由 `ReportMCPClient.save_to_history()` 维护，每次执行追加一条：

```json
[
  {
    "success": 6,
    "all": 10,
    "fail": 2,
    "skip": 2,
    "runtime": "7.553 S",
    "begin_time": "2026-05-20 13:59:07",
    "pass_rate": "60.00"
  }
]
```

## 查看报告

测试运行完成后：

```bash
# Windows
start reports/_report.html

# macOS
open reports/_report.html

# Linux
xdg-open reports/_report.html
```

## 企业微信推送

配置 `config/test.ini` 中的 `[notify]` 段后，测试结束自动推送结果到企业微信群：

```ini
[notify]
wecom_webhook=https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=你的key
wecom_msg_type=template_card
```

## 安全说明

- 报告文件**不提交到 Git**（已在 `.gitignore` 中排除）
- HTML 报告可能包含接口响应数据、测试账号信息
- JSON 报告含完整的请求/响应快照，仅供内部团队查看
