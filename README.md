# sora1looseload

《空之轨迹 the 1st》松散资源加载器，并为对白描边 Mod 提供固定接入点。将加载器和对白 Mod 文件放在游戏程序目录下，加载器会读取同目录中的松散资源并初始化对白核心。

## v0.1.0 下载

| 下载 | 用途 |
| --- | --- |
| [sora1looseload-v0.1.0.zip](https://github.com/RovingAimer/sora1looseload/releases/download/v0.1.0/sora1looseload-v0.1.0.zip) | 加载器，包含 `xinput1_4.dll`。 |
| [DialogueOutline-v0.1.0-main.zip](https://github.com/RovingAimer/sora1dialogueoutline/releases/download/v0.1.0/DialogueOutline-v0.1.0-main.zip) | 对白 Mod 主包：主对白正文、姓名描边及透明背景。 |
| [DialogueOutline-v0.1.0-active-voice.zip](https://github.com/RovingAimer/sora1dialogueoutline/releases/download/v0.1.0/DialogueOutline-v0.1.0-active-voice.zip) | 可选包：带头像的即时对白横条描边及透明背景。 |

[加载器 v0.1.0 发布页](https://github.com/RovingAimer/sora1looseload/releases/tag/v0.1.0) · [对白 Mod v0.1.0 发布页](https://github.com/RovingAimer/sora1dialogueoutline/releases/tag/v0.1.0)

## 安装与恢复

1. 完全退出游戏。备份游戏目录中已有的 `xinput1_4.dll`，以及之后会覆盖的布局和贴图文件。
2. 将加载器 ZIP 中的 `xinput1_4.dll` 放到与 `sora_1st.exe` 相同的目录。
3. 需要对白效果时，将对白 Mod 主包合并到该目录，保持包内路径。核心会放到 `mods/DialogueOutline/DialogueOutline.dll`。
4. 需要带头像的即时对白横条效果时，再合并可选包。

对白核心只接受其安装说明列出的 `sora_1st.exe` SHA256。请先核对[支持版本与校验值](https://github.com/RovingAimer/sora1dialogueoutline/blob/main/INSTALL.md)。

卸载时退出游戏，用备份恢复原来的 `xinput1_4.dll` 和被覆盖资源；安装前不存在的本 Mod 文件可逐个删除。

## 技术文档

- [方案、支持边界、构建与依赖许可](https://github.com/RovingAimer/sora1looseload/blob/main/README_FORK.md)
- [LocaleHandler 输出缓冲布局](https://github.com/RovingAimer/sora1looseload/blob/main/TLS_BUFFER_FIX.md)
- [源码与完整构建](https://github.com/RovingAimer/sora1looseload/tree/v0.1.0)
