# Xiaomi stock-only storage and I/O feature audit (xuanyuan)

Status: **source audit only; no safe-to-flash image**.

Target stock: Xiaomi 15 Ultra / xuanyuan, OS4.0.0.16.XOACNXM, Linux 6.6.118-android15-8.
Experimental candidate: android15-6.6-2026-01_r28 with KernelSU v3.3.1 built in.

## Findings

Offline comparison of the user's original boot Image (kept private) against the r28 candidate's embedded IKCONFIG yielded seven **stock-only** enabled Kconfig symbols:

| Stock-only config | Area | Source recovery |
|---|---|---|
| CONFIG_BLOCK_HYBRID_UFS | block/UFS | No matching reviewed 6.6.118 source patch |
| CONFIG_F2FS_FS_HYBRID_UFS | F2FS/UFS | No matching reviewed 6.6.118 source patch |
| CONFIG_F2FS_VIP_FILE | F2FS | No matching reviewed 6.6.118 source patch |
| CONFIG_SCSI_DISCARD | SCSI storage | No matching reviewed 6.6.118 source patch |
| CONFIG_SCSI_FASTDISCARD | SCSI/UFS | No matching reviewed 6.6.118 source patch |
| CONFIG_XIAOMI_ENHANCED_IOSTAT | F2FS I/O accounting | No matching reviewed 6.6.118 source patch |
| CONFIG_XIAOMI_EROFS_IOSTAT | EROFS I/O accounting | No matching reviewed 6.6.118 source patch |

**Do not append these CONFIG_* strings or make dummy Kconfig entries**: successful parsing does not imply functionality exists. Likewise, do not patch stock `uname -r` into the test kernel to hide mismatches.

Additional local binary string probes of the stock Image vs r28 Image show:
- `fastdiscard`: stock 6, r28 0
- `vip_file`: stock 2, r28 0
- `erofs_iostat`: stock 10, r28 0
- `multi_unmap`: stock 3, r28 0

These are case-insensitive byte-substring occurrence counts, **not** a disassembly or conclusive feature equivalence test. They support the hypothesis that the stock kernel contains implementation details absent from the test Image.

## Public source audit

- AOSP GKI r28 contains dynamic task_struct upstream support, already verified by Build r28.
- Xiaomi's public `MiCode/Xiaomi_Kernel_OpenSource` branch `xuanyuan-v-oss` has a 6.6.30 kernel tree, not the stock 6.6.118 tree. Direct reads of `block/Kconfig`, `drivers/scsi/Kconfig`, `fs/f2fs/Kconfig`, `fs/erofs/Kconfig`, `fs/f2fs/data.c`, `fs/f2fs/segment.c`, `fs/erofs/data.c` did not find these specific symbols.
- GitHub global code search found the seven config options in several **stock IKCONFIG dumps / defconfig snapshots**, but did not return complete source implementations suitable for 6.6.118. Search coverage is not proof they are unpublished everywhere.
- Separate project `hgn284/xiaomi_17pro_max_sm8850` has independently reconstructed UFS/fastdiscard research code, but it targets Xiaomi 17 Pro Max on **Linux 6.12.69**. Its own README labels its UFS cluster research-only and not a ready replacement for stock UFS; do not transplant this as a safe patch.
- The independent `niazlv/xuanyuan-kernel` project targets xuanyuan and discusses 96 MiB stock boot format, AVB footer preservation, stock boot patchlevel consistency, and prior bootloop risks. These are external project reports, not validation of this candidate.

## Current ABI evidence and what it DOES NOT prove

The previous private samples cover 25 of 390 vendor modules, 800 distinct imported symbols; 734 had providers with identical CRC, 66 lacked provider samples; 0 CRC mismatches among resolved records. Strong evidence for a **subset** of module symbol versions only. It does not certify the other modules, runtime initialization, storage semantics, encryption, vendor-specific sysfs interfaces, or boot.

## Next gates

1. Retrieve only those vendor modules likely to provide the remaining 66 symbols (MT Manager V6 collector prepared offline, shortlist based on device's module listing).
2. Analyze additional providers with full ELF `__versions` records and compare against pinned r28 `Module.symvers`.
3. Determine whether equivalent source patches exist **for exact Android15-6.6**; require provenance and static/source review before experimentally integrating anything.
4. Keep the stock boot image and AVB security patchlevel unchanged when considering a future controlled, recoverable test. Do not build or flash a final boot until the above gates and rollback plan are accepted.

References:
- https://github.com/MiCode/Xiaomi_Kernel_OpenSource/tree/xuanyuan-v-oss
- https://github.com/hgn284/xiaomi_17pro_max_sm8850/tree/main/research/ufs
- https://github.com/niazlv/xuanyuan-kernel
- https://source.android.com/docs/core/architecture/kernel/gki-faq

**Do not upload raw stock boot or vendor .ko files to this public repository.**
