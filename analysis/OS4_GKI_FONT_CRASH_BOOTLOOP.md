# HyperOS 4 / AOSP GKI 6.6.118：卡在开机动画的实机排查（2026-10-27/28）

测试内核：`android15-6.6-2026-01_r43`，版本号与原厂一致，补齐 14 个原厂独有 vendor hook，
AnyKernel3 刷入（原厂 boot 头 / vbmeta 不变）。现象：一直停在 "Xiaomi HyperOS" 开机动画。

## 已证实并修复：system_dlkm GKI 模块被拒绝加载

内核日志（KernelSU 抓日志模块，以 root 读取 dmesg）：

```
rfkill: exports protected symbol rfkill_alloc
cfg80211: Unknown symbol rfkill_alloc (err -2)
btpower: Unknown symbol rfkill_register (err -2)
modprobe: Failed to insmod '/system_dlkm/.../rfkill.ko' with args '': Permission denied
```

另外还有 mii、6lowpan、can、ieee802154、tipc、usbserial 等模块被拒绝。原因：system_dlkm 里的模块由原厂构建密钥签名，
自编内核不信任该密钥，`MODULE_SIG_PROTECT` 把它们当作厂商模块，拒绝其导出受保护符号。
修复：构建时清空 `android/abi_gki_protected_exports_aarch64`。修复后已加载模块数 535 → 593（原厂 602），
高通 `cnd`（WiFi QoS）不再反复崩溃。

## 仍未解决：system_server 字体初始化崩溃

每次开机 system_server 都以同一位置崩溃，开机动画无法结束：

```
#00 libminikin.so  minikin::FontFamily::FontFamily(...)+220
#02 libhwui.so     android::FontFamily_Builder_build
#12 miui-framework.jar  miui.util.font.MiCustomizedFonts.buildMiCustomizedFonts
SIGSEGV SEGV_MAPERR
```

反汇编实机 `libminikin.so`（BuildId `a3da11d7…`）与 `libhwui.so`（`621bd2fd…`）：

- `libhwui` 调用 `minikin::registerLocaleList(langTags)`，返回值原样作为 `localeListId` 传入 `FontFamily::create`。
- 构造函数里 `LocaleListCache::getByIdInternal(localeListId)` 返回 `mLocaleLists[id]`（每项 56 字节），
  随后 `ldrb w9, [x0, #0x32]` 越界。
- 崩溃时 `localeListId`（`x22`）**在 3 次开机、100 多次崩溃中恒为 `0x200d0000`**；该值恰为 system_server
  Java 堆 `[anon:dalvik-main space (region space)]` 中的一个地址。
- `registerLocaleList` → `LocaleListCache::getIdInternal(string)` 命中字符串缓存时直接返回节点 `+0x28` 处的值，
  说明这张 `unordered_map` 的内存已被破坏（指向的节点内容已是别的数据）。

同一崩溃也出现在小米 15 Pro（同一 OGKI 内核字符串）刷 GKI 内核后：
[WildKernels/GKI_KernelSU_SUSFS#302](https://github.com/WildKernels/GKI_KernelSU_SUSFS/issues/302)。

## 已排除

| 方向 | 依据 |
|---|---|
| KernelSU | 不含 KernelSU 的对照版（原厂 init_boot）同样崩溃，`x22` 同为 `0x200d0000` |
| GKI 模块加载 | 修复后仍崩溃 |
| SELinux | 原厂 `/sys/fs/selinux/policy_capabilities` 与 r43 相同（8 项，policyvers 33）；`font_fallback.xml` 的 lnk_file 拒绝原厂也有 |
| 字体文件读取 / EROFS | 两种内核下 `/system/fonts`、`/product/fonts` 共 294 个文件 sha256 完全一致 |
| CPU 特性 | 原厂 `/proc/cpuinfo` Features 全部在 r43 `hwcap_str` 中 |
| ART GC 类型 | `ro.dalvik.vm.enable_uffd_gc=false`，两边均为 CollectorTypeCC |
| zram swap / 换页 | 实验模块挡住 zram，整个开机过程 `SwapTotal: 0 kB`，仍崩溃 17 次，`x22` 同为 `0x200d0000` |
| 更新的 AOSP 分支 | 原厂独有的混合 UFS、F2FS VIP、EROFS LZ4 修改等在 r43、2026-10 分支和 android15-6.6 最新提交里都不存在（仅 `f2fs_fault_report` 在 2026-10 之后出现） |

## 结论

能低成本验证的方向都已排除（swap 由 [`diagnostics/noswap-module`](../diagnostics/noswap-module) 实测排除）。
同一套用户空间，只换成 AOSP GKI 内核，system_server 里 minikin 的 `LocaleListCache` 内存就会被确定性地破坏；
根源在小米未公开的内核修改里。要继续，需要与 OS4.0.0.16 对应的小米内核源码，或在开机过程中对 system_server
做内存写入断点之类的深度调试。在此之前，可用方案是原厂内核 + KernelSU LKM。
