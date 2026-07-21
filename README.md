# CoderRelay

简体中文 | [English](README.en.md)

[![CI](https://github.com/Lortzing/CoderRelay/actions/workflows/ci.yml/badge.svg)](https://github.com/Lortzing/CoderRelay/actions/workflows/ci.yml)
[![GitHub Release](https://img.shields.io/github/v/release/Lortzing/CoderRelay)](https://github.com/Lortzing/CoderRelay/releases)
[![Python](https://img.shields.io/badge/Python-3.11%2B-blue)](https://www.python.org/)
[![License](https://img.shields.io/github/license/Lortzing/CoderRelay)](LICENSE)

CoderRelay 是面向编码智能体 CLI 的账户、Profile 与 API 路由管理工具。当前完整支持 OpenAI Codex CLI；项目命名与架构已解除对单一厂商的绑定，后续将接入 Claude Code。

当前能力包括：

- 管理多个 ChatGPT/Codex 登录 Profile。
- 管理 `API Key + Base URL + Model` 类型的 OpenAI 兼容 API。
- 首次运行时自动导入当前 Codex 配置。
- 手动切换、健康检查、自动故障转移和高优先级恢复切回。
- 展示 ChatGPT 套餐、限额窗口、Credits、API 余额和延迟。
- 通过文件锁、原子写入和备份安全替换活动配置。
- 支持 Bash、Zsh 和 Fish 自动补全。

> Claude Code 支持属于后续功能，当前版本不会修改 Claude Code 的配置。

## 命令

推荐使用短命令：

```bash
cdy --help
```

完整命令也可用：

```bash
coder-relay --help
```

## 安装

### Windows

| 架构 | 安装程序 | 便携版 |
|---|---|---|
| x86 32 位 | `CoderRelay-Setup-<版本>-windows-x86.exe` | `CoderRelay-Portable-<版本>-windows-x86.zip` |
| x86_64 / x64 | `CoderRelay-Setup-<版本>-windows-x86_64.exe` | `CoderRelay-Portable-<版本>-windows-x86_64.zip` |
| ARM64 | `CoderRelay-Setup-<版本>-windows-arm64.exe` | `CoderRelay-Portable-<版本>-windows-arm64.zip` |

安装程序会把 `cdy.exe` 安装到当前用户目录、加入用户 `PATH` 并注册标准卸载程序。

### macOS

| 架构 | 安装镜像 |
|---|---|
| Intel x86_64 | `CoderRelay-<版本>-macOS-x86_64.dmg` |
| Apple Silicon ARM64 | `CoderRelay-<版本>-macOS-arm64.dmg` |

打开 DMG 后运行其中的 `CoderRelay-<版本>.pkg`。命令安装到：

```text
/usr/local/bin/cdy
```

### Linux

| 架构 | 通用包 | Debian/Ubuntu | Fedora/RHEL |
|---|---|---|---|
| x86_64 | `coder-relay-<版本>-linux-x86_64.tar.gz` | `coder-relay_<版本>_amd64.deb` | `coder-relay-<版本>-1.x86_64.rpm` |
| ARM64/AArch64 | `coder-relay-<版本>-linux-aarch64.tar.gz` | `coder-relay_<版本>_arm64.deb` | `coder-relay-<版本>-1.aarch64.rpm` |

```bash
sudo apt install ./coder-relay_<版本>_amd64.deb
# 或
sudo rpm -Uvh ./coder-relay-<版本>-1.x86_64.rpm
```

### 从源码安装

要求 Python 3.11+ 与 `uv`：

```bash
git clone https://github.com/Lortzing/CoderRelay.git
cd CoderRelay
./install.sh
```

也可以直接安装固定 Tag：

```bash
uv tool install --force git+https://github.com/Lortzing/CoderRelay.git@v0.7.0
```

## 快速开始

首次运行会在没有 Profile 时自动导入当前 `$CODEX_HOME/auth.json` 和 `config.toml`：

```bash
cdy status
```

添加登录 Profile：

```bash
cdy add-auth official ~/.codex/auth.json
```

添加 OpenAI 兼容 API：

```bash
cdy add-api backup \
  --url https://gateway.example.com/v1 \
  --model gpt-5.6 \
  --api-key-stdin
```

常用命令：

```bash
cdy status
cdy import-current
cdy use official
cdy auto official backup --watch
cdy launch -p official -p backup --
cdy doctor
cdy update
cdy uninstall
```

## 自动切换规则

1. 参数越靠前，Profile 优先级越高。
2. 当前 Profile 连续失败达到阈值后切换。
3. 高优先级 Profile 连续恢复达到阈值后切回。
4. 恢复切换受冷却时间限制，紧急故障转移不受限制。
5. 所有候选均不健康时，保持当前活动配置不变。

## 数据目录

```text
~/.config/coder-relay/
├── profiles/
├── backups/
├── state.json
└── switch.lock
```

可以通过 `CODER_RELAY_HOME` 覆盖。Codex 活动配置仍位于：

```text
~/.codex/auth.json
~/.codex/config.toml
```

卸载 CoderRelay 不会删除这两个活动文件。

## 更新与卸载

```bash
cdy update
cdy uninstall
cdy uninstall --purge
```

Windows Setup 安装版执行 `cdy uninstall` 时会启动标准卸载器。Linux DEB/RPM 建议使用系统包管理器卸载。独立可执行文件需要从 GitHub Release 下载新版本进行替换。

## 发布

推送与 `pyproject.toml` 版本一致的 Tag：

```bash
git tag -a v0.7.0 -m "CoderRelay v0.7.0"
git push origin v0.7.0
```

Release Workflow 会构建 Windows Setup EXE/ZIP、macOS DMG/PKG、Linux TAR/DEB/RPM，并生成 `SHA256SUMS.txt`。安装包未进行数字签名，Windows SmartScreen 或 macOS Gatekeeper 可能显示安全提示。

## 开发

```bash
uv sync --extra dev
uv run pytest
uv run cdy --help
uv build --no-sources
```

## License

MIT
