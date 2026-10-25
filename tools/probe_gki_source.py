#!/usr/bin/env python3
"""Read-only source capability comparison across AOSP GKI tags.

This is a SOURCE presence probe, not a kernel ABI test or flash certification.
Gitiles content is base64-encoded; never decode a 404/HTML error as source.
"""
import base64
from concurrent.futures import ThreadPoolExecutor, as_completed
import json
from pathlib import Path
import re
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

TAGS = ["android15-6.6-2026-01_r2", "android15-6.6-2026-01_r26",
        "android15-6.6-2026-01_r28", "android15-6.6-2026-01_r43"]
PATHS = ["arch/arm64/configs/gki_defconfig", "init/Kconfig",
         "arch/Kconfig", "init/main.c", "init/init_task.c",
         "kernel/fork.c", "include/linux/sched.h",
         "drivers/scsi/Kconfig", "fs/f2fs/Kconfig",
         "block/Kconfig", "android/abi_gki_aarch64_xiaomi"]
MARKERS = ["GKI_DYNAMIC_TASK_STRUCT_SIZE",
           "ARCH_WANTS_DYNAMIC_TASK_STRUCT",
           "GKI_TASK_STRUCT_VENDOR_SIZE_MAX",
           "vendor_data_pad", "arch_task_struct_size",
           "BLOCK_HYBRID_UFS", "F2FS_FS_HYBRID_UFS",
           "F2FS_VIP_FILE", "SCSI_DISCARD",
           "SCSI_FASTDISCARD", "XIAOMI_ENHANCED_IOSTAT",
           "XIAOMI_EROFS_IOSTAT"]

def fetch(tag, path):
    url = f"https://android.googlesource.com/kernel/common/+/refs/tags/{tag}/{path}?format=TEXT"
    for attempt in range(3):
        try:
            with urlopen(Request(url, headers={"User-Agent": "GKI-source-compat-probe/1"}),
                         timeout=25) as response:
                raw = response.read(8_000_000)
            return base64.b64decode(raw, validate=True).decode("utf-8", "replace"), None
        except HTTPError as exc:
            if exc.code == 404:
                return None, "not found at this tag"
            issue = f"HTTP {exc.code}"
        except (URLError, OSError, ValueError) as exc:
            issue = str(exc)
        time.sleep(attempt + 1)
    return None, issue

def inspect(tag, path):
    source, error = fetch(tag, path)
    if source is None:
        return tag, path, {"error": error}
    present = {}
    lines = source.splitlines()
    for marker in MARKERS:
        locations = [(idx, ln.strip()[:180]) for idx, ln in enumerate(lines, 1)
                     if marker in ln and not ln.strip().startswith(("#", "//", "/*", "*"))]
        if locations:
            present[marker] = {"count": len(locations), "examples":
                               [{"line": i, "text": s} for i, s in locations[:3]]}
    return tag, path, {"markers": present}

def main():
    out = {"warning": "Source markers prove neither enabled config nor vendor ABI compatibility.",
           "tags": {tag: {"paths": {}} for tag in TAGS}}
    with ThreadPoolExecutor(max_workers=8) as pool:
        tasks = [pool.submit(inspect, tag, path) for tag in TAGS for path in PATHS]
        for task in as_completed(tasks):
            tag, path, result = task.result()
            out["tags"][tag]["paths"][path] = result
    dest = Path("reports/gki_source_matrix.json")
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n")
    for tag, info in out["tags"].items():
        found = {k for p in info["paths"].values()
                 for k in p.get("markers", {}).keys()}
        errs = [p for p, v in info["paths"].items()
                if "error" in v and v["error"] != "not found at this tag"]
        print(f"{tag}: markers found {len(found)}/{len(MARKERS)}; network errors {len(errs)}")
        print("  present: " + (", ".join(sorted(found)) or "none"))
        if errs: print("  errors: " + ", ".join(errs))
    return 0 if any(
        "markers" in val
        for info in out["tags"].values()
        for val in info["paths"].values()) else 1

if __name__ == "__main__":
    raise SystemExit(main())
