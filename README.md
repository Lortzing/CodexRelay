# CodexRelay

简体中文 | [English](README.en.md)

[![CI](https://github.com/Lortzing/CodexRelay/actions/workflows/ci.yml/badge.svg)](https://github.com/Lortzing/CodexRelay/actions/workflows/ci.yml)
[![GitHub Release](https://img.shields.io/github/v/release/Lortzing/CodexRelay)](https://github.com/Lortzing/CodexRelay/releases)
[![Python](https://img.shields.io/badge/Python-3.11%2B-blue)](https://www.python.org/)
[![License](https://img.shields.io/github/license/Lortzing/CodexRelay)](LICENSE)

CodexRelay 是面向 OpenAI Codex CLI 的多账户与多 API 配置管理工具，支持 `auth.json`、OpenAI 兼容 API、状态检测、用量展示、手动切换和自动故障转移。

每个 Profile 都独立保存完整的 `auth.json` 与 `config.toml`。切换时，CodexRelay 会先备份当前配置，再通过文件锁和原子替换更新 Codex 的活动配置。

## 主要功能

- 导入并管理多个 ChatGPT/Codex `auth.json` 登录配置。
- 管理 `API Key + Base URL + Model` 类型的 OpenAI 兼容 API 配置。
- 首次安装或首次运行时自动导入当前 Codex 配置。
- 手动切换 Profile，并在切换失败时自动回滚。
- 检查 ChatGPT 账户状态、套餐、限额窗口和 Credits。
- 通过 Responses API、Models API 或自定义接口检查第三方 API 状态。
- 按优先级自动故障转移，并在高优先级配置恢复后自动切回。
- 以表格或 JSON 形式展示配置、健康状态、延迟和余额信息。
- 支持 Bash、Zsh 和 Fish 自动补全。
- 提供自更新和可选择保留 Profile 数据的卸载命令。

## 环境要求

- Python 3.11 或更高版本。
- 推荐使用 `uv` 安装和管理。
- 实际使用 Codex 时，需要系统中存在 `codex` 命令。
- 健康检查和用量查询需要网络连接。

## 安装

```bash
git clone https://github.com/Lortzing/CodexRelay.git
cd CodexRelay
./install.sh
```

安装后可使用：

```bash
cxr --help
codex-relay --help
```

`cxr` 是推荐的短命令。安装脚本会静默配置当前 Shell 的自动补全，并在 Profile 库为空时自动导入当前 `$CODEX_HOME/auth.json` 和 `config.toml`。

也可以直接从 GitHub 安装：

```bash
uv tool install --force git+https://github.com/Lortzing/CodexRelay.git
cxr status --no-probe
```

## 数据目录

```text
~/.config/codex-relay/
├── profiles/
│   └── <name>/
│       ├── profile.json   # 非敏感元数据
│       ├── auth.json      # 认证信息，权限 0600
│       └── config.toml    # 该 Profile 的完整 Codex 配置
├── backups/
├── state.json
└── switch.lock
```

Codex 当前活动配置位于：

```text
~/.codex/auth.json
~/.codex/config.toml
```

可通过 `CODEX_RELAY_HOME`、`CODEX_HOME`，或全局参数 `--home`、`--codex-home` 修改目录。

## 自动导入当前 Codex 配置

当尚未存在任何受管理 Profile 时，安装过程或首次业务命令会自动读取当前 Codex 配置。导入器能够识别 ChatGPT Token 登录、API Key 登录、当前模型、Provider ID、Base URL、邮箱和套餐等非敏感元数据。

也可以显式执行：

```bash
cxr import-current
cxr import-current official
```

为 API 配置指定健康检查和余额接口：

```bash
cxr import-current gateway \
  --health-mode responses \
  --balance-url https://gateway.example.com/account/credits \
  --balance-path data.balance
```

## 添加 Profile

导入 ChatGPT/Codex `auth.json`：

```bash
cxr add-auth official ~/.codex/auth.json
```

指定基础配置和模型：

```bash
cxr add-auth official ./auth.json \
  --config ~/.codex/config.toml \
  --model gpt-5.6
```

添加 API Key 配置：

```bash
cxr add-api backup \
  --url https://gateway.example.com/v1 \
  --model gpt-5.6 \
  --api-key 'sk-...'
```

为避免 API Key 进入 Shell 历史，推荐通过标准输入传入：

```bash
printf '%s' "$GATEWAY_API_KEY" | cxr add-api backup \
  --url https://gateway.example.com/v1 \
  --model gpt-5.6 \
  --api-key-stdin
```

未提供 API Key 参数时，CodexRelay 会通过隐藏输入提示读取密钥。

## API 健康检查

Responses API 检查会发送一个最小请求，可能消耗少量 Token：

```bash
cxr add-api backup \
  --url https://gateway.example.com/v1 \
  --model gpt-5.6 \
  --health-mode responses
```

Models API 检查：

```bash
cxr add-api backup \
  --url https://gateway.example.com/v1 \
  --model gpt-5.6 \
  --health-mode models
```

自定义健康检查：

```bash
cxr add-api backup \
  --url https://gateway.example.com/v1 \
  --model gpt-5.6 \
  --health-mode custom \
  --health-endpoint https://gateway.example.com/health \
  --expected-text ok
```

不同 API Provider 没有统一的余额协议。可为具体 Provider 配置余额接口和 JSON 路径：

```bash
cxr add-api backup \
  --url https://gateway.example.com/v1 \
  --model gpt-5.6 \
  --balance-url https://gateway.example.com/account/credits \
  --balance-path data.balance
```

## 状态展示与手动切换

```bash
cxr status --no-probe
cxr status
cxr status --watch --interval 30
cxr status --json
cxr use official
cxr use backup
```

`status` 会统一展示当前活动 Profile、类型、模型、API 地址、健康状态、延迟、ChatGPT 套餐与限额、自定义 API 余额和诊断信息。

手动切换前会备份当前活动文件。替换过程使用进程锁和原子写入；验证失败时会恢复原配置。已经运行的 Codex 进程可能缓存认证信息，因此手动切换后应重新启动 Codex。

## 自动切换

按优先级执行一次检查：

```bash
cxr auto official backup
```

持续监控：

```bash
cxr auto official backup \
  --watch \
  --interval 60 \
  --fail-threshold 2 \
  --recover-threshold 2 \
  --cooldown 300
```

自动切换策略：

1. 参数顺序越靠前，优先级越高。
2. 当前 Profile 连续失败达到阈值后，切换到优先级最高的健康 Profile。
3. 更高优先级 Profile 连续恢复达到阈值后，自动切回。
4. 恢复切换受冷却时间限制；紧急故障转移不受冷却时间阻止。
5. 所有候选都不健康时，保持当前活动配置不变。

选择健康 Profile 后启动新的 Codex 进程：

```bash
cxr launch -p official -p backup -- exec "say hello"
```

`--` 后面的参数会原样传递给 `codex`。

## 更新与卸载

从 GitHub `main` 分支更新，Profile 和当前 Codex 配置不会被修改：

```bash
cxr update
cxr update --yes
```

交互式卸载会询问是否保留 Profile、备份和状态：

```bash
cxr uninstall
```

跳过确认并默认保留数据：

```bash
cxr uninstall --yes
```

连同所有 CodexRelay 管理数据一起删除：

```bash
cxr uninstall --purge
cxr uninstall --purge --yes
```

卸载不会删除当前活动的 `~/.codex/auth.json` 或 `~/.codex/config.toml`。

## 后台监控

systemd 用户服务：

```bash
mkdir -p ~/.config/systemd/user
cp examples/codex-relay.service ~/.config/systemd/user/
systemctl --user daemon-reload
systemctl --user enable --now codex-relay.service
journalctl --user -u codex-relay.service -f
```

macOS launchd：先修改 `examples/com.codex-relay.auto.plist` 中的可执行文件绝对路径，然后执行：

```bash
mkdir -p ~/Library/LaunchAgents
cp examples/com.codex-relay.auto.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.codex-relay.auto.plist
```

## ChatGPT 用量查询

对于 ChatGPT Profile，CodexRelay 会从 `auth.json` 读取 access token 和 account id，然后请求：

```text
GET https://chatgpt.com/backend-api/wham/usage
Authorization: Bearer <access token>
ChatGPT-Account-Id: <account id>
```

该接口属于不稳定的实现接口，并非有稳定承诺的公开 API。使用 `cxr status --no-probe` 可完全跳过网络探测。

## 安全说明

- Profile 目录在支持的平台上使用限制性权限。
- 认证文件和状态文件使用 `0600` 权限。
- 状态表和 JSON 输出不会显示 API Key 或 access token。
- 推荐使用 `--api-key-stdin`，避免密钥进入 Shell 历史。
- 自定义健康检查和余额接口会收到 Bearer Token。
- 备份中包含认证信息，应妥善保护。

## 自动化测试与发布

项目包含两套 GitHub Actions：

- `CI`：在推送和 Pull Request 时，测试 Python 3.11、3.12、3.13，并覆盖 Linux、macOS 和 Windows。
- `Release`：推送 `v*` 标签后，校验标签版本、运行测试、构建 Wheel 和源码包、执行安装冒烟测试，并自动创建 GitHub Release。

发布新版本：

```bash
# 先在 pyproject.toml 和 src/codex_relay/__init__.py 中更新版本

git tag v0.6.0
git push origin v0.6.0
```

GitHub Release 会自动附带：

```text
codex_relay-<version>-py3-none-any.whl
codex_relay-<version>.tar.gz
```

可选的 PyPI 发布默认关闭。配置 PyPI Trusted Publisher、创建 GitHub Environment `pypi`，并将仓库变量 `PUBLISH_TO_PYPI` 设置为 `true` 后，同一标签工作流会自动执行 `uv publish`。

## 诊断与开发

```bash
cxr doctor
cxr doctor --json

uv sync --extra dev
uv run pytest
uv build --no-sources
```
