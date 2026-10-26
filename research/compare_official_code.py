#!/usr/bin/env python3
"""Read-only implementation comparison: Xiaomi 6.6.30 vs AOSP GKI r28 6.6.118.

Large differences across Linux versions MUST NOT be interpreted as OEM patches.
"""
import base64
import difflib
import hashlib
import json
from pathlib import Path
import sys
import urllib.request

OFFICIAL = Path("oss-src")
GKI_TAG = "android15-6.6-2026-01_r28"
OUT = Path("reports/official_xuanyuan/code_diffs")
OUT.mkdir(parents=True, exist_ok=True)
FILES = [
    "block/blk-core.c",
    "block/blk-mq.c",
    "fs/f2fs/data.c",
    "fs/f2fs/segment.c",
    "fs/f2fs/super.c",
    "fs/f2fs/file.c",
    "fs/erofs/data.c",
    "fs/erofs/zdata.c",
    "drivers/scsi/sd.c",
    "drivers/scsi/scsi_lib.c",
    "drivers/ufs/core/ufshcd.c",
    "drivers/ufs/core/ufshcd-priv.h",
    "include/linux/blkdev.h",
]

def load_gki(path):
    url = f"https://android.googlesource.com/kernel/common/+/refs/tags/{GKI_TAG}/{path}?format=TEXT"
    req = urllib.request.Request(url, headers={"User-Agent": "xuanyuan-official-code-diff/1"})
    with urllib.request.urlopen(req, timeout=60) as response:
        return base64.b64decode(response.read(), validate=True).decode("utf-8", "replace")

def main():
    report = {
        "source": "MiCode/Xiaomi_Kernel_OpenSource xuanyuan-v-oss @ 5a76b8c9010a39420632a20f32fe1bc30498aca0",
        "source_kernel": "6.6.30",
        "compared_against": GKI_TAG,
        "comparison_warning": "Differences include ordinary Linux fixes between 6.6.30 and 6.6.118, NOT necessarily Xiaomi patches.",
        "files": {}
    }
    for path in FILES:
        xi_file = OFFICIAL / path
        if not xi_file.is_file():
            report["files"][path] = {"status": "missing_from_xiaomi_checkout"}
            print(path, "absent from Xiaomi source")
            continue
        xi = xi_file.read_text(encoding="utf-8", errors="replace")
        try:
            gki = load_gki(path)
        except Exception as e:
            report["files"][path] = {"status": "GKI_download_failed", "error": str(e)}
            print(path, "fetch failure", e)
            continue
        sha_xi = hashlib.sha256(xi.encode()).hexdigest()
        sha_gki = hashlib.sha256(gki.encode()).hexdigest()
        # Generate full textual patch for local review; NEVER auto-apply it.
        patch = list(difflib.unified_diff(
            gki.splitlines(keepends=True),
            xi.splitlines(keepends=True),
            fromfile=f"AOSP-r28/{path}",
            tofile=f"Xiaomi-6.6.30/{path}",
            n=3
        ))
        dest = OUT / (path.replace("/", "__") + ".diff")
        dest.write_text("".join(patch), encoding="utf-8")
        plus = sum(1 for ln in patch if ln.startswith("+") and not ln.startswith("+++"))
        minus = sum(1 for ln in patch if ln.startswith("-") and not ln.startswith("---"))
        chunks = sum(1 for ln in patch if ln.startswith("@@ "))
        report["files"][path] = {
            "status": "ok",
            "sha256_xiaomi": sha_xi,
            "sha256_aosp_r28": sha_gki,
            "identical": sha_xi == sha_gki,
            "xiaomi_lines": xi.count("\n") + 1,
            "aosp_lines": gki.count("\n") + 1,
            "diff_hunks": chunks,
            "plus_lines": plus,
            "minus_lines": minus,
            "diff_path": str(dest),
            "do_not_auto_apply": True
        }
        print(path, f"identical={sha_xi == sha_gki}", f"diff_hunks={chunks}",
              f"added={plus}", f"removed={minus}", flush=True)
    payload = json.dumps(report, indent=2, ensure_ascii=False) + "\n"
    (OUT / "comparison.json").write_text(payload, encoding="utf-8")
    return 0 if any(r.get("status") == "ok" for r in report["files"].values()) else 1

if __name__ == "__main__":
    sys.exit(main())
