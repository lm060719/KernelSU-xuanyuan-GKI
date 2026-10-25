# Xiaomi 15 Ultra: GKI r28 compatibility hypothesis

**Scope:** read-only AOSP source comparisons and experimental builds. **No image is approved for flashing.**

Device: `xuanyuan` / Android 17 / `OS4.0.0.16.XOACNXM`. Stock Linux: `6.6.118-android15-8-gb9cc6ec16bc8-abogki536571621-4k`.

## Evidence

1. AOSP `android15-6.6-2026-01_r2` is Linux 6.6.118 and was used successfully for **Build #5** with KernelSU v3.3.1 built in (`CONFIG_KSU=y`).
2. The stock embedded kernel config has 10 keys absent in the Build #5 config. The most important concern is the **dynamic task_struct vendor extension**. CRC agreement on several modules does not establish behavioral compatibility.
3. A read-only AOSP Gitiles probe checked source files across `_r2`, `_r26`, `_r28`, `_r43`:
   - `_r2`: no `vendor_data_pad` in the examined sources.
   - `_r26`: added `vendor_data_pad` backing storage and `CONFIG_GKI_TASK_STRUCT_VENDOR_SIZE_MAX=1024`.
   - `_r28`: Xiaomi-specific ABI symbol list `android/abi_gki_aarch64_xiaomi` contains `vendor_data_pad` (Google's own upstream commit is authored by a Xiaomi contributor).
   - `_r43`: retains these features.
4. Stock vendor module sample (seven .ko binaries; not committed): **524 out of 527 unique imported symbols matched available provider CRC values** against Build #5, zero verified mismatches. Three additional symbols are exported by `mca_log.ko`, which was not included in the sample. This is **not** a full KMI or bootability certificate.

## Experimental next gate

An isolated workflow at `.github/workflows/gki-r28-abi-trial.yml` uses AOSP `android15-6.6-2026-01_r28`, integrates the same KernelSU tag, builds a new Image, and explicitly verifies:
- `CONFIG_KSU=y`
- `CONFIG_GKI_DYNAMIC_TASK_STRUCT_SIZE=y`
- `CONFIG_GKI_TASK_STRUCT_VENDOR_SIZE_MAX=1024`
- `CONFIG_ARCH_WANTS_DYNAMIC_TASK_STRUCT=y`
- `CONFIG_ARM64_4K_PAGES=y`

It exports `Module.symvers` for **offline comparison only**. A successful build with these values only passes this **limited source/config gate**. `stock_abi_verified=false`; `safe_to_flash=false`.

## Unresolved blockers

- Xiaomi-only UFS / F2FS / I/O configurations and their implementation cannot be inferred from upstream `gki_defconfig`.
- Compare the r28 CRC table with many **boot-critical** vendor modules; eventually also compare ELF ABI type information where available. Check module vermagic, module signing and kernel release policy.
- Neither forcing the original `uname -r` suffix nor matching module CRCs proves ABI equivalence or that vendor subsystems can initialize.
- Avoid repacking the user's original boot until there is an explicit tested rollback plan, verified image structure, and sufficiently strong compatibility evidence.

## Source references

- https://android.googlesource.com/kernel/common/+/refs/tags/android15-6.6-2026-01_r28
- https://android.1.googlesource.com/kernel/common/+/refs/tags/android15-6.6-2026-01_r26
- https://source.android.com/docs/core/architecture/kernel/abi-monitor
