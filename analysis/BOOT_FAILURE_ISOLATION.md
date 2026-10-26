
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

# xuanyuan second-logo boot failure: controlled isolation experiment

**Status:** Unresolved device boot failure. No replacement boot.img is approved for flashing.

## Ground truth from phone testing

- Stock `boot_b.img` boots Xiaomi 15 Ultra / Android 17 / OS4.0.0.16.XOACNXM.
- Experimental `android15-6.6-2026-01_r28` + KernelSU v3.3.1 built-in boot image stalled at the second splash/logo.
- Flashing the original boot image restored normal startup.
- `/sys/fs/pstore` was empty; `/proc/last_kmsg` and `/data/misc/logd` were absent.
- `/data/vendor/ramdump/mcrash_history` only contained old entries (June and September 2026), not an established October crash.
- `/data/system/dropbox/SYSTEM_BOOT` entries from 19:28 and 19:40 showed the original stock kernel; no log proving how far the experimental kernel booted was recovered.
- Root-managed system properties (e.g. `ro.boot.verifiedbootstate`) are spoofed on this phone; **do not infer actual bootloader state from those props**. Confirm via actual bootloader/Fastboot state before any future write.

## Isolation hypothesis

Two things changed simultaneously in the failed image: using generic AOSP GKI instead of stock Xiaomi kernel and integrating KernelSU.

The independent control build `.github/workflows/gki-r28-vanilla-control.yml` **only omits KernelSU** while keeping r28, the 4K / task-structure configuration, Kleaf target, and pinning. Any changes in the local kernel version string and image bytes are expected when source integration changes.

## Outcome interpretation (if an explicitly authorized controlled test is later performed)

| Vanilla control | KernelSU r28 | Interpretation |
|---|---|---|
| boots | hangs | KernelSU integration or its interaction with Xiaomi userspace/vendor code becomes the leading cause; compare KSU hooks/init and build delta |
| hangs | hangs | AOSP-vs-Xiaomi runtime differences or shared boot image packaging become leading causes; do **not** blame KernelSU alone |
| boots | boots | not currently observed; investigate testing differences |
| cannot be tested | hangs | static comparison only; cause remains uncertain |

**A successful CI build is not proof that the control will boot.**
This experiment also cannot rule out a subtle interaction among KernelSU, system services, device modules and proprietary code.

## Safety gates prior to any boot test

- Verify actual bootloader state from bootloader/Fastboot, not modified Android props.
- Keep an exact backup of current stock `boot_b.img` and record active A/B slot; do not assume it stayed the same.
- Keep fastboot/USB and recovery capabilities available in case the image hangs.
- Preserve the stock boot header v4, its 96 MiB partition layout, boot security patchlevel, and AVB footer metadata; never substitute a generic Kleaf 64 MiB boot.img.
- Do **not** flash a test kernel to both A/B slots, relock bootloader, erase `userdata`, or change boot/vbmeta patchlevels.
- Control artifact is distributed as **Image only** while validation is pending. It is not a flashable boot image.
- Do not upload a private stock boot image to this public GitHub repository.

## Build gates

The control workflow confirms the pristine common source tree, omits KernelSU completely, validates `CONFIG_KSU` disabled, validates ARM64 4K pages, dynamic task struct support and vendor task padding 1024. It exports `Module.symvers` and a static report. This is NOT a full vendor ABI test.

## Outstanding work

- Confirm control CI output actually passed (Image, config audit, symbol table).
- Offline compare control and KSU config / exported CRC / banner to isolate any differences beyond KSU.
- Separately assess stock-only UFS/F2FS/SCSI functionality (7 missing config symbols). Matching CRC is not equivalence.
- Only then consider an explicitly requested controlled device test, with stock backup and recoverability.


## 2026-10-26: Vanilla r28 boot experiment completed

**Observed on the actual xuanyuan handset:**
- Pinned `android15-6.6-2026-01_r28` + KernelSU v3.3.1: second-logo boot hang; stock boot restoration works.
- The **same r28 baseline without KernelSU**: also second-logo boot hang; restoring original boot restores normal operation.
- Therefore KernelSU is **not required** to trigger the failure. Shared r28-vs-stock runtime differences and/or shared boot packaging remain in scope. Rebuilding more variations of KernelSU alone is not justified.

**Offline boot image review:**
- Original stock, KSU and vanilla boot images are 100,663,296 bytes (96 MiB), Android Boot Header v4 with ramdisk_size=0 and signature_size=0.
- AVBf footer is present, and embedded vbmeta can be located via the recorded offset in both failed images. These facts do not prove bootloader acceptance.
- The custom images necessarily invalidate the original AVB signature; do not infer actual bootloader state from Android properties if the device uses a spoofing module.

**AOSP GKI protected export audit (read-only CI):**
- r28's upstream `android/abi_gki_protected_exports_aarch64` has **507 symbols**.
- 58 sampled stock .ko vendor modules intersect that list at **9 distinct imported symbols**, from `cfg80211.ko` (`rfkill_*`) and `mac80211.ko` (`arc4_crypt`, `arc4_setkey`).
- Crucial nuance: **all 9 are in the r28 `android/abi_gki_aarch64_qcom` KMI symbol list**, and hence appear in the GKI allowlist union. Their protected-export membership ALONE is **not evidence of load rejection**. Do not claim this is the confirmed boot-loop cause.
- Third-party xuanyuan-kernel project reports protected-exports-induced vendor module problems in a different build context. That is a lead to verify, not evidence about this exact HyperOS 4 firmware.
- Independent Xiaomi feature gap remains: seven stock-only UFS/F2FS/SCSI/I/O config symbols and unverified matching implementation.
- Stock `uname -r` references git hash `b9cc6ec16bc8`; AOSP GitHub public mirror could not resolve that hash, while an older xuanyuan kernel hash `e56cf6b09cca` was resolvable. This check cannot show whether the stock hash is available in Xiaomi's internal source or other upstreams.

**New priority:** stop device flashing until a concrete, high-confidence boot failure mechanism is demonstrated, ideally by an OS4.0.0.16.XOACNXM-compatible Xiaomi kernel tree or authenticated boot-stage diagnostics. Do not treat matching CRCs, GKI Build Success, or partial header verification as proof of bootability.
