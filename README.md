# CodexRelay

简体中文 | [English](README.en.md)

[![CI](https://github.com/Lortzing/CodexRelay/actions/workflows/ci.yml/badge.svg)](https://github.com/Lortzing/CodexRelay/actions/workflows/ci.yml)
[![GitHub Release](https://img.shields.io/github/v/release/Lortzing/CodexRelay)](https://github.com/Lortzing/CodexRelay/releases)
[![Python](https://img.shields.io/badge/Python-3.11%2B-blue)](https://www.python.org/)
[![License](https://img.shields.io/github/license/Lortzing/CodexRelay)](LICENSE)

CodexRelay 是面向 OpenAI Codex CLI 的多账户与多 API 配置管理工具，支持 `auth.json`、OpenAI 兼容 API、状态检测、用量展示、手动切换和自动故障转移。

每个 Profile 独立保存完整的 `auth.json` 与 `config.toml`。切换时，CodexRelay 会备份当前配置，并通过文件锁和原子替换更新 Codex 的活动配置。

## 主要功能

- 管理多个 ChatGPT/Codex 登录 Profile。
- 管理 `API Key + Base URL + Model` 类型的 OpenAI 兼容 API。
- 首次安装或首次运行时自动导入当前 Codex 配置。
- 手动切换 Profile，并在失败时自动回滚。
- 展示 ChatGPT 套餐、限额窗口、Credits、API 余额和延迟。
- 使用 Responses API、Models API 或自定义端点执行健康检查。
- 按优先级自动故障转移，并在高优先级配置恢复后自动切回。
- 支持 Bash、Zsh 和 Fish 自动补全。
- 提供更新和可选择保留 Profile 数据的卸载命令。

## 安装

### 方式一：下载独立可执行文件

在 [Releases](https://github.com/Lortzing/CodexRelay/releases) 中下载与系统和处理器匹配的压缩包。独立版不需要预先安装 Python。

| 系统 | 架构 | Release 文件 |
|---|---|---|
| Windows | 32 位 x86 | `codex-relay-<版本>-windows-x86.zip` |
| Windows | x86_64 / x64 | `codex-relay-<版本>-windows-x86_64.zip` |
| Windows | ARM64 | `codex-relay-<版本>-windows-arm64.zip` |
| macOS | Intel x86_64 | `codex-relay-<版本>-macos-x86_64.tar.gz` |
| macOS | Apple Silicon ARM64 | `codex-relay-<版本>-macos-arm64.tar.gz` |
| Linux | x86_64 / AMD64 | `codex-relay-<版本>-linux-x86_64.tar.gz` |
| Linux | ARM64 / AArch64 | `codex-relay-<版本>-linux-aarch64.tar.gz` |

Linux/macOS：

```bash
mkdir -p ~/.local/bin
tar -xzf codex-relay-<版本>-<平台>.tar.gz
install -m 0755 codex-relay-<版本>-<平台>/cxr ~/.local/bin/cxr
cxr --help
```

Windows：解压后将 `cxr.exe` 放入 PATH 中的目录，再运行：

```powershell
cxr.exe --help
```

每个 Release 都提供 `SHA256SUMS.txt`。下载后建议校验：

```bash
sha256sum -c SHA256SUMS.txt
```

当前发布的可执行文件未进行商业代码签名。macOS 或 Windows 可能显示系统安全提示；请确认文件来自本仓库 Release，并先核对 SHA-256。

### 方式二：使用 uv 从源码安装

```bash
git clone https://github.com/Lortzing/CodexRelay.git
cd CodexRelay
./install.sh
```

或者：

```bash
uv tool install --force git+https://github.com/Lortzing/CodexRelay.git
cxr status --no-probe
```

公开命令为：

```bash
cxr --help
codex-relay --help
```

`cxr` 是推荐短命令。

## 首次自动导入

当 Profile 库为空时，安装过程或首次业务命令会自动导入：

```text
$CODEX_HOME/auth.json
$CODEX_HOME/config.toml
```

未设置 `CODEX_HOME` 时使用：

```text
~/.codex/auth.json
~/.codex/config.toml
```

也可以显式导入：

```bash
cxr import-current
cxr import-current official
```

## 添加 Profile

导入 ChatGPT/Codex 登录配置：

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

## 状态和手动切换

```bash
cxr status
cxr status --no-probe
cxr status --watch --interval 30
cxr status --json
cxr use official
```

现有 Codex 进程可能缓存认证信息。切换后建议重新启动 Codex。

## 自动切换

单次判断：

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
2. 当前 Profile 达到连续失败阈值后切换。
3. 高优先级 Profile 达到连续恢复阈值后切回。
4. 恢复切换受冷却时间限制，紧急故障转移不受限制。
5. 所有候选都不健康时保持当前配置不变。

选择健康 Profile 后启动新的 Codex 进程：

```bash
cxr launch -p official -p backup -- exec "say hello"
```

`--` 后的参数会原样传给 `codex`。

## 更新

通过 `uv tool`、`pipx` 或源码方式安装时：

```bash
cxr update
cxr update --yes
```

独立可执行文件应从 GitHub Releases 下载新版本并替换旧文件。独立版不会静默覆盖自身。

## 卸载

交互式选择是否保留 Profile、备份和状态：

```bash
cxr uninstall
```

跳过确认并保留数据：

```bash
cxr uninstall --yes
```

彻底删除所有 CodexRelay 管理数据：

```bash
cxr uninstall --purge
cxr uninstall --purge --yes
```

独立可执行版本会同时删除自身；Windows 上会在当前进程退出后完成删除。任何卸载模式都不会删除活动的 `~/.codex/auth.json` 或 `~/.codex/config.toml`。

## 数据目录

```text
~/.config/codex-relay/
├── profiles/
│   └── <name>/
│       ├── profile.json
│       ├── auth.json
│       └── config.toml
├── backups/
├── state.json
└── switch.lock
```

可通过 `CODEX_RELAY_HOME`、`CODEX_HOME`、`--home` 和 `--codex-home` 覆盖路径。

## 自动发布

推送与项目版本一致的标签：

```bash
git tag -a v0.6.0 -m "CodexRelay v0.6.0"
git push origin v0.6.0
```

Release Workflow 会：

1. 校验标签与 `pyproject.toml` 版本一致。
2. 运行完整测试。
3. 在目标 OS 和 CPU 架构的原生 Runner 上构建独立可执行文件。
4. 对每个可执行文件执行 `--help` 冒烟测试。
5. 打包 7 个平台产物并生成 `SHA256SUMS.txt`。
6. 创建或更新 GitHub Release。

## 安全说明

- Profile 和备份中包含凭据，应妥善保护。
- 凭据文件在支持的平台上使用 `0600` 权限。
- 状态表和 JSON 输出不会打印 API Key 或 Access Token。
- Responses API 健康检查可能消耗少量 Token。
- ChatGPT 用量查询依赖非公开稳定接口，可能因上游变化而失效。

## 开发

```bash
uv sync --extra dev
uv run pytest
uv build --no-sources
```
