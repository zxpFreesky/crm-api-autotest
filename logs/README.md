# 日志目录

本目录存放测试运行日志，按日自动滚动生成。

## 日志格式

```
logs/
├── 2026年_05月_18日.log     # 按日生成
├── 2026年_05月_19日.log
└── 2026年_05月_20日.log
```

## 日志级别

在 `config/test.ini` 中配置：

```ini
[level]
logger=debug     # 全局日志级别
ch=DEBUG         # 控制台输出级别
fh=INFO          # 文件输出级别
```

## 日志内容示例

```
2026-05-20 13:59:07,123-INFO:[add_clue] 用例标题: 添加线索
2026-05-20 13:59:07,124-INFO:[add_clue] 账号: sale_account_1 (ca-zouxp), 请求: POST /api/admin/customer-clue/add
2026-05-20 13:59:07,250-INFO:[add_clue] 实际响应: 状态码=200, body={"code":200,"message":"success"...}
2026-05-20 13:59:07,251-INFO:[add_clue] 断言通过: code in [200, 0], 实际=200
```

## 安全说明

- 日志文件**不提交到 Git**（已在 `.gitignore` 中排除）
- 日志可能包含账号、Token、业务数据等敏感信息
- 生产环境建议配置日志轮转和清理策略
