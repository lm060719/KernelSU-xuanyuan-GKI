# 小米 15 Ultra OS4 原厂内核 vs AOSP GKI r37：BTF 真实实现与结构体差异

> **2026-10-27 只读离线分析。没有刷机、没有产生可刷镜像。**
> **结论：原厂内核与 r37 并非只差七个 Kconfig 项，原厂额外包含真实的存储实现函数及不同的 F2FS/EROFS 数据结构布局。** 这些是可能导致启动失败的候选差异，**尚无 boot-stage 日志证明单项差异就是根因**。

## 数据来源与一致性

- 原厂：用户自己备份且已验证可正常启动的 `boot_b.img`；Android Boot header v4 的 kernel payload `36866560` bytes。
- 对照：成功 CI [#40330094335](https://github.com/lm060719/KernelSU-xuanyuan-GKI/actions/runs/40330094335) 构建的纯 GKI `android15-6.6-2026-01_r37` Image，`36801024` bytes，SHA256 `f750918b8063b2cad9b851573ac788edbf18ee50baa3e648e8e29d9a5b53c9fd`。
- 两个真实 ARM64 Image 都包含有效 BTF header，`BTF_KIND_FUNC`、`BTF_KIND_STRUCT` 等 section 由直接解析 BTF type records 得到，**不是任意对二进制执行 `strings` 后猜测**。
- 原厂 BTF type records **141630**、独特 BTF FUNC 名称 **60475**；r37 type records **141468**、FUNC 名称 **60400**。
- 共有 **60395** 个同名 BTF FUNC；原厂独有 **80**；r37 独有 **5**。

BTF 提供编译后的类型与函数描述；不会自动提供完整源码或替代内核启动日志。它仍然比仅做 `CONFIG_*` 对比能更精确地定位改动。

## 原厂 80 个独有 BTF 函数名（实际精确集合）

```text
__add_to_free_list
__alloc_busy
__blkdev_query_disk
__bpf_trace_f2fs_fault_report
__bpf_trace_lz4_decompress_end
__bpf_trace_lz4_decompress_start
__drop_discard_cmd
__f2fs_cluster_blocks
__find_data_block
__init_discard_policy
__probestub_android_vh_f2fs_is_hiprio_task
__probestub_android_vh_f2fs_is_usr_task
__probestub_f2fs_fault_report
__probestub_lz4_decompress_end
__probestub_lz4_decompress_start
__remove_free_nid
__traceiter_android_vh_f2fs_is_hiprio_task
__traceiter_android_vh_f2fs_is_usr_task
__traceiter_f2fs_fault_report
__traceiter_lz4_decompress_end
__traceiter_lz4_decompress_start
busy_threshold_show
busy_threshold_store
device_hybrid_capable
en_iostat_enable_show
en_iostat_enable_store
erofs_destroy_iostat
erofs_init_iostat
erofs_iostat_config_parse
erofs_iostat_daily_latency_show
erofs_iostat_daily_stats_reset
erofs_iostat_latency_stats_reset
erofs_iostat_record_start
erofs_iostat_update
erofs_iostat_window_latency_show
f2fs_disable_hybrid
f2fs_fault_report
f2fs_get_alloc_range
f2fs_get_iostat
f2fs_hw_hybrid_get_avail
f2fs_hw_support_hybrid
f2fs_hybrid_die_info_show
f2fs_init_ext_cursegs
f2fs_inode_set_task_flag
f2fs_iostat_daily_latency_show
f2fs_iostat_window_latency_show
f2fs_iostat_window_latency_store
f2fs_update_die_usage
f2fs_vip_bsearch
f2fs_vip_insert
f2fs_vip_remove
fastunmap_cmd_count_show
fastunmap_cmd_count_store
iostat_array_size
iostat_daily_latency_show
iostat_daily_stats_reset
iostat_latency_stats_reset
iostat_latency_threshold_ms_show
iostat_latency_threshold_ms_store
iostat_window_latency_show
iostat_window_period_s_show
iostat_window_period_s_store
low_threshold_show
low_threshold_store
multi_unmap_len_max_show
need_defragment
perf_trace_f2fs_fault_report
perf_trace_lz4_decompress_end
perf_trace_lz4_decompress_start
queue_max_discard_segments_store
ratio_show
ratio_store
set_inode_dst_flag
trace_event_raw_event_f2fs_fault_report
trace_event_raw_event_lz4_decompress_end
trace_event_raw_event_lz4_decompress_start
trace_raw_output_f2fs_fault_report
trace_raw_output_lz4_decompress_end
trace_raw_output_lz4_decompress_start
z_erofs_get_lz4_decompress_inplace_margin
```

r37 独有的五个 BTF 函数：`del_page_from_free_list`、`f2fs_reset_iostat`、`f2fs_update_iostat`、`iostat_info_seq_show`、`read_xattr_block`。

## 存储结构：10 项 sizeof 不一致，14 项成员描述有差异

| 结构体 | 原厂 sizeof | r37 sizeof | 同名成员偏移变化 | 原厂新增成员 |
|---|---:|---:|---:|---|
| `f2fs_sb_info` | 4920 | 4592 | **98** | `hi` |
| `f2fs_inode_info` | 1480 | 1464 | 0 | `task_flag`、`cold_flag`、`dst_flag` |
| `f2fs_nm_info` | 424 | 376 | 0 | `vip` |
| `f2fs_mount_info` | 512 | 376 | 0 | `cold_perm_ext_cnt`、`cold_perm_exts`、`ext_start` |
| `f2fs_stat_info` | 944 | 800 | **13** | `dbt`、`rbt`、`wbt` |
| `discard_cmd_control` | 8424 | 8408 | **7** | `undiscard_large_blks` 等 3 项 |
| `erofs_sb_info` | 456 | 448 | 0 | `iostat` |
| `f2fs_bio_info` | 448 | 440 | **8** | 无新增名称，但原有成员偏移改变 |
| `f2fs_gc_control` | 72 | 64 | 0 | `dir` |
| `f2fs_io_info` | 128 | 120 | 0 | `alloc_range` |

> 成员偏移由 BTF 位偏移计算。统计只对同名、单一定义的 `BTF_KIND_STRUCT` 记录比较；大小一致但成员命名不同的记录亦可能存在。完整 BTF type/layout 比对远比仅列出这些行更丰富。

## 与 KernelSU LKM v3 报告的关系

用户 V3 报告在 70 项非 `Module.symvers` 导出依赖中只列出前 35 项。这 35 个名称，在**原厂与 r37** 两份内核的原始 Image 中都能找到 **33** 个完整的 NUL 分隔名称；两边无法通过该字符串方法确认的均为 `init_mm` 与 `__tracepoint_sys_enter`。进一步从 BTF 的 `FUNC` records 看，双方的函数名覆盖也高度一致；数据符号不能用函数名表推断不存在。

**这 35 个名称目前没有显示出原厂 vs r37 的明显差异。** 更重要的潜在线索是**两份内核在 F2FS/EROFS 的真实实现与内部数据结构布局上的差异**，但仍不能排除 LKM 的引导时序和其他厂商依赖。

## 严格结论与后续工程策略

1. 之前 GKI r28+内置 KSU 在原厂 init_boot 下失败；纯 r28/r37 在**含 LKM 的修补 init_boot**下失败。仍没有真正 root-free 的 GKI 实测对照。
2. BTF 已证明 Xiaomi OS4 存储代码不是在旧版 `xuanyuan-v-oss` 配置中加七个宏就能还原的。**不能盲目复制旧版结构体或强行增加空壳函数来“骗过”符号检查**。
3. 若厂商模块访问内部结构，跨布局可能导致 ABI 风险；但这些结构自身也可能只由内核内建 F2FS 驱动内部使用。**不能从结构大小变化直接推断 vendor .ko 越界，必须有具体访问者和失败日志。**
4. 仍以原厂 boot + 当前已修补 init_boot 的可工作组合为基准；不生成/推荐新刷机镜像。
5. 独立的 [r37 System.map 链接符号审计](https://github.com/lm060719/KernelSU-xuanyuan-GKI/actions/workflows/gki-r37-linked-symbol-audit.yml) 用于证实内核符号是否真正链接，不能代替 OEM 存储代码恢复。
