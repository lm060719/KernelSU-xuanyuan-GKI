# 小米 15 Ultra 原厂 OS4 6.6.118 的 BTF 私有函数签名（只读）

数据源：用户可正常启动的原厂 `boot_b.img`（Android Boot v4 kernel payload）及曾卡第二屏的纯 GKI `android15-6.6-2026-01_r37` Image。两份 ARM64 Image 的完整 BTF type records 经本地解析（不是仅凭 `strings` 猜测）。**所有下列函数都在原厂 BTF 中出现，不在 r37 的 BTF FUNC 列表中。**

| 原厂专有函数 | BTF 解出的真实签名 |
|---|---|
| `device_hybrid_capable` | `int (struct dm_target *ti, struct dm_dev *dev, sector_t start, sector_t len, void *data)` |
| `f2fs_hw_support_hybrid` | `bool (struct f2fs_sb_info *sbi)` |
| `f2fs_disable_hybrid` | `int (struct f2fs_sb_info *sbi)` |
| `f2fs_vip_insert` | `int (struct f2fs_sb_info *sbi, nid_t ino)` |
| `f2fs_vip_remove` | `int (struct f2fs_sb_info *sbi, nid_t ino)` |
| `erofs_init_iostat` | `int (struct erofs_sb_info *sbi)` |
| `erofs_iostat_update` | `void (struct erofs_sb_info *sbi, struct bio *bio)` |
| `__drop_discard_cmd` | `bool (struct f2fs_sb_info *sbi)` |
| `f2fs_update_die_usage` | `void (struct f2fs_sb_info *sbi, int ops, unsigned int start_blkaddr, unsigned int nr_blks)` |
| `fastunmap_cmd_count_show` | `ssize_t (struct device *dev, struct device_attribute *attr, char *buf)` |

另外，原厂两个私有 Hook 的真实 trace iterator 签名均为：

```c
int __traceiter_android_vh_f2fs_is_hiprio_task(void *__data, int *ret);
int __traceiter_android_vh_f2fs_is_usr_task(void *__data, int *ret);
```

其 probe stub 均为 `void (void *__data, int *ret)`。这些只是**编译器记录的函数原型**，不是 hook 的注册者、调用点或功能实现，不能据此编造空壳 Hook 或提供可刷机补丁。

## 这意味着什么

1. `device_hybrid_capable` 接收 `dm_target` 与 `dm_dev`，表明设备的 Hybrid 路径涉及 **Device Mapper 设备层**，不只是 F2FS 的可选统计功能。
2. `f2fs_hw_support_hybrid`、`f2fs_disable_hybrid` 和 `f2fs_vip_insert/remove` 接收 F2FS 内部对象，与先前实测的 `f2fs_sb_info` 4,920 vs 4,592 字节、`f2fs_nm_info` 的 `vip` 成员等差异方向吻合。
3. `erofs_iostat_update` 使用 `struct bio`，原厂 `erofs_sb_info` 也添加了 `iostat` 成员：存在实质的 I/O 跟踪路径。
4. 使用此前 58 个真实 `.ko` 的只读 ELF `SHN_UNDEF` 扫描，未见通过明确的 `f2fs|erofs|ufs|discard|hybrid` 外部符号名引用这些私有函数。这不排除未采集模块、内核内建代码或绕过 ELF 符号表的动态查找。

## 不可据此作出的推论

- BTF **不提供函数实现**。有类型与签名不意味着可以安全重建相同的 6.6.118 OEM 实现。
- 原厂 F2FS/Hybrid 逻辑是否为启动必需，尚未通过失败时内核日志证实。
- 已修补的 `init_boot` LKM 仍是纯 GKI 测试中的独立变量；内置 KSU r28 失败则配的是原厂 init_boot。
- **禁止直接刷写下一版 GKI，或靠补七项 config / 插入空壳函数“还原原厂”。**

关联资料：[完整 BTF 差异](https://github.com/lm060719/KernelSU-xuanyuan-GKI/blob/main/analysis/OS4_STOCK_VS_R37_BTF_STORAGE_GAP.md)、[真实 boot/init_boot 实验矩阵](https://github.com/lm060719/KernelSU-xuanyuan-GKI/blob/main/analysis/BOOT_FAILURE_ISOLATION.md)。
