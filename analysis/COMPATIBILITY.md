# Xuanyuan HyperOS 4 kernel compatibility checkpoint

**Status: Build #4 compiles successfully, but the Image is NOT approved for flashing.**

Target phone: Xiaomi 15 Ultra (`xuanyuan`), Android 17 `OS4.0.0.16.XOACNXM`.
The user's own `boot_b.img` was analyzed privately and is NOT stored in this public repository.

| Property | Stock Image | Build #4 |
|---|---|---|
| Linux KMI | 6.6.118-android15-8 | 6.6.118-android15-8 |
| Local version | gb9cc6ec16bc8-abogki536571621-4k | maybe-dirty-4k |
| Binary Image size | 36,866,560 | 36,858,368 |
| Embedded config entries | 6,184 | 6,178 |
| KernelSU built-in | absent | CONFIG_KSU=y |
| Verified vendor module CRC/ABI | not tested | not tested |

The embedded kernel configurations differ in **14 keys**: 4 KernelSU-specific entries in the new build, 10 stock options absent from the new build. No shared option had a different value.

Stock-only options:
- `CONFIG_ARCH_WANTS_DYNAMIC_TASK_STRUCT=y`
- `CONFIG_GKI_DYNAMIC_TASK_STRUCT_SIZE=y`
- `CONFIG_GKI_TASK_STRUCT_VENDOR_SIZE_MAX=1024`
- `CONFIG_BLOCK_HYBRID_UFS=y`
- `CONFIG_F2FS_FS_HYBRID_UFS=y`
- `CONFIG_F2FS_VIP_FILE=y`
- `CONFIG_SCSI_DISCARD=y`
- `CONFIG_SCSI_FASTDISCARD=y`
- `CONFIG_XIAOMI_ENHANCED_IOSTAT=y`
- `CONFIG_XIAOMI_EROFS_IOSTAT=y`

**Important:** Some features require kernel source patches and can alter vendor-module assumptions. Do not change a version string or append CONFIG_ entries to paper over their absence. This is NOT a formal ABI check.

A separate read-only GitHub Action (`probe-gki-tags.yml`) checked upstream `gki_defconfig` for releases `android15-6.6-2026-01_r2`, `r26`, `r43`:
- r2: 0/9 tracked option values present in `gki_defconfig`.
- r26 and r43: 1/9 present (the 1024 vendor task padding value).
- Absence in `gki_defconfig` alone **does not establish that an option is absent from Kconfig or the compiled kernel**.

More source and device evidence are needed before constructing a device test boot:
1. Identify a corresponding Xiaomi-customized 6.6.118 kernel patchset, or reproduce the missing features from verified upstream patches.
2. Compare built-in kernel configs, exported symbol CRC / kernel ABI and vendor module `vermagic` against matching `vendor_dlkm` / `system_dlkm` modules.
3. Plan a recoverable test procedure including A/B slot status, original boot and AVB.
4. Only after verification, consider repacking the original boot header v4 image for controlled testing.

Do not upload raw boot images to this **public** repository unless you explicitly intend to publish them.
