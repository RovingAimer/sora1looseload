# LocaleHandler 输出缓冲

调用游戏 `LocaleHandler` 时，加载器为输出路径提供 `0x204` 字节对象：前 `0x200` 字节是路径字符区，末尾 `0x4` 字节是长度字段。`InitialFileCheck` 为每个游戏线程使用独立的 `thread_local` 缓冲区，并在调用原始函数前清零首字节。

若当前 locale 对应的 loose 文件存在，加载器把其路径交给原始 `InitialFileCheck`。资源 hook 的目标签名和失败处理见 [README_FORK.md](README_FORK.md)。

该实现包含于 [v0.2.0](https://github.com/RovingAimer/sora1looseload/releases/tag/v0.2.0)，本次用户确认字幕描边与相机反虚化运行正常。
