#!/usr/bin/env python3
"""Read-only comparison of public GKI tag defconfig files."""
import base64
import json
import re
import sys
import time
import urllib.request
from pathlib import Path

TAGS = (
    "android15-6.6-2026-01_r2",
    "android15-6.6-2026-01_r26",
    "android15-6.6-2026-01_r43",
)
STOCK = {
    "CONFIG_GKI_DYNAMIC_TASK_STRUCT_SIZE": "y",
    "CONFIG_GKI_TASK_STRUCT_VENDOR_SIZE_MAX": "1024",
    "CONFIG_BLOCK_HYBRID_UFS": "y",
    "CONFIG_F2FS_FS_HYBRID_UFS": "y",
    "CONFIG_F2FS_VIP_FILE": "y",
    "CONFIG_SCSI_DISCARD": "y",
    "CONFIG_SCSI_FASTDISCARD": "y",
    "CONFIG_XIAOMI_ENHANCED_IOSTAT": "y",
    "CONFIG_XIAOMI_EROFS_IOSTAT": "y",
}

def fetch(tag):
    url = (f"https://android.googlesource.com/kernel/common/+/refs/tags/{tag}"
           "/arch/arm64/configs/gki_defconfig?format=TEXT")
    last = None
    for attempt in range(3):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "KernelSU-xuanyuan-GKI-compat-probe/1"})
            with urllib.request.urlopen(req, timeout=40) as rsp:
                return base64.b64decode(rsp.read(), validate=True).decode("utf-8")
        except Exception as exc:
            last = exc
            time.sleep(attempt + 1)
    raise RuntimeError(str(last))

def main():
    out = {"notice": "Compares gki_defconfig only; absence does not prove Kconfig or code lacks the feature", "tags": {}}
    for tag in TAGS:
        try:
            cfg = {}
            for line in fetch(tag).splitlines():
                match = re.match(r"^(CONFIG_[A-Z0-9_]+)=(.+)$", line)
                if match:
                    cfg[match[1]] = match[2]
            values = {key: cfg.get(key) for key in STOCK}
            match_count = sum(cfg.get(k) == v for k, v in STOCK.items())
            out["tags"][tag] = {"status": "ok", "matches": match_count, "expected_count": len(STOCK), "values": values}
            print(f"{tag}: {match_count}/{len(STOCK)} options match in defconfig", flush=True)
        except Exception as exc:
            out["tags"][tag] = {"status": "error", "error": str(exc)}
            print(f"{tag}: {exc}", flush=True)
    Path("reports").mkdir(exist_ok=True)
    Path("reports/gki_tag_probe.json").write_text(json.dumps(out, indent=2, ensure_ascii=False)+"\n")
    return int(not any(v["status"] == "ok" for v in out["tags"].values()))

if __name__ == "__main__":
    sys.exit(main())
