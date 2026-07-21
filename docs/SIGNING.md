# CodexRelay 签名与公证

CodexRelay 的 Release Workflow 已支持：

- Windows：对 `cxr.exe`、Setup EXE 和 Inno Setup 卸载器执行 Authenticode 签名。
- macOS：使用 Developer ID Application 签署 PyInstaller 产物，使用 Developer ID Installer 签署 PKG，并通过 Apple Notary Service 公证和 staple PKG/DMG。
- 未配置完整凭据时仍会构建安装包，但文件名会带 `-unsigned`。

签名证书和私钥必须由项目所有者申请并保管。它们涉及个人或企业身份验证，不能由第三方代为创建或上传。

## Windows Authenticode

### 1. 获取代码签名证书

需要从受 Windows 信任的 CA 或云签名服务获取代码签名证书。公开信任的代码签名证书通常要求私钥存储在硬件令牌、HSM 或云签名服务中。

当前 Workflow 内置的是 **PFX 导入模式**，适用于你能够合法导出为 `.pfx/.p12` 的证书。若供应商只提供硬件令牌或云签名 API，需要把 `scripts/build_windows_installer.ps1` 中的 SignTool 调用替换为供应商客户端，例如 Azure Trusted Signing、DigiCert KeyLocker 或 SSL.com eSigner。

自签名证书只能用于内部测试，不能消除普通用户看到的“未知发布者”警告。

### 2. 准备 PFX

确保 PFX：

- 包含私钥；
- 设置了强密码；
- Enhanced Key Usage 包含 Code Signing；
- 未提交到 Git 仓库。

编码为单行 Base64：

PowerShell：

```powershell
[Convert]::ToBase64String([IO.File]::ReadAllBytes("codesign.pfx")) | Set-Clipboard
```

macOS：

```bash
base64 -i codesign.pfx | tr -d '\n' | pbcopy
```

Linux：

```bash
base64 -w 0 codesign.pfx
```

### 3. 配置 GitHub Secrets

仓库进入：

```text
Settings → Secrets and variables → Actions → New repository secret
```

添加：

| Secret | 内容 |
|---|---|
| `WINDOWS_CERTIFICATE_PFX_BASE64` | PFX 的单行 Base64 |
| `WINDOWS_CERTIFICATE_PASSWORD` | PFX 密码 |

配置完整后，Workflow 会：

1. 临时导入证书到 `CurrentUser\My`；
2. 使用 SHA-256 和 RFC 3161 时间戳签署 `cxr.exe`；
3. 让 Inno Setup 签署 Setup EXE 和卸载器；
4. 使用 `signtool verify /pa` 验证签名；
5. 删除 Runner 上的临时证书。

默认时间戳服务：

```text
https://timestamp.digicert.com
```

### 4. 本地验证

```powershell
Get-AuthenticodeSignature .\cxr.exe | Format-List
Get-AuthenticodeSignature .\CodexRelay-Setup-*.exe | Format-List
```

或：

```powershell
signtool verify /pa /v .\CodexRelay-Setup-0.6.0-windows-x86_64.exe
```

## macOS Developer ID 与公证

### 1. 加入 Apple Developer Program

需要有效的 Apple Developer Program 会员资格。创建两类证书：

- `Developer ID Application`：签署 `cxr` 和 DMG；
- `Developer ID Installer`：签署 PKG。

两者不可互换。

### 2. 导出 P12

在“钥匙串访问”中找到证书及其私钥，分别导出：

```text
DeveloperIDApplication.p12
DeveloperIDInstaller.p12
```

为两个文件设置强密码。

查看准确的 Identity 名称：

```bash
security find-identity -v -p codesigning
security find-identity -v
```

常见格式：

```text
Developer ID Application: Your Name (TEAMID)
Developer ID Installer: Your Name (TEAMID)
```

### 3. 创建 App 专用密码

Apple ID 开启双重认证后，在 Apple ID 账户页面生成 App 专用密码，用于 `notarytool`。

需要记录：

- Apple ID 邮箱；
- Team ID；
- App 专用密码。

### 4. Base64 编码证书

```bash
base64 -i DeveloperIDApplication.p12 | tr -d '\n' | pbcopy
base64 -i DeveloperIDInstaller.p12 | tr -d '\n' | pbcopy
```

### 5. 配置 GitHub Secrets

必须一次性配置全部 9 项；只配置一部分时 Workflow 会主动失败，避免发布“看似已签名但未公证”的文件。

| Secret | 内容 |
|---|---|
| `MACOS_APPLICATION_CERT_P12_BASE64` | Developer ID Application P12 的 Base64 |
| `MACOS_APPLICATION_CERT_PASSWORD` | Application P12 密码 |
| `MACOS_INSTALLER_CERT_P12_BASE64` | Developer ID Installer P12 的 Base64 |
| `MACOS_INSTALLER_CERT_PASSWORD` | Installer P12 密码 |
| `MACOS_APPLICATION_IDENTITY` | 完整 Developer ID Application Identity |
| `MACOS_INSTALLER_IDENTITY` | 完整 Developer ID Installer Identity |
| `APPLE_ID` | Apple ID 邮箱 |
| `APPLE_TEAM_ID` | 10 位 Team ID |
| `APPLE_APP_PASSWORD` | App 专用密码 |

配置完成后，Workflow 会：

1. 创建临时 Keychain；
2. 导入两张证书和私钥；
3. 让 PyInstaller 使用 Developer ID Application 签署所有嵌入二进制，并启用 Hardened Runtime；
4. 使用 Developer ID Installer 构建签名 PKG；
5. 使用 `notarytool --wait` 公证 PKG 并 staple；
6. 创建并签署 DMG；
7. 公证和 staple DMG；
8. 删除临时 Keychain 和 P12 文件。

### 6. 本地验证

验证二进制：

```bash
codesign --verify --verbose=2 --strict cxr
codesign -dv --verbose=4 cxr
```

验证 PKG：

```bash
pkgutil --check-signature CodexRelay-0.6.0.pkg
spctl --assess --type install --verbose=4 CodexRelay-0.6.0.pkg
```

验证 DMG：

```bash
codesign --verify --verbose=2 CodexRelay-0.6.0-macOS-arm64.dmg
xcrun stapler validate CodexRelay-0.6.0-macOS-arm64.dmg
spctl --assess --type open --verbose=4 CodexRelay-0.6.0-macOS-arm64.dmg
```

## Secrets 安全要求

- 不要把 PFX、P12、密码或 Base64 文本提交到仓库。
- Release Workflow 只在 Tag 或手动发布时读取 Secrets。
- 建议为 Release 使用受保护的 GitHub Environment，并要求人工审批。
- 定期轮换 App 专用密码。
- 证书撤销或泄露后应立即停止发布并联系签发机构。
- 公共仓库中的 Pull Request 不应获得发布证书访问权限。

## 未签名构建

未配置任何签名 Secret 时，Workflow 仍会生成可测试的安装包：

```text
CodexRelay-Setup-<version>-windows-<arch>-unsigned.exe
CodexRelay-Portable-<version>-windows-<arch>-unsigned.zip
CodexRelay-<version>-macOS-<arch>-unsigned.dmg
```

这些文件适合内部测试，不适合作为面向普通用户的正式下载项。
