# 配置文件说明

本项目所有敏感配置文件均通过 `.gitignore` 排除，**请勿将真实账号密码或 API Key 提交到 Git**。

## 配置文件清单

| 文件 | 用途 | 是否提交 | 模板 |
|------|------|---------|------|
| `test.ini` | 环境 URL / 日志级别 / 通知配置 | ❌ 不提交 | `test.ini.example` |
| `users.yaml` | 测试账号用户名密码 | ❌ 不提交 | `users.yaml.example` |
| `ai_config.yaml` | LLM API Key 等敏感信息 | ❌ 不提交 | `ai_config.yaml.example` |

## 首次使用步骤

```bash
# 1. 克隆仓库
git clone <repository_url>
cd auto_api_rmp_new

# 2. 安装依赖
pip install -r requirements.txt

# 3. 复制配置模板并填入真实数据
cp config/test.ini.example config/test.ini
cp config/users.yaml.example config/users.yaml
cp config/ai_config.yaml.example config/ai_config.yaml

# 4. 编辑配置文件，填入真实的：
#    - test.ini: 修改 [host] 下的 URL、[notify] 下的企业微信 Webhook
#    - users.yaml: 填入测试账号的用户名密码
#    - ai_config.yaml: 填入 LLM 的 API Key

# 5. 运行测试
python run.py --all
```

## 安全提醒

- ✅ `.gitignore` 已配置排除真实配置文件
- ✅ 配置文件模板 `.example` 不含敏感数据，可安全提交
- ⚠️ 如果不小心提交了真实数据，请立即：
  1. 修改相关密码 / Token / API Key
  2. 使用 `git filter-branch` 或 BFG 清理 Git 历史
  3. 强制推送 `git push --force`
