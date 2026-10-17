# sora1looseload：方案与当前实现

本仓库维护《空之轨迹 the 1st》的松散资源加载器，并在启动时发现 `mods` 下声明的 DLL Mod。统一使用现有 `xinput1_4.dll` 入口，便于独立模块按目录安装；增加模块时可沿用该加载器及模块声明接口。

上游为 [Hinkiii/sora1looseload](https://github.com/Hinkiii/sora1looseload/tree/04e898e369e3019d5aa2cb13a7209de39c643a4a)，基于提交 `04e898e369e3019d5aa2cb13a7209de39c643a4a`。仓库保留原资源读取、locale 路径处理及七个 XInput 导出，并接入 Microsoft Detours。

[通用加载器 v0.2.0](https://github.com/RovingAimer/sora1looseload/releases/tag/v0.2.0) 已通过用户实机验收，字幕描边与相机反虚化均正常。模块接口见 [MODULES.md](MODULES.md)，安装及完整源码附件见 [README.md](README.md)。

## 启动与资源加载

`DllMain` 创建启动 worker。worker 首先定位 `InitialFileCheck` 与 `LocaleHandler`：前者搜索 GLB 签名，未找到时搜索 CLE 签名；后者使用固定签名。两者找到后提交 Detours 事务。当前资源接入不依赖 `DebugLogger`。

资源 hook 尝试结束后，无论成功与否都会继续发现 `mods` 下的模块。资源签名缺失或 Detours 事务失败记录为 `[Resources]` 日志；每个模块的声明、预检、映射和初始化返回值分别记录为 `[Mods]` 日志。资源接入不执行 EXE SHA256 白名单检查。

调用原始 `LocaleHandler` 时，`InitialFileCheck` 使用每线程 `0x204` 字节输出对象：`0x200` 字节字符区及 `0x4` 字节长度字段。每个游戏线程有独立缓冲区；当前 locale 下找到 loose 文件时将该路径交给原始 `InitialFileCheck`。

加载器保留七个 XInput 导出与原序号。加载器自身处理 loose 资源和 XInput 转发；独立 Mod 由模块声明指定 DLL 与初始化入口。

## 依赖与许可

上游代码采用 MIT，原版权为 Copyright (c) 2025 Hinkiii。集成及构建改动采用 MIT，Copyright (c) 2026 DialogueOutline contributors 与 SoraMod contributors。Detours 固定在提交 `9764cebcb1a75940e68fa83d6730ffaf0f669401`，采用 Microsoft MIT 许可。

仓库的 [LICENSE](LICENSE) 和 [Detours LICENSE](external/detours/LICENSE.md) 保存完整许可。构建会检查 DLL 中包含两份许可文本及版权标记。游戏资源许可由各自权利人规定。

完整的模块安装接口见 [MODULES.md](MODULES.md)，环境和命令见 [BUILDING.md](BUILDING.md)。
