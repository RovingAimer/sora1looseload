# sora1looseload 0.2.0

《空之轨迹 the 1st》松散资源加载器和通用 DLL Mod 加载器。统一发现并加载 `mods` 下声明的模块；以后安装符合接口的新 Mod 只需合并模块目录，无需为新模块再次替换 `xinput1_4.dll`。加载器 0.2.0 与字幕描边、相机反虚化的组合已由用户实机确认正常。

## 下载

| 下载 | 用途 |
| --- | --- |
| [sora1looseload-v0.2.0.zip](https://github.com/RovingAimer/sora1looseload/releases/download/v0.2.0/sora1looseload-v0.2.0.zip) | 安装包：`xinput1_4.dll` 与字幕模块声明 `mods/DialogueOutline/sora_mod.ini`。 |
| [sora1looseload-v0.2.0-source.zip](https://github.com/RovingAimer/sora1looseload/releases/download/v0.2.0/sora1looseload-v0.2.0-source.zip) | 完整源码、固定版本 Detours、构建方法和许可证，供查验或自行编译。 |
| [对白描边 v0.1.0](https://github.com/RovingAimer/sora1dialogueoutline/releases/tag/v0.1.0) | 独立 Mod：主包提供字幕核心和主对白资源；即时对白横条包为可选附件。 |
| [相机反虚化 v0.1.0](https://github.com/RovingAimer/sora1cameranearclarity/releases/tag/v0.1.0) | 独立 Mod：处理相机靠近人物时的近距离淡出。 |

GitHub 自动生成的 `Source code` 归档不包含 Detours 子模块；自行构建请使用上表的完整源码附件，或递归克隆仓库。

## 安装与恢复

退出游戏，备份已有 `xinput1_4.dll` 和将覆盖的模块声明，将安装 ZIP 解压到 `sora_1st.exe` 所在目录，保留目录层级。需要字幕效果时再安装对白主包，需要相机效果时安装相机模块；每个模块的核心 DLL 和资源由各自安装包提供。

卸载时退出游戏，用备份恢复被覆盖的文件；安装前不存在的模块文件可移除。保留其他 Mod 文件。

本次实机验收的 `sora_1st.exe` SHA256 为 `9585d3d993874d65156aba633c00b8a25faab3afde8953a8a183c80fb8f657ac`。加载器资源 hook 按代码签名定位；字幕和相机模块分别执行自己的 EXE 版本与原指令检查。其他游戏版本的兼容性尚未确认。

DLL 会以游戏进程的权限运行代码，可能影响游戏稳定性、文件和数据。只使用可信来源。完整源码与构建步骤可供查验和自行编译；附件 SHA256 与源码提交记录在发布页底部。

## 文档

- [当前方案、实现和许可](README_FORK.md)
- [模块声明与初始化接口](MODULES.md)
- [构建与打包](BUILDING.md)
