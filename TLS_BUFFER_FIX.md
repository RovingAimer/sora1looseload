# LocaleHandler 输出缓冲布局

加载器调用游戏的 `LocaleHandler` 时，为输出路径提供与目标函数写入结构相符的缓冲区：

| 偏移 | 大小 | 内容 |
| --- | ---: | --- |
| `0x000..0x1FF` | `0x200` 字节 | 路径字符区 |
| `0x200..0x203` | `0x004` 字节 | DWORD 长度字段 |
| 总计 | `0x204` 字节 | 完整输出对象 |

`InitialFileCheck` 使用每线程存储保存该对象：

```cpp
static thread_local char localizedPath[0x204];
```

调用前将首字节清零，再把缓冲区传给原始 `LocaleHandler`。当字符区包含路径时，加载器会按当前 locale 检查游戏目录中的对应 loose 文件，并将选中的路径交给原始 `InitialFileCheck`。每个游戏线程使用独立缓冲区。

加载器使用的资源 hook 签名边界与对白核心的 EXE 校验分别见 [README_FORK.md](https://github.com/RovingAimer/sora1looseload/blob/main/README_FORK.md) 和[核心支持版本说明](https://github.com/RovingAimer/sora1dialogueoutline/blob/main/INSTALL.md)。
