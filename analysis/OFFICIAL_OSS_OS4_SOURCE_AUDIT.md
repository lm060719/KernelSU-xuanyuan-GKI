# 小米 15 Ultra 官方源码与 HyperOS 4 适配审计（2026-10-26）

**结论：现有公开的 `xuanyuan-v-oss` 不能直接补齐 Android 17 / OS4.0.0.16.XOACNXM 的全部内核定制，因此目前没有经过验证的可启动内置 KernelSU 镜像。**

## 已验证的源码

- 小米官方内核：`MiCode/Xiaomi_Kernel_OpenSource` 分支 `xuanyuan-v-oss`，提交 `5a76b8c9010a39420632a20f32fe1bc30498aca0`，Linux **6.6.30**。
- 用户原厂 HyperOS 4：Linux **6.6.118-android15-8-gb9cc6ec16bc8-abogki536571621-4k**。
- 其他相关官方源码：`MiCode/kernel_devicetree`、`MiCode/vendor_qcom_opensource_camera-kernel` 均有 `xuanyuan-v-oss` 分支。

## 已完成的 GitHub Actions 源码审计

工作流：`.github/workflows/official-xuanyuan-oss-audit.yml`。按固定提交稀疏检出官方源码，与 AOSP `android15-6.6-2026-01_r28` 对比，均为公开源码，不上传用户 boot 或 .ko。

**扫描 3,710 个存储/ABI 相关源码文件：以下七项在所选文件内均没有引用。**

`CONFIG_BLOCK_HYBRID_UFS`、`CONFIG_F2FS_FS_HYBRID_UFS`、`CONFIG_F2FS_VIP_FILE`、`CONFIG_SCSI_DISCARD`、`CONFIG_SCSI_FASTDISCARD`、`CONFIG_XIAOMI_ENHANCED_IOSTAT`、`CONFIG_XIAOMI_EROFS_IOSTAT`。

五个文件 `block/Kconfig`、`drivers/scsi/Kconfig`、`fs/f2fs/Kconfig`、`fs/erofs/Kconfig`、`drivers/ufs/core/Kconfig` 与 r28 **逐字节相同**。

对比 13 个 C/头文件，均有源码差异，例如 `fs/f2fs/data.c` 91 个 diff 块、`drivers/ufs/core/ufshcd.c` 82 个。**这些 diff 跨越 Linux 6.6.30 到 6.6.118，绝大多数差异无法直接识别为 Xiaomi 私有补丁，严禁自动套用到 r28。**

## 真实启动试验

- `r28 + KernelSU v3.3.1`：卡第二屏。
- **纯 `r28`（不含 KernelSU）也卡第二屏**。
- 两次刷回用户同版本原厂 `boot_b.img`：正常开机。
- CRC 抽样检查不等于设备启动能力；缺失的七个配置仍**未证实就是根因**。

同类线索：[WildKernels Issue #302](https://github.com/WildKernels/GKI_KernelSU_SUSFS/issues/302)（Xiaomi 15 Pro、Android 17，另一机型，不能当成本设备证据）。

## 下一步门槛

1. 寻找与 OS4.0.0.16.XOACNXM / 6.6.118 **精确匹配**的 Xiaomi OEM 源码或可信的补丁来源。
2. 若只有旧版 6.6.30，应与**同年代同基础内核**比较提炼 OEM 改动，而不是将旧文件覆盖新版。
3. 优先建立能保留 boot 阶段错误的诊断方式；没有确证的修复方案前不应反复刷机。
4. 如接受改变原始目标，可评估保留原厂内核的 Root 方式；其与 KernelSU built-in 不等价。

**当前仍不批准刷写任何新试验镜像。** 完整机器报告见工作流产物 `official-xuanyuan-oss-source-audit`。
