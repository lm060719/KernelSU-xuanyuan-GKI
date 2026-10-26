# OS4.0.0.16 6.6.118：真实 Vendor .ko 版本与 Root 加载路径再审计

## 已从用户本机离线收集文件确认的事实

设备：Xiaomi 15 Ultra（xuanyuan），OS4.0.0.16.XOACNXM，原厂内核 `6.6.118-android15-8-gb9cc6ec16bc8-abogki536571621-4k`。

从此前的 `xuanyuan_module_critical_mt_v5`、`xuanyuan_module_provider_mt_v6` 以及 `xuanyuan_module_root_v4` 三批样本提取了共 **58 个互不重名的真实厂商 .ko**：

| `.modinfo/vermagic` | 数量 |
|---|---:|
| `6.6.57-android15-8-gbc807ab2c5a8-4k SMP preempt mod_unload modversions aarch64` | 55 |
| `6.6.57-android15-8-4k SMP preempt mod_unload modversions aarch64` | 2 |
| `6.6.57-4k-gbc807ab2c5a8 SMP preempt mod_unload modversions aarch64` | 1 |

**58 个均包含 ELF `__versions` section 名称。** 不应因为 6.6.57 与运行中 6.6.118 不同就判断加载失败；Linux 开启 `CONFIG_MODVERSIONS` 时可忽略 `vermagic` 第一个空格前的内核版本部分，并逐符号核验 CRC。真实执行路径可能包含其他厂商校验。官方文档：[Android loadable kernel modules](https://source.android.com/docs/core/architecture/kernel/loadable-kernel-modules)。

原始样本仅用于用户私有工作区中的只读分析，**未将 .ko、boot 或 init_boot 镜像上传到公开 GitHub**。约 390 个已发现的 `/vendor_dlkm/lib/modules` 文件中还有大量样本未验证。

## 已失败的实验

- GKI 6.6.118 `2026-01_r28` + KernelSU built-in：卡第二屏
- 纯 GKI `r28`：卡第二屏
- 纯 GKI `r37`（重获 12 个原厂标准 Vendor Hook）：仍卡第二屏
- 每次重新刷回原厂 boot：均恢复正常

上述实验**仅替换 boot.img**，没有记录手机 **`init_boot` 是否已经通过 KernelSU LKM 或其他 Root 方案修改**。这使得此前称作「不带 KernelSU 的对照版」在系统启动层面可能仍含有 KernelSU LKM 注入变量，不能完全排除它与新 Image 的相互作用。

KernelSU 官方 LKM 安装说明：带有 `init_boot` 的 Android 13+ 设备通常在 `init_boot` 修补 RAMDisk，而 built-in/GKI 模式替换 `boot` 中的内核 Image。参考 https://kernelsu.org/guide/installation.html 。

这只是待验证的**潜在干扰因素**，并无证据证明 LKM 导致第二屏卡死。也不能直接修改、恢复或清空手机的 `init_boot` 来求证——已有 Root 环境及解密状态必须保护。

## 新增只读手机诊断

仓库新增 `diagnostics/xuanyuan_os4_runtime_baseline.sh`，手机端 Root Shell 执行：

```sh
su
sh /sdcard/Download/xuanyuan_OS4_readonly_runtime_diag.sh
```

脚本记录：
- 内核版本和当前 A/B 槽位
- `/proc/modules` 实际加载的模块名、`modules.load` 简单对照
- KernelSU/SU 相关 **目录是否存在** 的弱线索
- 当前活跃 `boot` 和 `init_boot` 分区 **SHA256**（不会复制镜像）
- pstore 文件名（无崩溃内容）

用户工作区也提供了可直接复制到手机的 ZIP 脚本。

**判定门槛：** 将活跃 `boot` hash 与此前同版本原厂 `boot_b.img` hash 核验；如 `boot` 确为原厂而 Root 正常，说明 Root 并非靠重新编译原厂 boot 中的 KernelSU built-in，接着必须检查 `init_boot` 与 Root 实际实现。`init_boot` hash 必须与**同版本真正的原厂 init_boot** 比较才能判断其是否修改，不应凭任意 hash 猜测。

在缺乏相同固件的 OEM 私有源码、实机启动错误日志和全量 vendor .ko 分析前，**不制作、不刷写下一版 GKI**。


## 2026-10-26 23:08（UTC+8）：用户手机只读运行报告已回传

来自用户本机 `xuanyuan_OS4_root_module_baseline_20261026_230831.txt`：

- 机型 `xuanyuan`，系统 `OS4.0.0.16.XOACNXM`，原厂内核 `6.6.118-android15-8-gb9cc6ec16bc8-abogki536571621-4k`。
- 当前实际槽位 `_b`；`sha256(/dev/block/by-name/boot_b)` = `f082826b0e9ea020a5ab20db3dacc6814bbbe8b30e7a223eebd81f69d8eeac30`，**与此前提供的原厂 `boot_b.img` 完全匹配**。
- `sha256(/dev/block/by-name/init_boot_b)` = `df4db6bc51607e60c4128be6a6c9d0faf22a0aeb23aa7e8a70fc475bbf252b49`。**缺少该确切固件的干净原厂 `init_boot_b.img` 对照哈希，不得猜测是否已修改**。
- `id -Z` 回报 `u:r:ksu:s0`；`/proc/modules` 明确包含 **`kernelsu`**；存在 `/data/adb/ksu`。当前使用 **KernelSU LKM**，即使 `/sys/module/kernelsu`、`/sys/module/ksu`、`/sys/module/ksu_lkm` 均不存在也不能否定 LKM（可能隐藏、不同内核配置等）。
- `/proc/modules` 实际有 **602** 个加载模块；`/vendor_dlkm/lib/modules/modules.load` 有 **556** 个条目，其中脚本按名称匹配到 **542**，另 **14** 项未见于 `/proc/modules`，包含硬件替代驱动和重复条目（Wi-Fi `qca_cld3_*`、`icnss2` 等）；**并不证明任何模块在启动时加载失败**。
- `/sys/fs/pstore` 仍为空。

**重要实验解释修正：** “vanilla GKI”仅说明 **GKI Image 编译时无 `CONFIG_KSU`**；并不代表整个设备开机流程完全无 KernelSU。此前替换 `boot.img` 时很可能沿用了现有的 KernelSU LKM 启动环境。根据 [KernelSU 官方安装文档](https://kernelsu.org/guide/installation.html)，Android 13+ 设备在常规 LKM 安装模式下通过 **`init_boot` 的 ramdisk 注入**内核模块，而 GKI 模式替换 `boot`；但 KernelSU 还提供 late-load 模式，所以 **仅凭当前模块存在不能证实 `init_boot` 一定被修改**。若 `init_boot_b` 为补丁版，启动失败时已有 LKM 可能与新替换的 GKI 在 ABI 或加载时机上冲突。

**尚未证实的判断：**
- 不能因此把所有三次 bootloop 都归咎于 LKM：缺失的 OEM 存储补丁、专用 Hook、厂商模块加载或 ramdisk 行为等仍可能单独引起失败。
- 当前可用系统及数据应保持不变，**不应盲刷原厂 init_boot、卸载 Root、清除模块或试刷第四个 GKI**。
- 下一步以**只读**方式核对 `init_boot_b` 与匹配固件原厂 image 的哈希，同时辨认已安装 `kernelsu.ko` 的版本/依赖或 KernelSU Manager Runtime Mode，优先分析它与 r37 的 ABI；如需进一步改变 boot 测试条件，先制订可靠的完整回退方案。

安全：未将私有分区文件上传 GitHub；本仓库仅收录这些简要诊断事实。
