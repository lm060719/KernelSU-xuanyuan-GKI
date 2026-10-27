#!/usr/bin/env python3
"""Static checks of the compiled Image before packaging. Not a boot test."""
import gzip
import hashlib
import json
from pathlib import Path
import re
import sys

# __traceiter_android_* hooks in stock but missing from older public GKI tags.
STOCK_ONLY_HOOKS = [
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
STOCK_TRACEITER_TOTAL = 796
CONFIG_KEYS = ("CONFIG_KSU", "CONFIG_ARM64_4K_PAGES", "CONFIG_KPROBES", "CONFIG_EXT4_FS",
               "CONFIG_MODVERSIONS", "CONFIG_MODULE_SIG_PROTECT", "CONFIG_CFI_CLANG",
               "CONFIG_LTO_NONE", "CONFIG_LTO_CLANG_THIN", "CONFIG_LTO_CLANG_FULL")


def read_ikconfig(raw):
    start = raw.find(b"IKCFG_ST")
    end = raw.find(b"IKCFG_ED", start)
    if start < 0 or end < 0:
        raise SystemExit("IKCONFIG not found in Image")
    return gzip.decompress(raw[start + 8:end]).decode("utf-8", "replace")


def main():
    if len(sys.argv) != 6:
        raise SystemExit("usage: verify_build.py Image Module.symvers expected_release with_ksu(0|1) report.json")
    image, symvers, release, with_ksu, report_path = sys.argv[1:]
    raw = Path(image).read_bytes()
    exports = {f[1] for f in (l.split() for l in Path(symvers).read_text().splitlines()) if len(f) >= 4}

    banners = sorted({b.decode("utf-8", "replace") for b in re.findall(rb"Linux version ([^ \x00%]+) ", raw)})

    config = read_ikconfig(raw)
    opts = {}
    for key in CONFIG_KEYS:
        m = re.search(r"^" + re.escape(key) + r"=(.+)$", config, re.M)
        opts[key] = m.group(1) if m else "unset"

    iters = {x.decode() for x in set(re.findall(rb"__traceiter_(android_(?:rvh|vh)_[A-Za-z0-9_]+)", raw))}
    hooks = {h: {"traceiter_in_image": h in iters,
                 "tracepoint_exported": f"__tracepoint_{h}" in exports}
             for h in STOCK_ONLY_HOOKS}
    missing_hooks = [h for h, s in hooks.items() if not all(s.values())]

    failures = []
    if banners != [release]:
        failures.append(f"kernel release {banners} != stock {release!r}")
    for key in ("CONFIG_ARM64_4K_PAGES", "CONFIG_KPROBES", "CONFIG_MODVERSIONS"):
        if opts[key] != "y":
            failures.append(f"{key}={opts[key]}")
    if opts["CONFIG_KSU"] != ("y" if with_ksu == "1" else "unset"):
        failures.append(f"CONFIG_KSU={opts['CONFIG_KSU']} but with_ksu={with_ksu}")
    if missing_hooks:
        failures.append(f"stock-only hooks missing: {missing_hooks}")
    if len(iters) < STOCK_TRACEITER_TOTAL:
        print(f"WARNING: {len(iters)} vendor hooks in Image, stock has {STOCK_TRACEITER_TOTAL}", file=sys.stderr)

    report = {
        "image_bytes": len(raw),
        "image_sha256": hashlib.sha256(raw).hexdigest(),
        "kernel_release": banners,
        "config": opts,
        "vendor_hook_traceiter_total": len(iters),
        "stock_vendor_hook_traceiter_total": STOCK_TRACEITER_TOTAL,
        "stock_only_hooks": hooks,
        "module_symvers_exports": len(exports),
        "failures": failures,
        "note": "Static checks only; booting on HyperOS 4 is NOT verified.",
    }
    Path(report_path).write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))
    if failures:
        print("Verification FAILED:", *failures, sep="\n  ", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
