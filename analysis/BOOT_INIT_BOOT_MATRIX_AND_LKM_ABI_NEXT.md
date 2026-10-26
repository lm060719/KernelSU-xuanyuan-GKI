# Xiaomi 15 Ultra / OS4.0.0.16：boot + init_boot 根因隔离与 LKM 下一步（2026-10-26）

## 当前准确的实机测试矩阵

用户当场明确澄清三次实机测试所搭配的 `init_boot`，不能再将早期 pure-GKI 实验误称为完整的「无 KernelSU 对照」。

| boot | init_boot | 实测 |
|---|---|---|
| 原厂 6.6.118 boot | 已修补、KernelSU LKM | 正常 |
| `android15-6.6-2026-01_r28` + KernelSU v3.3.1 内置 | **原厂 init_boot** | 卡第二屏 |
| 纯 `android15-6.6-2026-01_r28` | **修补版 init_boot** | 卡第二屏 |
| 纯 `android15-6.6-2026-01_r37` | **修补版 init_boot** | 卡第二屏 |
| 纯 r28/r37 | **原厂 init_boot** | **未测试，结果未知** |

结论不能超越上述表：三个失败组合均涉及不同模式的 KernelSU，但不能说 LKM 必然造成纯 GKI 失败，也不能说 built-in KernelSU 肯定是 _r28 失败的唯一原因。GKI/OEM 差异和镜像验证仍是独立候选。已恢复且应保留的工作状态是原厂 boot + 修补版 init_boot。

## 目前已经确认的运行状态

2026-10-26 23:08 用户手机只读报告：

- `/proc/modules` 实际存在 `kernelsu` 模块，SELinux 上下文 `u:r:ksu:s0`。
- 当前槽位 `_b`，`sha256(boot_b)` 是 `f082826b0e9ea020a5ab20db3dacc6814bbbe8b30e7a223eebd81f69d8eeac30`，与先前备份的同版本原厂 boot 完全一致。
- `sha256(init_boot_b)` 是 `df4db6bc51607e60c4128be6a6c9d0faf22a0aeb23aa7e8a70fc475bbf252b49`，尚没有同版本原厂 init_boot 对照哈希。
- 原厂内核下可正常加载 602 个模块，不等于替换内核下仍能正常加载相同模块。

KernelSU 官方的常规 LKM 启动时序：`ksuinit` 在 early init 加载 `kernelsu.ko`，随后恢复原厂 init；不过官方亦支持 late-load（系统启动完成后加载）。这些是**一般机制**，并不能单凭当前报告确定本设备失败期间实际执行了哪个阶段。[KernelSU 官方安装指南](https://kernelsu.org/guide/installation.html) / [模块与运行阶段说明](https://kernelsu.org/guide/module.html)。

## 新的可离线验证步骤（无需刷机）

私人工作区新增 `xuanyuan_OS4_init_boot_LKM_offline_audit_kit.zip`：

- `audit_init_boot_lkm.py`：只读解析 Android boot v3/v4 header、init_boot ramdisk（gzip、lz4 frame、lz4-legacy、xz、未压缩 newc cpio）；查找潜在 KernelSU 启动组件，不解压文件到公共路径、不执行组件。
- 如镜像中确实含有 `kernelsu.ko` ELF：读取 `.modinfo`、`__versions`，与本次已保存的 `r37_Module.symvers` 进行交叉核对，报告匹配/CRC 冲突/目标内核未导出的符号。
- 工具已用用户原厂 `boot_b.img` 验证 Boot v4/无 ramdisk 的正常路径；另用*合成镜像*内嵌一个既有厂商 ELF 样本作为 **Parser 单元测试**，得到 9/9 CRC 匹配。**这个自测样本不是用户真正的 KernelSU LKM，不能把它作为真实的兼容性结果**。
- 该分析工具本身及随机合成测试数据均不包含真实 `init_boot_b_current.img`；尚待用户提供该镜像或私下运行报告。
- 若 `kernelsu.ko` 嵌入 `ksud`/其他启动文件而不是 cpio 中独立的 ELF 文件，工具可能无法发现；「未发现」并不能排除存在。CRC 完全匹配也不能等同启动可用。
- **请勿公开上传修补版 init_boot 或从手机导出的其它二进制到 GitHub。**

如需备份，仅限已解锁且当前系统可启动设备，MT 管理器 Root Shell **只读**：

```sh
su
dd if=/dev/block/by-name/init_boot_b of=/sdcard/Download/init_boot_b_current.img bs=1M
sha256sum /sdcard/Download/init_boot_b_current.img
```

注意必须保持 `if=` 为分区，`of=` 为手机 Download 文件，千万不要反过来。若根本不想导出镜像，可先使用 KernelSU 管理器查看「LKM / late-load」安装/运行模式，但仅凭截图仍不足以比对符号 CRC。

## 明确禁止的捷径

- 不修改或清空 `init_boot` 来「排除干扰」，不做任何未验证的实验镜像第四次刷写。
- 不把七个缺失的厂商存储 `CONFIG_*` 名称强行添加到 GKI：找不到实现时，这不会重建 OEM 代码。
- 不凭 `vermagic` 字符串单独否定模块兼容性；也不能凭 58 个样本的 CRC 一致就确认全部模块与内核兼容。

**下一个最有信息增益的证据**：从修补版 init_boot 确认具体加载链和二进制 LKM，结合用户现有 r37 Module.symvers 离线比较；随后再决定是否需要从同版本厂商源代码或 boot 阶段日志寻求证据。


## 2026-10-26 23:51：MT LKM 诊断 v2 的真实发现

用户使用 MT 管理器执行第二版 SH，上传 `xuanyuan_LKM_只读诊断_20261026_235148.txt`，报告所示：

- 机型 `xuanyuan`，固件 `OS4.0.0.16.XOACNXM`，内核 `6.6.118-android15-8`，槽位 `_b`。
- `boot_b` SHA256 `f082826b0e9ea020a5ab20db3dacc6814bbbe8b30e7a223eebd81f69d8eeac30`，仍然匹配原厂备份。
- `init_boot_b` SHA256 `df4db6bc51607e60c4128be6a6c9d0faf22a0aeb23aa7e8a70fc475bbf252b49`。
- `init_boot` 是 boot header v4，ramdisk LZ4；27 个 CPIO entry 中有 `kernelsu.ko`（330664 bytes）和 `ksu_config`（9 bytes），目前 `/proc/modules` 确认 KSU LKM 已加载。
- KSU LKM SHA256 `e57ce23de951be6b0dee5030f6724322fed126aa4af71828994437bfb0bb61ad`。
- KSU 模块 `vermagic=6.6.127-4k-g46a034eca005-dirty SMP preempt mod_unload modversions aarch64`。
- v2 扩展 ELF 节解析结果：**`__versions` 存在，但 size=0；`__version_ext_names` 与 `__version_ext_crcs` 都不存在**。

### 重要修正：空的版本节不是解析失败或 CRC 冲突证据

有 KernelSU 手动重定位 / 模块加载构建方式**有意要求 `__versions` size=0**，并通过运行时 kallsyms 解析符号，不使用相应的 CRC 表。实证参考：
- https://github.com/WitAqua-tools/Root-My-Device-Payloads/blob/main/src/kernelsu/README.md

这说明本机 LKM 的格式与此种实现**一致**，但尚未实证这台手机实际采用的是哪一个具体的加载器和符号解析路径。不能再按纯 `Module.symvers` CRC 缺失得出兼容/不兼容结论。

### 下一步工具

MT 单文件 `xuanyuan_MT_LKM_check_v3.sh` 保留 v2 全部只读检测，在模块无非空版本节时新增**手工解析 ARM64 ELF64 SHT_SYMTAB + SHT_STRTAB**，列出全部普通 ELF `SHN_UNDEF` 符号（仅符号名）。将这些名字与已经构建的 r37 `Module.symvers` 导出名字集（9450 项）交叉对照。

重要限制：
- **导出符号名覆盖不代表运行时 CRC、一致的结构体布局、kallsyms 能否访问或 init_boot LKM 在失败引导阶段是否成功加载。**
- `r37` 若找不到某个符号，也不等于必定缺少；可能由另一 `.ko`、内核本地/非导出符号或手动重定位解析器提供。
- 无需上传原始 init_boot，仍不刷机。等待新报告后才能继续做更强判断。
