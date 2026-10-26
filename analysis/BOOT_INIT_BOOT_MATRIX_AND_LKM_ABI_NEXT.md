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
