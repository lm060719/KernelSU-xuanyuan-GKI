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
