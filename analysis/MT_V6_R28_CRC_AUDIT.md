# MT V6 / r28: Kernel module symbol CRC audit

Scope: **Read-only offline comparison** against private phone samples. No flashing, no stock or vendor binaries committed.

Device: Xiaomi 15 Ultra (xuanyuan), Android 17, OS4.0.0.16.XOACNXM.
Experimental build: AOSP GKI `android15-6.6-2026-01_r28` with KernelSU v3.3.1 built in.

## Input coverage

- V4: 7 vendor modules
- V5: 18 vendor modules
- V6: 33 vendor modules, collected as root via MT Manager; zero file read errors
- **Total 58 distinct ELF .ko modules**, compared to a directory listing of **390**.
- **1,095 unique imported symbols** across the 58 samples.

## Symbol version results (r28)

| Result | Count |
|---|---:|
| Matched kernel vmlinux CRC | 814 |
| Matched GKI module CRC | 9 |
| Matched collected vendor .ko exporter CRC | 144 |
| **Total symbol CRC matches** | **967** |
| Import symbols without a sampled export provider | **128** |
| CRC mismatches where a provider was found | **0** |
| Same imported name with conflicting CRC among sampled modules | **0** |
| Same exported name with conflicting CRC among sampled vendor modules | **0** |

Sample coverage: **967/1,095 = 88.31%**. This is NOT a device-wide compatibility score or boot probability.

V5 had 66 unresolved symbols; V6 resolves 14 of those, leaving 52 old unresolved. Newly collected modules introduce 76 additional unresolved names, for the total of 128.

Among symbols used by the collected modules, r28 and r2 yield identical resolved symbol status. This **does not** establish runtime or private layout equivalence. Sample .ko `vermagic` mostly begins `6.6.57`; phone runs `6.6.118`. This is not by itself a CRC conflict.

## Source/provider bottlenecks

Several samples declare `depends=` references that are not among these 58 binaries, notably `qcom_scmi_client`, `qcom-scm`, `smem`, `rproc_qcom_common`, `qcom-pmu-lib`, `qcom-dcvs`, `qcom_ipc_logging`, and a number of Xiaomi `mca_*` modules. Some may be built into the kernel or live outside the listed partition; missing a sampled provider does not prove the compiled kernel lacks the feature.

## Remaining major blocker: Xiaomi-private functionality

The `r28` image has 7 missing stock-only configs related to **hybrid UFS, FastDiscard/SCSI, F2FS VIP, F2FS I/O and EROFS I/O statistics**. No fully verified source-compatible reproduction is presently integrated. Correct symbol CRC matches alone cannot certify their functionality.

Thus **safe_to_flash = false**. Do not repack and flash this GKI candidate without fuller firmware/source equivalence checks and a recoverable plan.

Detailed comparison is retained in a private conversation report (NOT uploaded here). Avoid committing phone boot or private .ko binaries to this public repository.
