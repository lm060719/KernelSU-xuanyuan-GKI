#!/usr/bin/env python3
"""Compare 14 stock xuanyuan trace hooks across pinned public android15-6.6 tags.

This analysis never uploads stock binaries and never creates flashable images.
A source EXPORT_TRACEPOINT_SYMBOL_GPL is not proof of a symbol in built Image.
"""
import base64
import concurrent.futures
import json
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

TAGS = ["android15-6.6-2026-01_r" + str(i) for i in (28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38)]
# Unique stock-only __traceiter_android_* symbols seen in the xuanyuan boot,
# compared against the failed vanilla r28 Image (no stock firmware included).
STOCK_ONLY = [
    "android_vh_cma_alloc_lat_end",
    "android_vh_cma_alloc_lat_start",
    "android_vh_dma_heap_buffer_alloc_lat_end",
    "android_vh_dma_heap_buffer_alloc_lat_start",
    "android_vh_f2fs_is_hiprio_task",
    "android_vh_f2fs_is_usr_task",
    "android_vh_folio_end_writeback",
    "android_vh_folio_start_writeback",
    "android_vh_mm_direct_reclaim_end",
    "android_vh_mm_direct_reclaim_start",
    "android_vh_mmc_attach_sd",
    "android_vh_mmc_blk_reset",
    "android_vh_mmc_gpio_cd_irqt",
    "android_vh_sdhci_get_cd",
]
OUT = Path("reports/xuanyuan_hook_tags")
OUT.mkdir(parents=True, exist_ok=True)

def fetch(tag, file):
    uri = (f"https://android.googlesource.com/kernel/common/+/refs/tags/{tag}/"
           f"{file}?format=TEXT")
    err = None
    for attempt in range(4):
        try:
            req = urllib.request.Request(uri, headers={"User-Agent": "xuanyuan-stock-hook-audit/1"})
            with urllib.request.urlopen(req, timeout=55) as resp:
                return base64.b64decode(resp.read(), validate=True).decode("utf-8", "replace")
        except (OSError, ValueError) as exc:
            err = exc
            time.sleep(0.4 * (attempt + 1))
    raise RuntimeError(f"{tag} {file}: {err}")

def inspect(tag):
    exported = fetch(tag, "drivers/android/vendor_hooks.c")
    makefile = fetch(tag, "Makefile")
    version = {
        k: re.search(r"^" + k + r"\s*=\s*(\d+)", makefile, re.M).group(1)
        for k in ("VERSION", "PATCHLEVEL", "SUBLEVEL")
    }
    known = set(re.findall(r"EXPORT_TRACEPOINT_SYMBOL(?:_GPL)?\s*\(\s*(android_(?:rvh|vh)_[A-Za-z0-9_]+)\s*\)", exported))
    # Count only the 14 established missing hooks; no guessing from modules.
    return {
        "tag": tag,
        "kernel_version": ".".join(version.values()),
        "exported_count": len(known),
        "stock_missing_14_resolved_in_source": sorted(set(STOCK_ONLY) & known),
        "stock_missing_14_still_absent_in_source": sorted(set(STOCK_ONLY) - known),
        "coverage": len(set(STOCK_ONLY) & known),
    }

def main():
    reports = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as pool:
        futures = {pool.submit(inspect, tag): tag for tag in TAGS}
        for fut in concurrent.futures.as_completed(futures):
            tag = futures[fut]
            try:
                value = fut.result()
                reports.append(value)
                print(f"{tag}: kernel {value['kernel_version']}, "
                      f"14-hook exported coverage {value['coverage']}/14", flush=True)
            except Exception as e:
                print("ERROR", tag, e, flush=True)
                reports.append({"tag":tag,"error":str(e),"coverage": None})
    reports.sort(key=lambda v: TAGS.index(v["tag"]))
    result = {
        "device": "Xiaomi 15 Ultra (xuanyuan)",
        "stock_kernel": "6.6.118-android15-8-gb9cc6ec16bc8-abogki536571621-4k",
        "failed_kernel_tag": "android15-6.6-2026-01_r28",
        "stock_traceiter_count": 796,
        "failed_vanilla_traceiter_count": 782,
        "stock_only_14_hooks": STOCK_ONLY,
        "tested_tags": reports,
        "limitations": [
            "Only public source EXPORT_TRACEPOINT_SYMBOL[_GPL] presence is checked.",
            "The actual ARM64 Image, symbol CRC, module imports, and runtime are not validated here.",
            "Unlisted Xiaomi vendor modules may reference additional symbols.",
            "KernelSU integration is irrelevant to this analysis.",
            "Do not flash any untested kernel based only on this report.",
        ],
        "flashable": False,
    }
    (OUT/"tag_hook_matrix.json").write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n")
    md=["# 15 Ultra 原厂缺失 14 项 Hook：GKI 月度 Tag 来源矩阵", "",
        "基于你原厂 Image 与失败的 r28 Image 的字符串证据；不包含任何原厂镜像。", "",
        "| GKI tag | 内核版本 | 14 项原厂 Hook 在源码中的导出 |",
        "|---|---|---:|"]
    for r in reports:
        md.append(f"| \`{r['tag']}\` | {r.get('kernel_version', 'ERROR')} | {str(r.get('coverage', 'ERROR'))}/14 |")
    md += ["", "只统计源码 \`EXPORT_TRACEPOINT_SYMBOL_GPL\`：即使 14/14 也不代表实际编译出的 Image 一定包含它们、更不代表可以开机。",
           "", "## 原厂存在、失败 r28 缺少的 Hook", "",
           *[f"- \`{x}\`" for x in STOCK_ONLY]]
    (OUT/"README.md").write_text("\n".join(md)+"\n")
    failures = [r for r in reports if "error" in r]
    if failures:
        raise SystemExit(f"{len(failures)} GKI release tags could not be audited")
    if not all(r["kernel_version"]=="6.6.118" for r in reports):
        raise SystemExit("Version drift in monthly release: review before proceeding")
    return 0

if __name__ == "__main__":
    sys.exit(main())
