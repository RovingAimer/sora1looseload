# sora1looseload DialogueOutline 接入版

本仓库维护《空之轨迹 the 1st》的 loose 资源加载器，并在现有资源加载流程完成后接入独立 DialogueOutline 核心。它基于 [Hinkiii/sora1looseload](https://github.com/Hinkiii/sora1looseload/tree/04e898e369e3019d5aa2cb13a7209de39c643a4a) 的提交 `04e898e369e3019d5aa2cb13a7209de39c643a4a`，保留原有资源读取、语言路径处理和七个 XInput 导出。

## 当前方案

加载器复用现有后台 worker。在资源 Detours 事务成功提交后，它从游戏目录加载 `mods/DialogueOutline/DialogueOutline.dll`，并在 loader lock 外显式调用 `SoraDialogueInitialize()`。这沿用 loose 资源 Mod 的目录结构，并让核心在字形 hook 初始化前完成检查。

加载器负责松散资源、locale 路径和 XInput 转发；DialogueOutline 核心负责对白节点识别、描边几何及颜色选择。核心缺失时，加载器继续运行资源加载功能。

描边核心发布于 [v0.1.0](https://github.com/RovingAimer/sora1dialogueoutline/releases/tag/v0.1.0)。必装主包处理主对白正文和姓名。可选 active-voice 包处理带头像的即时对白横条；其 `active_voice.lay` 使用横条资源 `active_voice`，头像由独立资源节点 `avfc5000` 提供。

## 支持边界

加载器按程序代码签名定位资源 hook。当前 `InitialFileCheck` 搜索 GLB 签名，未找到时再搜索 CLE 签名；同时要求 `DebugLogger` 与 `LocaleHandler` 签名均可找到。三个目标找到后，加载器提交 Detours 事务。加载器本身不执行 EXE SHA256 白名单检查。

对白核心独立校验游戏 EXE，只接受对白 Mod v0.1.0 安装说明列出的 SHA256：`9585d3d993874d65156aba633c00b8a25faab3afde8953a8a183c80fb8f657ac`。请以[核心支持版本说明](https://github.com/RovingAimer/sora1dialogueoutline/blob/main/INSTALL.md)为准。资源 hook 签名和核心 EXE 校验是两个独立检查。

核心成功安装 hook 时，加载器日志会显示 `[DialogueOutline] Initialization status: 0x0000014F (hook active)`。

## 构建

需要 Windows x64、Python 3、Visual Studio 2022 C++ Build Tools（MSVC x64）和 Windows SDK。Detours 作为固定 Git 子模块参与构建。GitHub 自动生成的 Source code ZIP 不含子模块内容；完整构建请递归克隆 v0.1.0 源码：

```powershell
git clone --recursive https://github.com/RovingAimer/sora1looseload.git
cd sora1looseload
git checkout v0.1.0
git submodule update --init --recursive
python build.py
```

脚本构建 `build/xinput1_4.dll`，并写入 `build/report.json`，记录源码提交、依赖版本、导出检查和 DLL SHA256。Detours 固定在 `9764cebcb1a75940e68fa83d6730ffaf0f669401`，静态链接到加载器。七个 XInput 导出与原序号保持不变。

## 来源与许可证

上游 [Hinkiii/sora1looseload](https://github.com/Hinkiii/sora1looseload/tree/04e898e369e3019d5aa2cb13a7209de39c643a4a) 的原始代码采用 MIT，Copyright (c) 2025 Hinkiii。加载器接入和构建改动采用 MIT，Copyright (c) 2026 DialogueOutline contributors。

Microsoft Detours 采用 Microsoft MIT 许可证，Copyright (c) Microsoft Corporation；其源码由上述固定提交锁定。仓库中的 [LICENSE](https://github.com/RovingAimer/sora1looseload/blob/main/LICENSE) 和 [Detours LICENSE](https://github.com/microsoft/Detours/blob/9764cebcb1a75940e68fa83d6730ffaf0f669401/LICENSE.md) 保留完整许可文本。加载器 DLL 也嵌入对应版权和许可通知。游戏资源及对白 Mod 资源的许可由各自权利人规定，详见[资源来源与授权](https://github.com/RovingAimer/sora1dialogueoutline/blob/main/THIRD_PARTY.md)。

## 安装与卸载

加载器 v0.1.0 发布 ZIP 只含 `xinput1_4.dll`。退出游戏并备份游戏目录中原有的同名文件，再将 ZIP 解压到 `sora_1st.exe` 所在目录。需要对白效果时，继续安装对白 Mod 主包；带头像的即时对白横条按需安装可选 active-voice 包。

卸载时退出游戏，用安装前备份恢复原来的 `xinput1_4.dll`。对白 Mod 的布局和贴图文件按其[安装说明](https://github.com/RovingAimer/sora1dialogueoutline/blob/main/INSTALL.md)逐个恢复。
