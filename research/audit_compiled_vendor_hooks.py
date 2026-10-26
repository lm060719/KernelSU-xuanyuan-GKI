#!/usr/bin/env python3
"""Read-only r37 Image hook presence inspection; NOT a bootability certification."""
import hashlib
import json
from pathlib import Path
import re
import sys

STOCK_ONLY_14 = [
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
OFFICIAL_SOURCE_EXPECTED = set(STOCK_ONLY_14) - {
    "android_vh_f2fs_is_hiprio_task",
    "android_vh_f2fs_is_usr_task",
}

def main():
    if len(sys.argv) != 4:
        raise SystemExit("Usage: audit_compiled_vendor_hooks.py Image Module.symvers report.json")
    image_path, symvers_path, report_path = map(Path, sys.argv[1:])
    raw = image_path.read_bytes()
    present_iters = {
        x.decode().replace("__traceiter_", "", 1)
        for x in set(re.findall(rb"__traceiter_android_(?:rvh|vh)_[A-Za-z0-9_]+", raw))
    }
    present_points = {
        x.decode().replace("__tracepoint_", "", 1)
        for x in set(re.findall(rb"__tracepoint_android_(?:rvh|vh)_[A-Za-z0-9_]+", raw))
    }
    exports = {}
    for line in symvers_path.read_text(errors="replace").splitlines():
        fields = line.split()
        if len(fields) >= 4:
            exports[fields[1]] = fields[0]
    status={}
    for hook in STOCK_ONLY_14:
        point="__tracepoint_" + hook
        iterator="__traceiter_" + hook
        status[hook] = {
            "traceiter_string_in_image": hook in present_iters,
            "tracepoint_string_in_image": hook in present_points,
            "tracepoint_in_module_symvers": point in exports,
            "traceiter_in_module_symvers": iterator in exports,
            "tracepoint_crc": exports.get(point),
        }
    unresolved=[x for x in STOCK_ONLY_14 if x not in present_iters]
    required_missing=[x for x in OFFICIAL_SOURCE_EXPECTED
                      if x not in present_iters or ("__tracepoint_"+x) not in exports]
    payload = {
        "image_sha256": hashlib.sha256(raw).hexdigest(),
        "image_bytes": len(raw),
        "source_expected_12": sorted(OFFICIAL_SOURCE_EXPECTED),
        "stock_only_14": STOCK_ONLY_14,
        "compiled_traceiter_total": len(present_iters),
        "compiled_tracepoint_total": len(present_points),
        "still_missing_stock_hook_iters": unresolved,
        "compiled_source_expected_12_failures": sorted(required_missing),
        "hook_status": status,
        "limitations": [
            "Counts are derived from string references plus public Module.symvers, not from full device ABI/boot.",
            "The proprietary Xiaomi F2FS callbacks may be compiled without exported __tracepoint symbols.",
            "The rest of the 390 vendor modules were not collected or validated.",
            "The Image must not be considered safe to flash.",
        ],
        "safe_to_flash": False,
    }
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2)+"\n")
    print("Image traceiter hooks:",len(present_iters))
    print("Missing vs xuanyuan stock 14:",unresolved)
    print("Required exported 12 failures:",sorted(required_missing))
    if required_missing:
        raise SystemExit("Static r37 Image vendor hook verification failed")
    return 0

if __name__ == "__main__":
    sys.exit(main())
