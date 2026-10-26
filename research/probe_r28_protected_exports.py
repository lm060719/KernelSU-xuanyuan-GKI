#!/usr/bin/env python3
"""Probe pinned AOSP GKI r28 protected exports; PUBLIC UPSTREAM files only.

Analysis aid for Xiaomi 15 Ultra second-logo bootloop. This does not modify a
kernel, weaken protections, or establish a device-level cause.
"""
import base64
import hashlib
import json
from pathlib import Path
import urllib.request

TAG = "android15-6.6-2026-01_r28"
PATHS = [
    "android/abi_gki_protected_exports_aarch64",
    "android/gki_aarch64_protected_modules",
    "android/abi_gki_aarch64_xiaomi",
]
DEST = Path("reports/protected_exports_probe")
DEST.mkdir(parents=True, exist_ok=True)
summary = {"tag": TAG, "sources": {}, "stock_vendor_abi_verified": False,
           "flashable": False}
for path in PATHS:
    url = f"https://android.googlesource.com/kernel/common/+/refs/tags/{TAG}/{path}?format=TEXT"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "xuanyuan-readonly-probe/1"})
        with urllib.request.urlopen(req, timeout=45) as res:
            blob = base64.b64decode(res.read(), validate=True)
        assert blob and b"<!DOCTYPE" not in blob
        content = blob.decode("utf-8", "replace")
        symbols = [line.strip() for line in content.splitlines()
                   if line.strip() and not line.strip().startswith("#")]
        outname = Path(path).name + ".txt"
        (DEST/outname).write_text(content, encoding="utf-8")
        summary["sources"][path] = {
            "status": "ok", "line_count": len(symbols),
            "sha256": hashlib.sha256(blob).hexdigest(), "saved_as": outname,
            "first_five": symbols[:5]
        }
        print(path, "lines", len(symbols))
    except Exception as err:
        summary["sources"][path] = {"status": "error", "error": str(err)}
        print("Unable to fetch", path, str(err))
(DEST/"summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False)+"\n")
if summary["sources"][PATHS[0]]["status"] != "ok":
    raise SystemExit("Cannot acquire upstream protected export list; results are inconclusive")
