#!/usr/bin/env python3
"""Read-only static validation for experimental ARM64 GKI Image, not a boot image."""
import gzip
import hashlib
import json
import pathlib
import re
import sys

def read_ikconfig(raw):
    marker_start = b"IKCFG_ST"
    marker_end = b"IKCFG_ED"
    start = raw.find(marker_start)
    if start < 0:
        raise RuntimeError("IKCONFIG start marker not found")
    start += len(marker_start)
    end = raw.find(marker_end, start)
    if end < 0:
        raise RuntimeError("IKCONFIG end marker not found")
    return gzip.decompress(raw[start:end]).decode("utf-8", "replace")

def main():
    if len(sys.argv) != 3:
        raise SystemExit("usage: inspect_image.py Image report.json")
    image = pathlib.Path(sys.argv[1])
    report_path = pathlib.Path(sys.argv[2])
    raw = image.read_bytes()
    m = re.search(rb"Linux version (6\.6\.[0-9]+-android15-8[^\x00\r\n]{0,240})", raw)
    report = {
        "image_bytes": len(raw),
        "sha256": hashlib.sha256(raw).hexdigest(),
        "kernel_banner": m.group(1).decode("utf-8", "replace") if m else None,
        "expected_linux_branch": bool(m and b"6.6.118-android15-8" in m.group(1)),
        "stock_kernel_abi_verified": False,
        "safe_to_flash": False,
    }
    try:
        config = read_ikconfig(raw)
        report["ikconfig_found"] = True
        keys = ("CONFIG_KSU", "CONFIG_ARM64_4K_PAGES", "CONFIG_KPROBES",
                "CONFIG_EXT4_FS", "CONFIG_MODVERSIONS", "CONFIG_MODULES")
        opts = {}
        for key in keys:
            enabled = re.search(r"^" + re.escape(key) + r"=(.+)$", config, re.M)
            opts[key] = enabled.group(1) if enabled else "unset"
        report["config"] = opts
        report["ksu_builtin"] = opts["CONFIG_KSU"] == "y"
        report["is_4k_kernel"] = opts["CONFIG_ARM64_4K_PAGES"] == "y"
    except (RuntimeError, OSError, EOFError) as ex:
        report["ikconfig_found"] = False
        report["config_error"] = str(ex)
        report["ksu_builtin"] = False
        report["is_4k_kernel"] = False
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))
    if not (report["expected_linux_branch"] and report["ksu_builtin"] and report["is_4k_kernel"]):
        print("Static validation failed: NOT approved for device flashing", file=sys.stderr)
        return 1
    print("Static checks passed. Vendor/KMI compatibility and boot are NOT verified.")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
