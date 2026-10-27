# KernelSU 内置 GKI 内核 — 小米 15 Ultra (xuanyuan)

> **实验性构建，未经实机验证能开机。** HyperOS 4 原厂内核是小米闭源定制的 OGKI
> (`6.6.118-android15-8-gb9cc6ec16bc8-abogki536571621-4k`)，公开 AOSP 源码无法完全还原。
> 刷入前务必备份，并确认能用 fastboot 救回。

## 这一版做了什么

GitHub Actions 工作流 [`kernel-gki.yml`](.github/workflows/kernel-gki.yml)：

1. 源码：AOSP `android15-6.6-2026-01_r43`（Linux 6.6.118，KMI `android15-8`，与原厂相同）。
2. **版本号与原厂一字不差**：`6.6.118-android15-8-gb9cc6ec16bc8-abogki536571621-4k`（脚本校验，不一致即失败）。
3. **补齐原厂独有的 vendor hook**：r43 已含 14 个中的 12 个；另外两个小米私有 F2FS hook
   `android_vh_f2fs_is_hiprio_task` / `android_vh_f2fs_is_usr_task` 按原厂 BTF 中的原型
   `(int *ret)` 声明、导出并加入 KMI 列表，避免厂商驱动因 "unknown symbol" 加载失败。
4. **允许原厂签名的 GKI 模块加载**：`system_dlkm` 里的 rfkill/cfg80211/bluetooth 等模块用原厂密钥签名，
   本内核不信任，会被当作厂商模块拒绝导出“受保护符号”（实测 `rfkill: exports protected symbol rfkill_alloc`，
   WiFi/蓝牙随之失效）。构建时清空 `abi_gki_protected_exports_aarch64`，只关闭这项导出检查。
5. KernelSU `v3.3.1` 内置（`CONFIG_KSU=y`）；同时编一个**不含 KernelSU 的对照版**（`noKernelSU`），
   用来区分问题是否与 KernelSU 有关（刷对照版时要配原厂 init_boot）。
6. 产物是 **AnyKernel3 刷机包**：只替换手机自身 boot 里的内核，原厂 boot 头、安全补丁级别、
   cmdline、AVB footer 和内嵌 vbmeta 全部保留（不修改 vbmeta 标志）。

之前三次失败的测试记录见 [`analysis/`](analysis/)。

## 下载

Actions → 最新一次成功的 “Build KernelSU GKI AnyKernel3 (xuanyuan)” → Artifacts →
`AnyKernel3-xuanyuan-KernelSU`（内置 KernelSU）或 `AnyKernel3-xuanyuan-noKernelSU`（对照版），
解压后得到 `AK3-xuanyuan-...zip`。

## 刷机前准备（必须）

1. 用 root shell 备份当前**两个**分区（`_b` 换成你的当前槽位，`getprop ro.boot.slot_suffix` 可查）：
   ```sh
   su
   dd if=/dev/block/by-name/boot_b of=/sdcard/Download/boot_b_stock.img bs=1M
   dd if=/dev/block/by-name/init_boot_b of=/sdcard/Download/init_boot_b_lkm.img bs=1M
   ```
   拷到电脑上。
2. 电脑上准备好 `fastboot`。

## 刷机

内置版 KernelSU 不能与 LKM 版同时存在，所以要先恢复原厂 init_boot：

1. KernelSU 管理器 → 卸载 → **还原原厂镜像**（先不要重启）。如果没有这个选项，
   就从同版本 `OS4.0.0.16.XOACNXM` 完整卡刷包的 `payload.bin` 提取原厂 `init_boot.img`，
   刷完 zip 后在 fastboot 里 `fastboot flash init_boot init_boot.img`。
2. 用 Kernel Flasher / Horizon Kernel Flasher 刷入 AnyKernel3 zip（刷到当前槽位）。
3. 重启。开机后安装 KernelSU 管理器 v3.3.1，应显示“工作中（内置/GKI）”。

## 卡开机怎么救

进 fastboot（关机后按住音量下 + 电源），在电脑上执行：

```sh
fastboot flash boot boot_b_stock.img
fastboot flash init_boot init_boot_b_lkm.img
fastboot reboot
```

即可回到刷机前的状态（原厂内核 + LKM 版 KernelSU）。

## 卡开机时抓日志

[`diagnostics/bootlog-module`](diagnostics/bootlog-module) 是一个 KernelSU 模块（把两个文件打成 zip 即可安装）：
测试内核（内置 KernelSU）开机时，在 post-fs-data 阶段开始记录 dmesg、logcat、开机进度和 tombstone，
持续 10 分钟，存到 `/data/local/tmp/xuanyuan_bootlog/boot_<时间>/`。原厂内核 + LKM 开机时它什么都不做，
所以救回后不会覆盖失败那次的日志。如果失败后那里没有新目录，说明测试内核没有走到 post-fs-data。

## 参考

- https://github.com/tiann/KernelSU/releases/tag/v3.3.1
- https://kernelsu.org/guide/installation.html
- https://github.com/osm0sis/AnyKernel3
