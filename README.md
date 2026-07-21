# CodexRelay

简体中文 | [English](README.en.md)

[![CI](https://github.com/Lortzing/CodexRelay/actions/workflows/ci.yml/badge.svg)](https://github.com/Lortzing/CodexRelay/actions/workflows/ci.yml)
[![GitHub Release](https://img.shields.io/github/v/release/Lortzing/CodexRelay)](https://github.com/Lortzing/CodexRelay/releases)
[![Python](https://img.shields.io/badge/Python-3.11%2B-blue)](https://www.python.org/)
[![License](https://img.shields.io/github/license/Lortzing/CodexRelay)](LICENSE)

CodexRelay 是面向 OpenAI Codex CLI 的多账户与多 API Profile 管理工具，支持 `auth.json`、OpenAI 兼容 API、状态检测、用量展示、手动切换和自动故障转移。

每个 Profile 独立保存完整的 `auth.json` 与 `config.toml`。切换时，CodexRelay 会备份当前配置，并通过文件锁和原子替换更新 Codex 的活动配置。

## 主要功能

- 管理多个 ChatGPT/Codex 登录 Profile。
- 管理 `API Key + Base URL + Model` 类型的 OpenAI 兼容 API。
- 首次运行时自动导入当前 Codex 配置。
- 手动切换、健康检查、故障转移和高优先级恢复切回。
- 展示 ChatGPT 套餐、限额窗口、Credits、API 余额和延迟。
- 支持 Bash、Zsh 和 Fish 自动补全。
- 提供更新与可选择保留 Profile 数据的卸载命令。

## 安装

### Windows

推荐下载对应架构的安装程序：

| 架构 | 安装程序 | 便携版 |
|---|---|---|
| x86 32 位 | `CodexRelay-Setup-<版本>-windows-x86.exe` | `CodexRelay-Portable-<版本>-windows-x86.zip` |
| x86_64 / x64 | `CodexRelay-Setup-<版本>-windows-x86_64.exe` | `CodexRelay-Portable-<版本>-windows-x86_64.zip` |
| ARM64 | `CodexRelay-Setup-<版本>-windows-arm64.exe` | `CodexRelay-Portable-<版本>-windows-arm64.zip` |

`Setup.exe` 会把 `cxr.exe` 安装到用户目录、加入用户 `PATH`，并注册标准卸载程序。安装后重新打开终端：

```powershell
cxr --help
```

Windows 可能对从网络下载的安装程序显示安全提示。

### macOS

| 架构 | 安装镜像 |
|---|---|
| Intel x86_64 | `CodexRelay-<版本>-macOS-x86_64.dmg` |
| Apple Silicon ARM64 | `CodexRelay-<版本>-macOS-arm64.dmg` |

打开 DMG 后双击其中的 `CodexRelay-<版本>.pkg`。安装器会把命令安装到：

```text
/usr/local/bin/cxr
```

安装完成后：

```bash
cxr --help
```

macOS 可能对从网络下载的安装镜像显示安全提示。

### Linux

每种架构同时提供通用压缩包、DEB 和 RPM：

| 架构 | 通用包 | Debian/Ubuntu | Fedora/RHEL |
|---|---|---|---|
| x86_64 | `codex-relay-<版本>-linux-x86_64.tar.gz` | `codex-relay_<版本>_amd64.deb` | `codex-relay-<版本>-1.x86_64.rpm` |
| ARM64/AArch64 | `codex-relay-<版本>-linux-aarch64.tar.gz` | `codex-relay_<版本>_arm64.deb` | `codex-relay-<版本>-1.aarch64.rpm` |

DEB：

```bash
sudo apt install ./codex-relay_<版本>_amd64.deb
```

RPM：

```bash
sudo rpm -Uvh ./codex-relay-<版本>-1.x86_64.rpm
```

通用包：

```bash
tar -xzf codex-relay-<版本>-linux-x86_64.tar.gz
install -m 0755 codex-relay-<版本>-linux-x86_64/cxr ~/.local/bin/cxr
```

### 从源码安装

要求 Python 3.11+ 与 `uv`：

```bash
git clone https://github.com/Lortzing/CodexRelay.git
cd CodexRelay
./install.sh
```

也可以直接安装 Git Tag：

```bash
uv tool install --force git+https://github.com/Lortzing/CodexRelay.git@v0.6.0
```

公开命令：

```bash
cxr --help
codex-relay --help
```

## 校验下载文件

每个 Release 都包含 `SHA256SUMS.txt`：

```bash
sha256sum -c SHA256SUMS.txt
```

## 常用命令

```bash
cxr status
cxr import-current
cxr add-auth official ~/.codex/auth.json
cxr add-api backup --url https://gateway.example.com/v1 --model gpt-5.6
cxr use official
cxr auto official backup --watch
cxr launch -p official -p backup --
cxr doctor
cxr update
cxr uninstall
```

## 自动切换规则

1. 参数越靠前，Profile 优先级越高。
2. 当前 Profile 连续失败达到阈值后切换。
3. 高优先级 Profile 连续恢复达到阈值后切回。
4. 恢复切换受冷却时间限制，紧急故障转移不受限制。
5. 所有候选均不健康时，保持当前活动配置不变。

## 数据目录

```text
~/.config/codex-relay/
├── profiles/
├── backups/
├── state.json
└── switch.lock
```

Codex 活动配置仍位于：

```text
~/.codex/auth.json
~/.codex/config.toml
```

卸载 CodexRelay 不会删除这两个活动文件。

## 更新与卸载

源码或 `uv tool` 安装：

```bash
cxr update
cxr uninstall
cxr uninstall --purge
```

Windows Setup 安装版执行 `cxr uninstall` 时会启动标准卸载器。Linux DEB/RPM 建议使用系统包管理器卸载。macOS PKG 安装到系统目录，删除时通常需要管理员权限。

## 发布

推送与 `pyproject.toml` 版本一致的标签：

```bash
git tag -a v0.6.0 -m "CodexRelay v0.6.0"
git push origin v0.6.0
```

Release Workflow 会在原生 Runner 上构建 Windows Setup EXE、macOS DMG/PKG 和 Linux TAR/DEB/RPM，执行冒烟测试，生成 `SHA256SUMS.txt`，再上传到 GitHub Release。

## 安全说明

- Profile 和备份中包含凭据，应妥善保护。
- API Key 和访问令牌不会显示在状态表或 JSON 输出中。
- 建议使用 `--api-key-stdin`，避免凭据进入 Shell 历史。
- Responses API 健康检查可能消耗少量 Token。
- ChatGPT 用量查询依赖非公开稳定接口，未来可能因上游变化失效。

## 开发

```bash
uv sync --extra dev
uv run pytest
uv run cxr --help
uv build --no-sources
```
