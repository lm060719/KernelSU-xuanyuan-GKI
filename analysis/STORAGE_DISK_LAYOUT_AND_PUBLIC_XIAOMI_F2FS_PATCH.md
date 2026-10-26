# 小米 15 Ultra OS4 / r37：区分磁盘结构与运行时结构，并追踪可公开获取的 Xiaomi F2FS 补丁

> 2026-10-27 只读离线核对；不生成刷机镜像，不改分区。

## 一、来自用户原厂 boot 与已失败 r37 Image 的真实 BTF 对比

输入：
- 用户可正常启动的原厂 `boot_b.img`，SHA256 `f082826b0e9ea020a5ab20db3dacc6814bbbe8b30e7a223eebd81f69d8eeac30`
- 用户已经验证**卡第二屏**的纯 r37 Image，SHA256 `f750918b8063b2cad9b851573ac788edbf18ee50baa3e648e8e29d9a5b53c9fd`

下表只比较各自 BTF 的 `BTF_KIND_STRUCT` 记录：**字节大小、成员名称、成员偏移、位域大小**；不把两份 BTF 的局部 type ID 当作可直接比较的数值。

| 结构体 | 原厂大小 | r37 大小 | BTF 布局 |
|---|---:|---:|---|
| `f2fs_super_block` | 3072 | 3072 | 一致（46 成员） |
| `f2fs_checkpoint` | 192 | 192 | 一致（22 成员） |
| `f2fs_inode` | 4072 | 4072 | 一致（25 成员） |
| `f2fs_nat_block` | 4095 | 4095 | 一致（1 成员） |
| `f2fs_node` | 4096 | 4096 | 一致（2 成员） |
| `f2fs_summary_block` | 4096 | 4096 | 一致（3 成员） |
| `erofs_super_block` | 128 | 128 | 一致（24 成员） |
| `dm_target`（Device Mapper 运行时） | 96 | 96 | 一致（24 成员） |
| `dm_dev`（Device Mapper 运行时） | 40 | 40 | 一致（4 成员） |
| `f2fs_sb_info`（内核运行时） | **4920** | **4592** | **不同** |
| `f2fs_mount_info`（内核运行时） | **512** | **376** | **不同** |
| `f2fs_inode_info`（内核运行时） | **1480** | **1464** | **不同** |
| `f2fs_nm_info`（内核运行时） | **424** | **376** | **不同** |

### 结论的严格边界

1. 上述标准 F2FS/EROFS 结构的 **BTF 布局没有差异**，但这不证明实际磁盘数据格式完全兼容：`feature` 字段可能包含不同的新标志位，代码也可能改变挂载验证条件。
2. 之前发现的 `f2fs_sb_info` 等差异，主要是**内核在 RAM 中的运行时结构**变化，不能直接等同于原厂 /data 的超级块格式变化。
3. BTF 结构一致无法证明不同版本对相同 F2FS feature 位及 Hybrid UFS 的实际行为一致；也没有失败时内核挂载日志。
4. 不能从这组比较直接认定「数据分区无法识别导致第二屏卡住」。这仍是**候选故障路径**。

## 二、找到首个与原厂 BTF 独有函数明确对应的公开补丁

原厂独有的 **80 个 BTF FUNC 名字**中，有一组 `f2fs_fault_report` 及其 trace wrapper。其对应的真正 F2FS 故障追踪功能由小米工程师提交 Linux 上游：

- Linux 上游 patch [`f6b24566035835dc22796f24b1e8738581840b17`](https://kernel.googlesource.com/pub/scm/linux/kernel/git/stable/linux-stable.git/+/f6b24566035835dc22796f24b1e8738581840b17)（2026 年 6 月），主题为 `f2fs: Add trace_f2fs_fault_report`，文件涉及 `fs/f2fs/f2fs.h`、`fs/f2fs/super.c`、`include/trace/events/f2fs.h`。
- 6.6 Android common 后续回移 patch [`2386761e7500733a2823927d4d673a47c5ced5b1`](https://android.googlesource.com/kernel/common/+/2386761e7500733a2823927d4d673a47c5ced5b1)（2026 年 9 月），位于标签 `android15-6.6-2026-07_r8`，相关文件为 `fs/f2fs/checkpoint.c`、`fs/f2fs/f2fs.h`、`include/trace/events/f2fs.h`。

**这组功能在用户原厂 BTF 存在、r37 BTF 缺失，也确实能找到后续公开源代码。** 这是“80 个 OEM 独有函数”里首次对应到了具体可复核的公开补丁来源。但是：

- 这是一组**F2FS 错误诊断 tracepoint**，而不是 Hybrid UFS 或 F2FS VIP 的具体实现。
- 不能因为一个函数同名就默认二进制实现与源码逐行相同；还需针对同版上下文核对。
- 也不能简单拿更新的 Android GKI tag 替换当前 6.6.118 并刷机（升级标签会同时改变大量上游代码/KMI）。
- 不能认为移植此跟踪功能就会修复开机失败；**它可以作为今后真实源码还原工作的一个可审查候选补丁**。

## 三、优先级

1. **最高：** 找到 OS4.0.0.16 的 Hybrid UFS、F2FS VIP、Fast Discard 私有逻辑及其相同基线；已证实实际包含 `device_hybrid_capable`、`f2fs_hw_support_hybrid`、`f2fs_vip_insert` 等，但目前公开搜索未找到可核验的完整实现。
2. **高：** 从原厂能启动的只读运行环境辨别 `/data` F2FS 实际 feature 位、挂载配置与 UFS/Device Mapper 的 Hybrid 状态；若未来采集，仅查询，不可对原始分区运行 `fsck` 修复或写入操作。
3. **中：** 用新公布的 Xiaomi 上游 trace patch 作源码来源目录和代码风格线索；**不是修机补丁**。
4. **持续：** 明确隔离 KernelSU 内置版与 `init_boot` LKM 版的两种失败组合；纯 GKI + 原厂 init_boot 从未验证，不能宣称 KernelSU 已被完全排除。

## 工程复现

`research/compare_arm64_image_btf.py` 已增加 `selected_storage_layouts` 的机器可读字段。请在**本地私有环境**向其传入用户原厂 boot 和已验证 SHA 的纯 r37 Image；绝不把原厂镜像上传到公开 Actions。

参考：[完整 BTF 差异](https://github.com/lm060719/KernelSU-xuanyuan-GKI/blob/main/analysis/OS4_STOCK_VS_R37_BTF_STORAGE_GAP.md)，[boot/init_boot 实测矩阵](https://github.com/lm060719/KernelSU-xuanyuan-GKI/blob/main/analysis/BOOT_FAILURE_ISOLATION.md)。
