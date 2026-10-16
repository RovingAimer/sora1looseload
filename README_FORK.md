# DialogueOutline 接入扩展

这是 [Hinkiii/sora1looseload](https://github.com/Hinkiii/sora1looseload) 的 fork，基于上游提交 `04e898e369e3019d5aa2cb13a7209de39c643a4a`。原 MIT 许可证和上游历史保留；新增接入及构建代码也采用 MIT，Copyright (c) 2026 DialogueOutline contributors。Detours 子模块固定为 `9764cebcb1a75940e68fa83d6730ffaf0f669401`，保留 Microsoft MIT 许可证。

本仓库维护加载器；独立描边 Mod 位于 [sora1dialogueoutline](https://github.com/RovingAimer/sora1dialogueoutline)。这份 fork 尚未实机验证，上游原版没有合入本改动。

## 改动范围

原有资源读取、语言处理与 XInput 转发代码保留。`dllmain.cpp` 增加一个头文件引用，并在资源 Detours 事务成功提交后调用固定模块加载函数。该函数从游戏程序目录读取 `mods/DialogueOutline/DialogueOutline.dll`，然后在 DllMain 和 loader lock 之外显式调用 `SoraDialogueInitialize()`。

这是一个固定的描边模块接入点，不是通用插件框架。它不扫描其他 DLL，不占用 D3D/DXGI 入口，也不更改进程全局 DLL 搜索路径。未安装描边模块时跳过；路径错误、加载失败或核心初始化失败记录在原 `console.log`，不撤销已成功建立的资源读取 detours。七个原 XInput 导出及序号保持。

## 构建

```powershell
git clone --recursive https://github.com/RovingAimer/sora1looseload.git
cd sora1looseload
python build.py
```

需要 Windows x64、Python 3 和 Visual Studio C++ Build Tools（MSVC、MASM/Windows SDK）。也可以使用原 Visual Studio 工程。完整源码压缩包已附带 Detours 的所需源码，解压后可直接运行构建脚本，无须 Git 子模块下载。

脚本只写本工作副本的 `build/`，不安装、不加载生成的 DLL，也不启动游戏。输出 `build/xinput1_4.dll`、`build/report.json`。报告记录源码及依赖版本、源码校验、DLL 校验和 XInput 导出检查。运行 `python tools/package_release.py` 可生成独立的加载器候选包和完整源码包。

## 安装与恢复

选择本接入方式时，用户需要先备份当前游戏根目录的 `xinput1_4.dll`，再明确选择将其替换为本 fork 的构建产物。之后按描边 Mod 的说明合并其目录。无需 `SoraLooseLoader.dll`，也无需其他 DLL 代理。现用原版 DLL 不会因为复制 Mod 文件就自动获得接入能力。

不要同时启用描边 Mod 的 ASI 入口，以免两份核心争用同一位置。核心接入正常时日志会出现 `[DialogueOutline]` 初始化状态；它只能证明接入状态，画面、稳定性与已有 Mod 是否兼容仍需实机检查。卸载本 fork 时，退出游戏后用自己的备份恢复原加载器即可。

本仓库不修改磁盘游戏 EXE，不提供游戏或 Mod 资源，不提供自动安装脚本。描边效果、文字颜色适配与具体游戏版本检查由独立 Mod 核心负责。
