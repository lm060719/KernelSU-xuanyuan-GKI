#!/usr/bin/env python3
"""Declare and export the two Xiaomi-private F2FS vendor hooks of the stock kernel.

Prototypes come from the stock OS4 kernel BTF (see
analysis/OS4_OEM_BTF_FUNCTION_SIGNATURES.md):
    int __traceiter_android_vh_f2fs_is_hiprio_task(void *__data, int *ret);
    int __traceiter_android_vh_f2fs_is_usr_task(void *__data, int *ret);

Only the hook points are added so vendor modules that register them can load;
public GKI F2FS never fires them.
"""
from pathlib import Path
import sys

HOOKS = ("android_vh_f2fs_is_hiprio_task", "android_vh_f2fs_is_usr_task")


def replace_once(path, old, new):
    text = path.read_text()
    if text.count(old) != 1:
        raise SystemExit(f"{path}: anchor not found exactly once: {old!r}")
    path.write_text(text.replace(old, new))


def main():
    common = Path(sys.argv[1] if len(sys.argv) > 1 else "common")
    header = common / "include/trace/hooks/fs.h"
    hooks_c = common / "drivers/android/vendor_hooks.c"
    symbols = common / "android/abi_gki_aarch64_xiaomi"

    if all(h in header.read_text() for h in HOOKS):
        print("Xiaomi F2FS hooks already present")
        return 0

    anchor = """DECLARE_HOOK(android_vh_f2fs_restore_priority,
	TP_PROTO(struct task_struct *p, int saved_prio),
	TP_ARGS(p, saved_prio));
"""
    decls = "".join(f"""
DECLARE_HOOK({h},
	TP_PROTO(int *ret),
	TP_ARGS(ret));
""" for h in HOOKS)
    replace_once(header, anchor, anchor + decls)

    anchor = "EXPORT_TRACEPOINT_SYMBOL_GPL(android_vh_f2fs_restore_priority);\n"
    exports = "".join(f"EXPORT_TRACEPOINT_SYMBOL_GPL({h});\n" for h in HOOKS)
    replace_once(hooks_c, anchor, anchor + exports)

    # Unsigned vendor modules may only use KMI-listed symbols (MODULE_SIG_PROTECT).
    lines = ["", "# Xiaomi OS4 private F2FS hooks"]
    for h in HOOKS:
        lines += [f"  __traceiter_{h}", f"  __tracepoint_{h}"]
    with symbols.open("a") as f:
        f.write("\n".join(lines) + "\n")

    print("Added", ", ".join(HOOKS))
    return 0


if __name__ == "__main__":
    sys.exit(main())
