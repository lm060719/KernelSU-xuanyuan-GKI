#!/usr/bin/env python3
"""Read-only compare user-reported LKM names to linked r37 GKI System.map.

The 35 names were shown in the user's v3 diagnostic report, not inferred from
Module.symvers. The user's raw LKM and init_boot are never uploaded to GitHub.
This does not certify KernelSU loading or phone bootability.
"""
import hashlib
import json
from pathlib import Path
import sys

# The phone's v3 report displayed only the FIRST 35 of 70 names not found
# in r37 Module.symvers. All 70 are NOT known locally; do not claim otherwise.
FIRST_35 = """
__arm64_sys_close __arm64_sys_setns __hashtab_insert __set_fixmap
__tracepoint_sys_enter abort_creds alloc_uid anon_inode_getfile_secure
avc_has_perm avc_ss_reset avtab_alloc avtab_destroy avtab_insert_nonunique
avtab_search_node avtab_search_node_next change_pid commit_creds cond_compute_av
copy_from_user_nofault copy_to_kernel_nofault copy_to_user_nofault
current_is_single_threaded dcache_clean_inval_poc ebitmap_cmp ebitmap_contains
ebitmap_destroy ebitmap_get_bit ebitmap_set_bit ext4_unregister_sysfs
filp_open groups_alloc groups_sort init_mm kallsyms_lookup kallsyms_lookup_name
""".split()
assert len(FIRST_35) == 35 and len(set(FIRST_35)) == 35

OLD_R37_IMAGE_SHA256 = "f750918b8063b2cad9b851573ac788edbf18ee50baa3e648e8e29d9a5b53c9fd"

def load_map(path):
    result = {}
    bad = 0
    for line in path.read_text(errors="replace").splitlines():
        v = line.split()
        if len(v) < 3:
            bad += 1
            continue
        address, symtype, symname = v[:3]
        if len(symtype) != 1:
            bad += 1
            continue
        result.setdefault(symname, []).append({
            "type": symtype,
            "is_absolute": symtype.upper() == "A",
            "is_undefined": symtype.upper() == "U",
        })
    return result, bad

def load_symvers(path):
    items = {}
    for line in path.read_text(errors="replace").splitlines():
        row = line.split()
        if len(row) >= 4:
            items[row[1]] = {"crc": row[0], "provider": row[2], "export_type": row[3]}
    return items

def main():
    if len(sys.argv) != 5:
        raise SystemExit("Usage: audit_r37_lkm_symbol_map.py System.map Module.symvers Image report_dir")
    smap, symvers, image, out = (Path(x) for x in sys.argv[1:])
    out.mkdir(parents=True, exist_ok=True)
    kallsyms, failed_lines = load_map(smap)
    exports = load_symvers(symvers)
    imagehash = hashlib.sha256(image.read_bytes()).hexdigest()
    result = {}
    for name in FIRST_35:
        entry = [i for i in kallsyms.get(name, []) if not i["is_undefined"]]
        result[name] = {
            "linked_system_map": bool(entry),
            "system_map_types": sorted(set(i["type"] for i in entry)),
            "module_symvers_exported": name in exports,
            "note": "System.map presence does NOT imply kallsyms loader can resolve this at runtime",
        }
    linked = sorted(x for x,v in result.items() if v["linked_system_map"])
    absent = sorted(x for x,v in result.items() if not v["linked_system_map"])
    summary = {
        "device": "Xiaomi 15 Ultra xuanyuan",
        "kernel": "AOSP android15-6.6-2026-01_r37 (vanilla, no KSU)",
        "scope": "35 of 70 LKM undefined names not exported by Module.symvers and displayed by user's v3 report",
        "image_sha256": imagehash,
        "image_matches_prior_successful_r37": imagehash == OLD_R37_IMAGE_SHA256,
        "prior_r37_image_sha256": OLD_R37_IMAGE_SHA256,
        "system_map_unique_names": len(kallsyms),
        "module_symvers_export_count": len(exports),
        "system_map_ignored_lines": failed_lines,
        "first35_found_linked": len(linked),
        "first35_absent_linked": len(absent),
        "linked_symbols": linked,
        "absent_symbols": absent,
        "per_symbol": result,
        "limitations": [
            "No raw userspace KernelSU module is available in this runner, only 35 names printed by MT v3.",
            "This cannot answer for the other 35 names omitted from the user's TXT.",
            "System.map shows linked symbols, not their runtime visibility, CRC, signatures, ABI, or hook layout.",
            "LTO or linker scripts can affect symbol naming and presence.",
            "No private kernel or init_boot data uploaded to GitHub.",
            "No flashable boot image is generated or validated here."
        ],
        "safe_to_flash": False
    }
    (out/"r37_lkm_first35_linked_symbols.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    lines=[
        "# Xiaomi 15 Ultra: r37 LKM undefined symbols vs linked System.map",
        "",
        f"Actual compiled r37 Image SHA256: \`{imagehash}\`",
        f"Image byte-for-byte matches previous r37: **{imagehash == OLD_R37_IMAGE_SHA256}**",
        "",
        "Only **35** reported names available. The user's v3 script printed the first 35 of 70;",
        "do not generalize this report to the 35 undisclosed names.",
        "",
        f"Linked in r37 System.map: **{len(linked)}/35**",
        f"Not found in linked r37 System.map: **{len(absent)}/35**",
        "",
        "| Unexported LKM dependency | In r37 System.map |",
        "|---|---|"
    ]
    lines += [f"| \`{name}\` | {'yes' if result[name]['linked_system_map'] else '**no**'} |"
              for name in FIRST_35]
    lines += ["",
              "**Limitations:** System.map presence is not proof that KernelSU's manual",
              "relocation loader can resolve the symbol or that replacing the OEM",
              "6.6.118 Image would boot. This is read-only CI; DO NOT FLASH.",
              ""]
    (out/"README.md").write_text("\n".join(lines), encoding="utf-8")
    print(f"r37 System.map names={len(kallsyms)}, exports={len(exports)}")
    print(f"r37 Image SHA256={imagehash}, identical to prior build={summary['image_matches_prior_successful_r37']}")
    print(f"FIRST_35 linked={len(linked)}/35; absent={len(absent)}/35")
    if absent:
        print("Not found in r37 linked kernel:", ", ".join(absent))
    if len(kallsyms) < 1000:
        raise SystemExit("Unexpectedly tiny System.map: refusing to interpret")
    return 0

if __name__=="__main__":
    sys.exit(main())
