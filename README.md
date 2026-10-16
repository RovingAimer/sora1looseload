# sora1looseload — DialogueOutline integration

《空之轨迹 the 1st》loose资源加载器与DialogueOutline接入扩展，基于[Hinkiii/sora1looseload](https://github.com/Hinkiii/sora1looseload)。保留上游历史、MIT版权、语言路径处理和7个XInput导出；后台worker初始化资源hook后接入独立描边核心。

当前语言路径缓冲使用游戏要求的0x204字节容量。安装包只提供xinput1_4.dll，配合[对白Mod](https://github.com/RovingAimer/sora1dialogueoutline)的主包和可选即时对话包使用。

- [方案、构建、安装及恢复](README_FORK.md)
- [语言路径输出结构](TLS_BUFFER_FIX.md)
- [MIT许可证](LICENSE)
- [Microsoft Detours许可证](external/detours/LICENSE.md)

```powershell
git clone --recursive https://github.com/RovingAimer/sora1looseload.git
cd sora1looseload
python build.py
```
