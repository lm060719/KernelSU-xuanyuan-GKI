# KernelSU GKI built-in prototype — Xiaomi 15 Ultra (xuanyuan)

> **Experimental build only. Do not flash any produced Image or boot.img.**
>
> The GKI kernel below is a **candidate AOSP baseline**, NOT proven byte-for-byte or ABI compatible with the vendor kernel in HyperOS 4.

## Device and source baseline

- Device: Xiaomi 15 Ultra (`xuanyuan`)
- OS: Android 17, HyperOS `OS4.0.0.16.XOACNXM`
- Stock kernel: `6.6.118-android15-8-gb9cc6ec16bc8-abogki536571621-4k`
- Boot image: `boot_b.img`, Android boot header v4, 96 MiB (kept offline; **never upload personal partition data to this public repository**)
- AOSP candidate: `common-android15-6.6-2026-01` at kernel tag `android15-6.6-2026-01_r2`
- KernelSU: `tiann/KernelSU` tag `v3.3.1`, compiled **built-in** with `CONFIG_KSU=y`, not LKM.

## CI

See [GitHub Actions](../../actions): a push to `main` triggers the experimental build, with an optional manual rerun.

The workflow:
1. Frees unneeded space on ephemeral Ubuntu runner, installs Google's `repo` tool.
2. Syncs the fixed manifest branch, checks out the candidate GKI tag, records exact SHA.
3. Checks out KernelSU v3.3.1, integrates kernel code, enables `CONFIG_KSU=y`.
4. Builds `//common:kernel_aarch64_dist` with Kleaf/Bazel.
5. Verifies that output contains `CONFIG_KSU=y`, records versions, uploads **unflashable** Image and diagnostic logs.

**Known limitations:** A matching Linux version/KMI alone cannot ensure that Xiaomi vendor modules or AVB chain will accept the kernel. A successful CI build is only the first gate. No automatic repacking or flashing is included.

References:
- https://source.android.com/docs/core/architecture/kernel/gki-android15-6_6-release-builds
- https://github.com/tiann/KernelSU/releases/tag/v3.3.1
- https://kernelsu.org/guide/how-to-build.html
