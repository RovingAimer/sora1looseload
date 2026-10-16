# sora1looseload — DialogueOutline integration fork

本 fork 增加独立描边模块的固定接入点，保留原加载器功能与 MIT 协议。具体差异、构建、安装和未实机状态见 [README_FORK.md](README_FORK.md)。原版项目：[Hinkiii/sora1looseload](https://github.com/Hinkiii/sora1looseload)；描边 Mod：[sora1dialogueoutline](https://github.com/RovingAimer/sora1dialogueoutline)。

---

This project uses submodules, so make sure to clone it with the `--recursive` flag:

```bash
git clone --recursive https://github.com/Hinkiii/sora1looseload.git
```

I suggest building with Release, but either works.

Put xinput1_4.dll into game folder

Will log asset requests that the game makes, and gives the dir it'd load from when not in the cache yet (first load)

Will log strings the game has internally with support for the Japanese character set


For example with this dll you could put

`Trails in the Sky 1st Chapter\asset\dx11\image\st_c5000.dds` to overrride estelles camp sprite

`Trails in the Sky 1st Chapter\script\scena\system.dat` to override system scene script
