# CodexRelay

简体中文 | [English](README.en.md)

[![CI](https://github.com/Lortzing/CodexRelay/actions/workflows/ci.yml/badge.svg)](https://github.com/Lortzing/CodexRelay/actions/workflows/ci.yml)
[![GitHub Release](https://img.shields.io/github/v/release/Lortzing/CodexRelay)](https://github.com/Lortzing/CodexRelay/releases)
[![Python](https://img.shields.io/badge/Python-3.11%2B-blue)](https://www.python.org/)
[![License](https://img.shields.io/github/license/Lortzing/CodexRelay)](LICENSE)

CodexRelay 是面向 OpenAI Codex CLI 的多账户与多 API Profile 管理工具，支持 `auth.json`、OpenAI 兼容 API、状态检测、用量展示、手动切换和自动故障转移。

每个 Profile 独立保存完整的 `auth.json` 与 `config.toml`。切换时，CodexRelay 会先备份当前配置，再通过文件锁和原子替换更新 Codex 的活动配置。

## 主要功能

- 导入并管理多个 ChatGPT/Codex `auth.json` 登录配置。
- 管理 `API Key + Base URL + Model` 类型的 OpenAI 兼容 API。
- 首次安装或首次运行时自动导入当前 Codex 配置。
- 手动切换 Profile，并在切换失败时自动回滚。
- 检查 ChatGPT 账户状态、套餐、限额窗口和 Credits。
- 通过 Responses API、Models API 或自定义接口检查第三方 API 状态。
- 按优先级自动故障转移，并在高优先级配置恢复后自动切回。
- 以表格或 JSON 形式展示配置、健康状态、延迟和余额信息。
- 支持 Bash、Zsh 和 Fish 自动补全。
- 提供自更新和可选择保留 Profile 数据的卸载命令。

## 安装

### 使用 GitHub Release 独立程序

每个正式版本会自动生成四个平台包：

| 系统 | 架构 | Release 文件 |
|---|---|---|
| Windows | x86_64 | `codex-relay-<version>-windows-x86_64.zip` |
| macOS | Intel x86_64 | `codex-relay-<version>-macos-x86_64.tar.gz` |
| macOS | Apple Silicon arm64 | `codex-relay-<version>-macos-arm64.tar.gz` |
| Linux | x86_64 | `codex-relay-<version>-linux-x86_64.tar.gz` |

Release 同时提供 `SHA256SUMS`，用于校验下载文件。

Windows：

```powershell
# 解压后，将 cxr.exe 移动到固定目录，并把该目录加入 PATH
cxr.exe --help
```

macOS / Linux：

```bash
chmod +x cxr
mkdir -p ~/.local/bin
mv cxr ~/.local/bin/cxr
cxr --help
```

独立程序包含 Python 运行时和项目依赖，用户不需要另行安装 Python。当前发布产物未进行商业代码签名；Windows SmartScreen 或 macOS Gatekeeper 可能显示安全提示。

### 从源码安装

要求 Python 3.11+ 和 `uv`：

```bash
git clone https://github.com/Lortzing/CodexRelay.git
cd CodexRelay
./install.sh
```

也可以直接从 Git 仓库安装：

```bash
uv tool install --force git+https://github.com/Lortzing/CodexRelay.git
```

安装后可使用：

```bash
cxr --help
codex-relay --help
```

`cxr` 是推荐的短命令。

## 数据目录

默认应用数据目录：

```text
~/.config/codex-relay/
├── profiles/
│   └── <name>/
│       ├── profile.json   # 非敏感元数据
│       ├── auth.json      # 凭据，权限 0600
│       └── config.toml    # 完整 Codex 配置
├── backups/
├── state.json
└── switch.lock
```

Codex 活动配置位于：

```text
~/.codex/auth.json
~/.codex/config.toml
```

可以通过 `CODEX_RELAY_HOME`、`CODEX_HOME` 或全局参数 `--home`、`--codex-home` 修改路径。

## 自动导入当前配置

当 Profile 库为空时，安装过程或首次业务命令会自动导入当前 Codex 配置。导入器能够识别 ChatGPT Token 登录或 API Key 登录，并提取邮箱、套餐、模型、Provider ID 和 Base URL 等非敏感信息。

也可以显式导入：

```bash
cxr import-current
cxr import-current official
```

## 添加 Profile

导入 ChatGPT/Codex `auth.json`：

```bash
cxr add-auth official ~/.codex/auth.json
```

添加 API Profile：

```bash
cxr add-api backup \
  --url https://gateway.example.com/v1 \
  --model gpt-5.6 \
  --api-key 'sk-...'
```

避免 API Key 进入 Shell 历史：

```bash
printf '%s' "$GATEWAY_API_KEY" | cxr add-api backup \
  --url https://gateway.example.com/v1 \
  --model gpt-5.6 \
  --api-key-stdin
```

## 健康检查

Responses API 最小请求：

```bash
cxr add-api backup \
  --url https://gateway.example.com/v1 \
  --model gpt-5.6 \
  --health-mode responses
```

Models API：

```bash
cxr add-api backup \
  --url https://gateway.example.com/v1 \
  --model gpt-5.6 \
  --health-mode models
```

自定义健康接口：

```bash
cxr add-api backup \
  --url https://gateway.example.com/v1 \
  --model gpt-5.6 \
  --health-mode custom \
  --health-endpoint https://gateway.example.com/health \
  --expected-text ok
```

## 状态与手动切换

```bash
cxr status --no-probe
cxr status
cxr status --watch --interval 30
cxr status --json
cxr use official
```

切换前会备份活动配置。替换过程使用进程锁和原子写入；验证失败时会恢复原配置。已运行的 Codex 进程可能缓存认证信息，切换后建议重新启动 Codex。

## 自动切换

按参数顺序确定优先级：

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

策略：

1. 越靠前的 Profile 优先级越高。
2. 当前 Profile 连续失败达到阈值后切换。
3. 高优先级 Profile 连续恢复达到阈值后切回。
4. 恢复切换受冷却时间限制，紧急故障转移不受限制。
5. 所有候选均不健康时，保持当前活动配置不变。

选择健康 Profile 并启动新的 Codex 进程：

```bash
cxr launch -p official -p backup -- exec "say hello"
```

`--` 后的参数会原样传给 `codex`。

## 更新与卸载

更新源码安装版本：

```bash
cxr update
cxr update --yes
```

交互式卸载会询问是否保留 Profile、备份和状态数据：

```bash
cxr uninstall
```

保留数据并跳过确认：

```bash
cxr uninstall --yes
```

永久删除全部 CodexRelay 管理数据：

```bash
cxr uninstall --purge
cxr uninstall --purge --yes
```

卸载不会删除活动的 `~/.codex/auth.json` 和 `~/.codex/config.toml`。

## 发布流程

推送与 `pyproject.toml` 版本一致的标签：

```bash
git tag -a v0.6.0 -m "CodexRelay v0.6.0"
git push origin v0.6.0
```

Release Workflow 会自动：

1. 校验 Git Tag 与项目版本一致。
2. 在四种目标环境中运行测试。
3. 使用 PyInstaller 构建四个独立可执行程序。
4. 对每个程序执行 `cxr --help` 冒烟测试。
5. 生成 ZIP 或 TAR.GZ 平台包。
6. 生成 `SHA256SUMS`。
7. 创建或更新 GitHub Release 并上传全部产物。

## 安全说明

- Profile 目录和凭据文件使用限制性权限。
- API Key 和访问令牌不会显示在状态表或 JSON 输出中。
- 建议使用 `--api-key-stdin`，避免凭据进入 Shell 历史。
- 自定义健康接口和余额接口会收到配置的 Bearer Token。
- 备份中可能包含凭据，需要妥善保护。
- ChatGPT 用量查询依赖非公开稳定接口，未来可能因上游变化失效。

## 开发

```bash
uv sync --extra dev
uv run pytest
uv run cxr --help
uv build --no-sources
```
