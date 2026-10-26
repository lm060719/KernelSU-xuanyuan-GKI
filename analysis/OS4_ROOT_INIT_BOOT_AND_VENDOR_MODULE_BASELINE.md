# OS4.0.0.16 6.6.118：真实 Vendor .ko 版本与 Root 加载路径再审计

## 已从用户本机离线收集文件确认的事实

设备：Xiaomi 15 Ultra（xuanyuan），OS4.0.0.16.XOACNXM，原厂内核 `6.6.118-android15-8-gb9cc6ec16bc8-abogki536571621-4k`。

从此前的 `xuanyuan_module_critical_mt_v5`、`xuanyuan_module_provider_mt_v6` 以及 `xuanyuan_module_root_v4` 三批样本提取了共 **58 个互不重名的真实厂商 .ko**：

| `.modinfo/vermagic` | 数量 |
|---|---:|
| `6.6.57-android15-8-gbc807ab2c5a8-4k SMP preempt mod_unload modversions aarch64` | 55 |
| `6.6.57-android15-8-4k SMP preempt mod_unload modversions aarch64` | 2 |
| `6.6.57-4k-gbc807ab2c5a8 SMP preempt mod_unload modversions aarch64` | 1 |

**58 个均包含 ELF `__versions` section 名称。** 不应因为 6.6.57 与运行中 6.6.118 不同就判断加载失败；Linux 开启 `CONFIG_MODVERSIONS` 时可忽略 `vermagic` 第一个空格前的内核版本部分，并逐符号核验 CRC。真实执行路径可能包含其他厂商校验。官方文档：[Android loadable kernel modules](https://source.android.com/docs/core/architecture/kernel/loadable-kernel-modules)。

原始样本仅用于用户私有工作区中的只读分析，**未将 .ko、boot 或 init_boot 镜像上传到公开 GitHub**。约 390 个已发现的 `/vendor_dlkm/lib/modules` 文件中还有大量样本未验证。

## 已失败的实验

- GKI 6.6.118 `2026-01_r28` + KernelSU built-in：卡第二屏
- 纯 GKI `r28`：卡第二屏
- 纯 GKI `r37`（重获 12 个原厂标准 Vendor Hook）：仍卡第二屏
- 每次重新刷回原厂 boot：均恢复正常

上述实验**仅替换 boot.img**，没有记录手机 **`init_boot` 是否已经通过 KernelSU LKM 或其他 Root 方案修改**。这使得此前称作「不带 KernelSU 的对照版」在系统启动层面可能仍含有 KernelSU LKM 注入变量，不能完全排除它与新 Image 的相互作用。

KernelSU 官方 LKM 安装说明：带有 `init_boot` 的 Android 13+ 设备通常在 `init_boot` 修补 RAMDisk，而 built-in/GKI 模式替换 `boot` 中的内核 Image。参考 https://kernelsu.org/guide/installation.html 。

这只是待验证的**潜在干扰因素**，并无证据证明 LKM 导致第二屏卡死。也不能直接修改、恢复或清空手机的 `init_boot` 来求证——已有 Root 环境及解密状态必须保护。

## 新增只读手机诊断

仓库新增 `diagnostics/xuanyuan_os4_runtime_baseline.sh`，手机端 Root Shell 执行：

```sh
su
sh /sdcard/Download/xuanyuan_OS4_readonly_runtime_diag.sh
```

脚本记录：
- 内核版本和当前 A/B 槽位
- `/proc/modules` 实际加载的模块名、`modules.load` 简单对照
- KernelSU/SU 相关 **目录是否存在** 的弱线索
- 当前活跃 `boot` 和 `init_boot` 分区 **SHA256**（不会复制镜像）
- pstore 文件名（无崩溃内容）

用户工作区也提供了可直接复制到手机的 ZIP 脚本。

**判定门槛：** 将活跃 `boot` hash 与此前同版本原厂 `boot_b.img` hash 核验；如 `boot` 确为原厂而 Root 正常，说明 Root 并非靠重新编译原厂 boot 中的 KernelSU built-in，接着必须检查 `init_boot` 与 Root 实际实现。`init_boot` hash 必须与**同版本真正的原厂 init_boot** 比较才能判断其是否修改，不应凭任意 hash 猜测。

在缺乏相同固件的 OEM 私有源码、实机启动错误日志和全量 vendor .ko 分析前，**不制作、不刷写下一版 GKI**。
