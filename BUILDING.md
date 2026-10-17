# 构建与打包

## 环境

需要 Windows x64、Python 3、Visual Studio 2022 C++ Build Tools（MSVC x64）和 Windows SDK。从 [v0.2.0 完整源码附件](https://github.com/RovingAimer/sora1looseload/releases/download/v0.2.0/sora1looseload-v0.2.0-source.zip) 或递归克隆的仓库构建。Detours 固定在 `9764cebcb1a75940e68fa83d6730ffaf0f669401`。

GitHub 自动生成的 `Source code` 归档不包含 Detours 子模块。完整源码 ZIP 会包含 Detours 源码、`SOURCE_MANIFEST.json` 和依赖许可。

## 构建

在干净且已提交的源码目录运行：

```powershell
python build.py
```

若 Windows SDK 位于自定义目录，可传入 SDK 根目录：

```powershell
python build.py --sdk-root "E:/path/to/sdk"
```

脚本将 `xinput1_4.dll`、`report.json`、编译/链接日志及 PE 检查输出写入 `build/`。报告记录源码与 Detours 版本、编译器和 SDK、实际命令、导出与依赖检查及 DLL SHA256。构建使用 `/O2 /MT /W4`，链接使用 `/Brepro`，并检查七个 XInput 导出序号和嵌入的 MIT 许可文本。

## 打包

构建完成并提交干净源码后运行：

```powershell
python tools/package_release.py
```

输出写入 `build/packages/`：

- `sora1looseload-v0.2.0.zip`：安装包，包含 `xinput1_4.dll` 与 `mods/DialogueOutline/sora_mod.ini`。
- `sora1looseload-v0.2.0-source.zip`：完整当前源码、Detours 子模块及许可，含 `SOURCE_MANIFEST.json`。
- `manifest.json`、`build-report.json`：附件成员、SHA256 与原生构建信息。

打包会核对源码提交、构建输入、依赖版本及 ZIP 成员。它不会运行游戏或 DLL。v0.2.0 的安装二进制已由用户实机验收；正式源码包更新文档和发布元数据，保留通过验收的 DLL。`SOURCE_MANIFEST.json` 记录当前源码快照提交；原生构建报告保留实际编译来源，两者分别记录。

## 来源

上游及本项目的许可信息见 [README_FORK.md](README_FORK.md)、[LICENSE](LICENSE) 和 [Detours LICENSE](external/detours/LICENSE.md)。
