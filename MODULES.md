# DLL Mod 模块接口（加载器 0.2.0）

加载器在游戏程序目录的 `mods` 下扫描一级子目录。每个模块目录须包含 `sora_mod.ini` 和同目录 DLL；未声明的 DLL 不会被加载。

```text
sora_1st.exe
xinput1_4.dll
mods/
  Example/
    sora_mod.ini
    Example.dll
```

声明格式：

```ini
[SoraMod]
Api=1
DLL=Example.dll
Initialize=ExampleInitialize
Enabled=1
```

`Api=1` 与 `DLL` 为必填项。`DLL` 必须是同目录 `.dll` 文件名，不能带路径。`Initialize` 可省略，默认导出名为 `SoraModInitialize`。`Enabled` 可省略，默认启用；值 `0` 禁用模块，值 `1` 启用。

## 初始化入口

入口须为 C 名称导出、无参数的 `DWORD WINAPI` 函数，例如：

```cpp
extern "C" __declspec(dllexport) DWORD WINAPI ExampleInitialize(void);
```

`Initialize` 必须是非空的可打印 ASCII 导出名。函数返回的 32 位值会由加载器原样写入 `console.log`。状态位含义由各 Mod 自己定义，加载器不从返回值推断成功或失败。模块初始化后仍会继续处理其他模块。

## 检查与生命周期

加载前，加载器以只读方式检查 DLL 文件中的 PE32+ AMD64 架构、表和边界、导出表、声明的入口名称及入口代码所在区段。初始化导出必须有文件支持的代码字节、位于可执行区段，且不能是转发导出。检查通过后才将 DLL 映射进游戏进程，再解析入口并调用它。

单个模块的声明、检查、加载或入口解析失败会写入日志并跳过该模块，随后继续其他模块。成功映射的模块保持加载，直至游戏进程退出。

预检覆盖文件中的 PE 架构、结构边界及初始化导出位置。DLL 映射后会在游戏进程内以当前玩家账户权限执行，可能影响游戏稳定性、文件和数据。只使用可信来源；可查阅完整源码和许可证、自行编译，并将附件 SHA256 与发布清单核对。
