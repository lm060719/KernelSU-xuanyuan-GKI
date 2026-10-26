#!/usr/bin/env python3
"""Reproducible, READ-ONLY audit of the Xiaomi 15 Ultra official OSS code.

Never modifies/repacks an Image. Never uses user or vendor phone binaries.
"""
import difflib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import urllib.request
import base64

XIAOMI_COMMIT = "5a76b8c9010a39420632a20f32fe1bc30498aca0"
XIAOMI_REPOSITORY = "https://github.com/MiCode/Xiaomi_Kernel_OpenSource.git"
XIAOMI_BRANCH = "xuanyuan-v-oss"
GKI_TAG = "android15-6.6-2026-01_r28"
SYMBOLS = (
    "BLOCK_HYBRID_UFS", "F2FS_FS_HYBRID_UFS", "F2FS_VIP_FILE",
    "SCSI_DISCARD", "SCSI_FASTDISCARD",
    "XIAOMI_ENHANCED_IOSTAT", "XIAOMI_EROFS_IOSTAT",
)
SPARSE = (
    "block", "drivers/scsi", "drivers/ufs", "fs/f2fs", "fs/erofs",
    "include/linux", "arch/arm64/configs", "android",
)
KCONFIGS = (
    "block/Kconfig", "drivers/scsi/Kconfig",
    "fs/f2fs/Kconfig", "fs/erofs/Kconfig",
    "drivers/ufs/core/Kconfig",
)
WORK = Path("oss-src")
REPORT = Path("reports/official_xuanyuan")
REPORT.mkdir(parents=True, exist_ok=True)

def run(*args):
    print("+", " ".join(args), flush=True)
    proc = subprocess.run(args, text=True, capture_output=True, timeout=480, check=False)
    if proc.returncode:
        print(proc.stdout[-2500:], proc.stderr[-2500:], flush=True)
        raise RuntimeError(f"Command exited {proc.returncode}: {args[0]}")
    return proc.stdout.strip()

def google_source(path):
    u = ("https://android.googlesource.com/kernel/common/+/refs/tags/"
         + GKI_TAG + "/" + path + "?format=TEXT")
    req = urllib.request.Request(u, headers={"User-Agent": "xuanyuan-source-provenance/1"})
    with urllib.request.urlopen(req, timeout=45) as response:
        return base64.b64decode(response.read(), validate=True).decode("utf-8", "replace")

def main():
    if not WORK.exists():
        run("git", "-c", "protocol.version=2", "clone", "--depth=1",
            "--single-branch", "--filter=blob:none", "--sparse",
            "--branch", XIAOMI_BRANCH, XIAOMI_REPOSITORY, str(WORK))
    run("git", "-C", str(WORK), "sparse-checkout", "set", *SPARSE)
    sha = run("git", "-C", str(WORK), "rev-parse", "HEAD")
    if sha != XIAOMI_COMMIT:
        raise RuntimeError("Xiaomi upstream HEAD changed; manually review new revision: " + sha)

    makefile = (WORK / "Makefile").read_text()
    def mk(name):
        match = re.search(r"^" + re.escape(name) + r"\s*=\s*(\d+)", makefile, re.M)
        return match.group(1) if match else "?"
    version = ".".join([mk(k) for k in ("VERSION", "PATCHLEVEL", "SUBLEVEL")])
    print("Official Xiaomi Linux:", version)
    audit = {
        "official_repo": XIAOMI_REPOSITORY,
        "official_commit": sha,
        "official_branch": XIAOMI_BRANCH,
        "official_linux": version,
        "user_firmware_linux": "6.6.118",
        "gki_comparison_tag": GKI_TAG,
        "important": "This is an older Android V release. Source markers are not proof of boot compatibility.",
        "symbol_references": {},
        "kconfig_diffs": {},
        "related_official_repositories": {
            "devicetree": "MiCode/kernel_devicetree xuanyuan-v-oss",
            "camera": "MiCode/vendor_qcom_opensource_camera-kernel xuanyuan-v-oss",
        },
        "safe_to_flash": False,
    }
    paths = [p for subdir in SPARSE for p in (WORK / subdir).rglob("*")
             if p.is_file() and p.suffix in (".c", ".h", ".S", ".Kconfig", ".mk")]
    paths += [p for subdir in SPARSE for p in (WORK / subdir).rglob("Kconfig*")
              if p.is_file()]
    paths = sorted(set(paths))
    print(f"Scanning {len(paths)} Xiaomi source files in selected storage/ABI areas")
    for key in SYMBOLS:
        hits = []
        for p in paths:
            try:
                data = p.read_text("utf-8", "replace")
            except OSError:
                continue
            for line_number, line in enumerate(data.splitlines(), 1):
                if re.search(r"(?<![A-Z0-9_])(?:CONFIG_)?" + re.escape(key) + r"(?![A-Z0-9_])", line):
                    hits.append({"path": str(p.relative_to(WORK)), "line": line_number,
                                 "text": line.strip()[:170]})
        audit["symbol_references"][key] = {
            "count": len(hits), "examples": hits[:25]
        }
        print(key, "reference count", len(hits))
    for path in KCONFIGS:
        file = WORK / path
        if not file.exists():
            audit["kconfig_diffs"][path] = {"error": "absent in Xiaomi sparse checkout"}
            continue
        xiaomi = file.read_text("utf-8", "replace")
        try:
            gki = google_source(path)
        except Exception as e:
            audit["kconfig_diffs"][path] = {"error": str(e)}
            continue
        changes = list(difflib.unified_diff(
            gki.splitlines(True), xiaomi.splitlines(True),
            fromfile="AOSP r28/" + path,
            tofile="Xiaomi 6.6.30/" + path,
            n=2
        ))
        (REPORT / (path.replace("/", "__") + ".diff")).write_text("".join(changes), "utf-8")
        audit["kconfig_diffs"][path] = {
            "aosp_lines": len(gki.splitlines()), "xiaomi_lines": len(xiaomi.splitlines()),
            "diff_lines": len(changes), "identical": not changes,
        }
        print(path, "diff lines", len(changes))
    dest = REPORT / "source_audit.json"
    dest.write_text(json.dumps(audit, ensure_ascii=False, indent=2) + "\n", "utf-8")
    summary = [
        "# Xiaomi 15 Ultra xuanyuan: official OSS storage-source audit",
        "",
        f"Official MiCode `{XIAOMI_BRANCH}` commit: `{sha}`",
        f"Official Linux base: **{version}**, tested phone's OS4 Linux: **6.6.118**",
        f"Compared Kconfig files against AOSP `{GKI_TAG}`.",
        "",
        "This is only a source audit. No port has been built or validated. **DO NOT FLASH.**",
        "",
        "| Stock-only config | Occurrences in selected official source |",
        "|---|---:|",
    ]
    for key, entry in audit["symbol_references"].items():
        summary.append(f"| `CONFIG_{key}` | {entry['count']} |")
    summary += [
        "", "No occurrences in the selected source areas **does not prove that no",
        "implementation exists anywhere**. The older branch also differs from",
        "the running OS4 release and may not include Xiaomi's later proprietary patches.",
        "",
        "Vendor modules and device-tree/camera repositories are distinct from this common",
        "kernel branch. A module CRC match alone does not establish runtime equivalence.",
    ]
    (REPORT / "README.md").write_text("\n".join(summary) + "\n", "utf-8")
    if version != "6.6.30":
        print("WARNING: Xiaomi source Linux base changed; inspect before using this data.")
    return 0

if __name__ == "__main__":
    sys.exit(main())
