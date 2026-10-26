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


# KMI-allowlist cross-check for publicly named symbols used by Android Wi-Fi.
# A protected export alone does not prove that a vendor module is blocked.
from concurrent.futures import ThreadPoolExecutor
WATCH_SYMBOLS = {"rfkill_alloc", "rfkill_blocked", "rfkill_destroy", "rfkill_register",
                 "rfkill_resume_polling", "rfkill_set_hw_state_reason",
                 "rfkill_unregister", "arc4_crypt", "arc4_setkey"}
try:
    directory = ("https://android.googlesource.com/kernel/common/+/refs/tags/"
                 + TAG + "/android/?format=JSON")
    with urllib.request.urlopen(urllib.request.Request(directory), timeout=45) as res:
        listing = res.read().decode("utf-8", "replace")
    if listing.startswith(")]}'"):
        listing = listing.split("\n", 1)[1]
    entries = json.loads(listing).get("entries", [])
    names = [x["name"] for x in entries
             if x.get("type") == "blob"
             and x["name"].startswith("abi_gki_aarch64")
             and "protected_exports" not in x["name"]]
    results = {}
    def check(name):
        url = ("https://android.googlesource.com/kernel/common/+/refs/tags/"
               + TAG + "/android/" + name + "?format=TEXT")
        with urllib.request.urlopen(urllib.request.Request(url), timeout=45) as res:
            content = base64.b64decode(res.read()).decode("utf-8", "replace")
        symbols = set(x.strip() for x in content.splitlines()
                      if x.strip() and not x.lstrip().startswith("#"))
        return name, sorted(WATCH_SYMBOLS & symbols)
    with ThreadPoolExecutor(max_workers=6) as workers:
        for name, hits in workers.map(check, names):
            if hits:
                results[name] = hits
    union = set().union(*(set(v) for v in results.values()))
    missing = sorted(WATCH_SYMBOLS - union)
    summary["kmi_crosscheck"] = {
        "list_count": len(names), "watched_symbol_count": len(WATCH_SYMBOLS),
        "kmi_list_matches": results, "not_found_in_kmi_lists": missing,
        "note": "Symbol list membership is necessary context; this is not a runtime module load test."
    }
    print("KMI lists found:", len(names), "watch symbols in KMI:", len(union))
    for name, hits in results.items():
        print(name, ":", ", ".join(hits))
    print("Unlisted watch symbols:", ", ".join(missing) or "none")
except Exception as exc:
    summary["kmi_crosscheck"] = {"error": str(exc),
                                  "status": "inconclusive"}
    print("KMI list cross-check inconclusive:", str(exc))
(DEST/"summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False)+"\n")
