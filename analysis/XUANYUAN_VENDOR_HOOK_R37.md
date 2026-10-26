
## 2026-10-26：用户澄清测试时的 init_boot 状态（重要因果修正）

用户明确说明：
- **GKI r28 + KernelSU v3.3.1 built-in** 失败时，搭配的是**原厂 `init_boot`**。
- **纯 GKI r28、纯 GKI r37** 失败时，搭配的均为**已经修补过的 `init_boot`（KernelSU LKM 环境）**。
- 刷回原厂 `boot` 可以正常启动，目前的原厂 `boot_b` SHA256 已确认一致。

### 重建真实试验矩阵

| boot | init_boot | 实机 |
|---|---|---|
| 原厂 boot | 目前的修补版 init_boot（运行时 `/proc/modules` 有 `kernelsu`） | 正常 |
| GKI r28 + KSU built-in | 原厂 init_boot | 第二屏卡住 |
| 纯 GKI r28 | 修补版 init_boot（LKM 注入链未被隔离） | 第二屏卡住 |
| 纯 GKI r37 | 修补版 init_boot（LKM 注入链未被隔离） | 第二屏卡住 |
| 纯 GKI r28 / r37 | **原厂 init_boot** | **尚未做过有效对照，结果未知** |

### 必须撤销先前过度推论

此前文档以纯 GKI r28 也失败为理由断言「**KernelSU 不是 bootloop 的必要条件**」「问题来自共享通用 GKI 而与 KSU 无关」——**这一点尚无有效实机证据**：**三个失败组合中，内置版有 KernelSU built-in，两个纯 GKI 版则保留修补过的 init_boot、可能加载 KernelSU LKM**。因此迄今**没有一组已知完全不含 KernelSU 的替换 GKI 测试**。也未证实 LKM 一定已在卡第二屏前实际加载，更不能反向确定 LKM 就是根因。

- built-in 镜像在**原厂 init_boot**下失败，故其故障不应归因于另一个已存在的 **LKM init_boot**。
- vanilla r28/r37 在**修补 init_boot**下失败，无法排除已有 LKM 与替换的 GKI ABI/符号表/引导时序不匹配。
- 各组也共用 AOSP 内核、boot 封装等变量。**OEM 七项存储配置与两个 F2FS 私有 Hook 是否致故障未获证实**。
- 对照组最核心的缺口是「纯 r37 + 原厂 init_boot」，然而此前三次卡机且暂无可靠 boot-stage 日志，**不应仅为补齐矩阵就劝用户再刷**。

**当前策略：保持现有能启动的原厂 boot + 已修补 init_boot，不对 init_boot 做未经授权的写入。优先离线分析 KernelSU LKM 及设备的厂商模块依赖，寻找能证明失败发生在哪个引导阶段的日志。**

---

# Xiaomi 15 Ultra / HyperOS4 6.6.118：原厂 Vendor Hook 缺失的可复现证据（2026-10-26）

## 实机基准与结果

- Xiaomi 15 Ultra `xuanyuan`, `OS4.0.0.16.XOACNXM`, Android 17
- Stock kernel: `6.6.118-android15-8-gb9cc6ec16bc8-abogki536571621-4k`，原厂 `boot_b.img` 可正常启动
- 之前刷入的 `android15-6.6-2026-01_r28` 纯 GKI 与集成 KernelSU v3.3.1 版本均卡第二屏；刷回原厂 boot 均正常
- 在**完整原厂 boot 原始字节**、先前构建的 **r28 纯 Image** 和 **r28 KSU Image** 中读取 `__traceiter_android_*` 字符串：
  - stock: **796** 条不同符号
  - r28 vanilla: **782**
  - r28 KernelSU: **782**
  - 原厂独有 **14**；r28 未见独有符号
- 这仅是二进制字符串比较，不是 ELF 符号解析或模块实际加载日志，不能单靠数量解释 bootloop。

## 14 个原厂独有 Hook

```
android_vh_cma_alloc_lat_end
android_vh_cma_alloc_lat_start
android_vh_dma_heap_buffer_alloc_lat_end
android_vh_dma_heap_buffer_alloc_lat_start
android_vh_f2fs_is_hiprio_task
android_vh_f2fs_is_usr_task
android_vh_folio_end_writeback
android_vh_folio_start_writeback
android_vh_mm_direct_reclaim_end
android_vh_mm_direct_reclaim_start
android_vh_mmc_attach_sd
android_vh_mmc_blk_reset
android_vh_mmc_gpio_cd_irqt
android_vh_sdhci_get_cd
```

## 公开 GKI 月度标签溯源（已完成）

只读 CI `Xuanyuan stock hook tag audit` 从 Android Gitiles 固定标签获取 `drivers/android/vendor_hooks.c`，检测 `EXPORT_TRACEPOINT_SYMBOL[_GPL]`，结果：

| AOSP GKI 标签 | 导出覆盖的原厂 14 项 |
|---|---:|
| 2026-01_r28 | 0/14 |
| 2026-01_r29 | 0/14 |
| 2026-01_r30–r33 | 2/14 |
| 2026-01_r34–r36 | 8/14 |
| 2026-01_r37–r38 | **12/14** |

所有标签均报告 Linux **6.6.118**。

- r30 首次覆盖 2 个 `folio_*_writeback`。
- r34 增加 CMA、DMA Heap、内存直接回收相关 6 个。
- r37 增加 MMC/SD 相关 4 个。
- `android_vh_f2fs_is_hiprio_task` 和 `android_vh_f2fs_is_usr_task` 在所有审计标签的导出列表中均未找到：可能为小米厂商私有，不可在没有源码和签名验证时臆造 Hook 签名或随意添加。
- **编译出的最终 Image 不一定包含源码所导出的所有符号**，必须基于产物二次核验。

## 对用户已有 58 个 .ko 的额外交叉核验

本地只读解析了已采集的 58 个 .ko ELF `SHN_UNDEF` 符号，而不是仅搜索字符串。

- 共找到 17 个不同的 `__tracepoint_android_*` / `__traceiter_android_*` 导入名。
- **其中 0 个属于 r28 所缺的 14 个 Hook**。
- 这意味着 **58 个模块不能证明 14 个 Hook 导致 bootloop**；且 58/390 并非完整模块覆盖。真正 boot 根因依旧未证实。
- 原始厂商 .ko 和 boot 没有上传公开 GitHub；这里只保存非隐私的聚合结论。

## 下一阶段已经启动

仓库工作流 `.github/workflows/gki-r37-vendor-hook-control.yml` 使用 `android15-6.6-2026-01_r37` **不含 KernelSU** 的代码，并新增：

1. 同样的 Kleaf 编译配置和 4KB 页、动态 task struct 的验证。
2. 在真正的 Image 中核对 12 个新标准 Hook 的 `__traceiter` 存在性。
3. 在 `Module.symvers` 中核对 `__tracepoint` 导出及其 CRC。
4. 仅上传 **非可刷** `Image` 和诊断报告；**不生成 boot.img、不建议刷机**。

原厂仍有七项 GKI 缺少的 UFS/F2FS/SCSI 配置，其必要性未排除。后续必须再次核对更完整的厂商模块 KMI 及关键内核特征，不能因 r37 补齐部分 Hook 就宣布可用。

## 官方和同类参考

- [Google 官方 GKI 6.6.118 发布时间表](https://source.android.com/docs/core/architecture/kernel/gki-android15-6_6-release-builds)
- [AOSP android15-6.6 源代码](https://android.googlesource.com/kernel/common/)
- [同内核字符串的小米 15（dada）研究记录](https://github.com/Re-s/Mi15-Droidspaces-Kernel/blob/main/docs/RESEARCH.md)：另一机型，不等同于 xuanyuan 实测。

**当前既没有实机成功启动证据，也不具备支持刷写的新 boot.img。**


## r37 纯 GKI 实际编译完成及离线 ABI 验证（2026-10-26）

[成功工作流 #40330094335](https://github.com/lm060719/KernelSU-xuanyuan-GKI/actions/runs/40330094335)

- `GKI_TAG=android15-6.6-2026-01_r37`，Kleaf 成功生成无 KernelSU 的 ARM64 `Image`。
- `Image` 的 `__traceiter_android_*` 总数 **794**，而用户原厂 **796**，先前失败的 r28 **782**。
- 14 个 r28 缺失的原厂 Hook 中，**12 个恢复**，产物 `Image` 字符串和 `Module.symvers` 均确认导出；仍缺小米 F2FS 私有 Hook：`android_vh_f2fs_is_hiprio_task`、`android_vh_f2fs_is_usr_task`。
- r28 导出 **9427** 个、r37 **9450** 个；共有 **9423** 个符号全部 CRC 相同；新增 **27** 个，移除 **4** 个。
- 使用用户早先提交的 58 个真实 `.ko` 进行私下只读检查：包含 **1095** 个唯一 `__versions` 导入；与 r37 的 GKI 导出相交 **823** 个，**0** CRC 冲突；四个被 r37 移除的导出在这 58 个模块中**未发现引用**。有 **272** 项需从其他厂商模块或内建功能进一步解析（既有报告划分为采集样本互相提供的 144 + 缺提供方的 128），不能算作 r37 单独缺失。
- 相比 r28，模块抽样 CRC 并没有退步。这只是局部 ABI 验证，**不是实机可启动证明**。
- 原厂 boot v4 容器支持独立离线打包，固定大小 **100663296 字节**、原厂 `boot.security_patch=2026-09-01`；重打包原厂内核与原厂完整镜像逐字节一致。已离线制作单独标记的 **纯 r37 无 KSU、未测试**对照 boot.img（文件保留在用户会话工作区，**未发布到公有 GitHub 仓库**，也未刷机）。
- 与 r28 对照镜像一样，新 `boot.img` 不是原厂签名，**可能卡第二屏**；禁止宣称「可稳定启动」、禁止改变 patchlevel、不可双槽同时测试。


## 实机测试已失败：r37 仍然卡第二屏（2026-10-26）

用户已实际将「纯 GKI `android15-6.6-2026-01_r37`、无 KernelSU」的对照 `boot.img` 刷入小米 15 Ultra `xuanyuan`；仍**卡第二屏**。随即刷回**同固件原厂 `boot_b.img`**，手机**再次正常开机**，未报告数据丢失。

因此不能把 12 个标准 Hook 的补齐视为解决 bootloop，也不能仅因构建通过、CRC 抽样相同而再劝刷后续 GKI。测试过的三类镜像：r28+KSU、r28 pure、r37 pure，全部失败。**停止重复刷机。**

### 关键新增证据：原厂 vs r37 内核实际 IKCONFIG 全量比较

从原厂 `boot_b.img` 的 kernel payload 和 CI `vanilla-r37-hook-control-Image-NOT-FLASHABLE` Image 中直接解出嵌入的 IKCONFIG：

- 原厂发现 **6191** 条明确的 `CONFIG_*` 设置（含 `not set`），r37 为 **6184**。
- 两者**仅有 7 条差异**，均为原厂 `=y`、通用 r37 **没有同名配置项**（不是值为 n）：
  - `CONFIG_BLOCK_HYBRID_UFS`
  - `CONFIG_F2FS_FS_HYBRID_UFS`
  - `CONFIG_F2FS_VIP_FILE`
  - `CONFIG_SCSI_DISCARD`
  - `CONFIG_SCSI_FASTDISCARD`
  - `CONFIG_XIAOMI_ENHANCED_IOSTAT`
  - `CONFIG_XIAOMI_EROFS_IOSTAT`
- 这**不能**说明全部编译代码一致：同一 Kconfig 可以对应不同代码实现、结构体布局、配置依赖、厂商下游补丁。原厂版本横幅与 GKI r37 的构建标识仍有差异。

上述配置涉及存储、文件系统与 I/O；在 OS4 原厂真正的 6.6.118 对应完整私有源码缺失时，不能直接将旧版本的配置名称追加到 GKI。必须先找到源码实现并确认其接口/KMI/行为。**七项差异是最具体的候选原因，未有失败时内核日志直接归因。**

### 后续门槛

1. 无日志/无同版本 OEM 源码时不建议用户继续盲刷同一 GKI 系列；保留已验证正常的原厂 boot。
2. 优先核实同版本 Xiaomi OEM 存储补丁的真实源码，或者在保留原厂 boot 的基础上使用非重编内核的 Root 方案（如果用户接受它与 built-in KSU 不等价）。
3. 新验证必须具备实际 boot-stage/内核错误证据，CI success 不是启动能力证明。
