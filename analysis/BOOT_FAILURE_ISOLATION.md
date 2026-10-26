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
