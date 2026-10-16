# sora1looseload DialogueOutline 接入版

本项目基于 [Hinkiii/sora1looseload](https://github.com/Hinkiii/sora1looseload)，保留上游历史和 MIT 版权。它负责游戏 loose 资源覆盖、语言路径处理、XInput 转发，并在后台初始化完成后接入 [DialogueOutline](https://github.com/RovingAimer/sora1dialogueoutline) 核心。

## 方案与实现

加载器复用现有后台 worker，在资源 Detours 事务提交成功后，从 EXE 目录的 `mods/DialogueOutline/DialogueOutline.dll` 加载核心并显式调用 `SoraDialogueInitialize()`。这一时机让字形 hook 的初始化在 loader lock 外完成，也沿用现有玩家的 loose 目录安装方式。

语言路径输出缓冲为 `0x204` 字节，容纳游戏的512字节路径和DWORD长度字段，详见 [TLS_BUFFER_FIX.md](TLS_BUFFER_FIX.md)。原来的7个XInput导出与ordinal保持，资源读取和locale处理继续由本加载器负责。Detours源码锁定 `9764cebcb1a75940e68fa83d6730ffaf0f669401`。

核心缺失时跳过接入；接入结果写入原console.log。`0x14F`包含此核心hook active状态，字形的描边颜色、粗细和专属标记由核心维护。

## 构建

Windows x64、Python3、VS2022 C++工具和Windows SDK：

```powershell
git clone --recursive https://github.com/RovingAimer/sora1looseload.git
cd sora1looseload
python build.py
python tools/package_release.py
```

默认loader和Detours均使用 `/O2 /MT`。产物为 `build/xinput1_4.dll`；`build/report.json`记录源文件hash、源提交、依赖版本和7个导出检查。完整源码包包含Detours全部所需源码与许可证，解包后可直接构建。

## 安装与恢复

退出游戏并备份已有xinput1_4.dll，再将 `sora1looseload-v0.1.0.zip` 内的xinput1_4.dll合并到游戏程序目录。描边核心及主/即时对话资源使用独立Mod包安装。用户已确认组合的主对白、即时对话和去阴影效果；当前文字视觉参数见核心仓库说明。

恢复时退出游戏，用此次安装前的备份恢复xinput1_4.dll。其他资源按其原有Mod说明逐文件恢复。OptiScaler配置及DXGI入口由其自身安装维护。

安装ZIP只包含xinput1_4.dll。源码、构建记录与文档放在GitHub。原Hinkiii与Microsoft Detours完整MIT许可通知已嵌入DLL的只读数据，源码保留原LICENSE及external/detours/LICENSE.md。
