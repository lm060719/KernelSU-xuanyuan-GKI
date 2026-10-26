#!/usr/bin/env bash
set -Eeuo pipefail

# AOSP GKI 6.6.118 + KernelSU built-in for Xiaomi 15 Ultra (xuanyuan).
# Produces an AnyKernel3 zip that only swaps the kernel inside the phone's own
# boot image (header, patch level, cmdline and AVB vbmeta blob stay stock).
ROOT="${GKI_ROOT:-$PWD/gki}"
DIST="${DIST_DIR:-$PWD/dist}"
REPORTS="${REPORT_DIR:-$PWD/reports}"
OUT="${OUT_DIR:-$PWD/out}"
MANIFEST_BRANCH="${MANIFEST_BRANCH:-common-android15-6.6-2026-01}"
GKI_TAG="${GKI_TAG:-android15-6.6-2026-01_r43}"
KSU_TAG="${KSU_TAG:-v3.3.1}"
# Stock: 6.6.118-android15-8-gb9cc6ec16bc8-abogki536571621-4k
# Kleaf builds "-android15-8" + this + CONFIG_LOCALVERSION ("-4k").
STOCK_SCMVERSION="${STOCK_SCMVERSION:--gb9cc6ec16bc8-abogki536571621}"
STOCK_RELEASE="${STOCK_RELEASE:-6.6.118-android15-8-gb9cc6ec16bc8-abogki536571621-4k}"
AK3_COMMIT="${AK3_COMMIT:-c072981836cd3ee46ad52a5f2cba76ecb927cb1b}"
JOBS="${JOBS:-3}"
HERE="$(cd "$(dirname "$0")" && pwd)"
mkdir -p "$DIST" "$REPORTS" "$OUT"

case "${1:-}" in
  prepare)
    mkdir -p "$ROOT"
    cd "$ROOT"
    repo init -u https://android.googlesource.com/kernel/manifest -b "$MANIFEST_BRANCH" --depth=1
    repo sync -c --no-tags --fail-fast --no-clone-bundle -j "$JOBS"
    test -e common/.git || { echo 'Missing common kernel tree'; exit 1; }
    # repo-managed Git checkouts may not have an "origin" remote.
    # Fetch the pinned upstream tag directly from its canonical URL.
    git -C common fetch --depth=1 https://android.googlesource.com/kernel/common "refs/tags/$GKI_TAG:refs/tags/$GKI_TAG"
    git -C common checkout --detach "refs/tags/$GKI_TAG"
    grep -qx 'SUBLEVEL = 118' common/Makefile || { echo "$GKI_TAG is not 6.6.118" >&2; exit 1; }
    git -C common rev-parse HEAD | tee "$REPORTS/gki.commit"
    git -C common describe --always --tags | tee "$REPORTS/gki.tag"
    df -h "$ROOT"
    ;;
  patch)
    test -d "$ROOT/common/drivers" || { echo 'Run prepare first'; exit 1; }
    cd "$ROOT"
    # Same uname -r / vermagic as stock instead of "-maybe-dirty".
    stamp=build/kernel/kleaf/impl/stamp.bzl
    grep -Fq "stable_scmversion_cmd = \"echo '-maybe-dirty'\"" "$stamp"
    sed -i "s|stable_scmversion_cmd = \"echo '-maybe-dirty'\"|stable_scmversion_cmd = \"echo '$STOCK_SCMVERSION'\"|" "$stamp"
    grep -Fq "echo '$STOCK_SCMVERSION'" "$stamp"
    grep -qx 'CONFIG_LOCALVERSION="-4k"' common/arch/arm64/configs/gki_defconfig
    # The two Xiaomi-private F2FS vendor hooks still missing from public GKI.
    python3 "$HERE/add_xiaomi_hooks.py" common
    git -C common diff > "$REPORTS/xiaomi_hooks.patch"
    git -C build/kernel diff > "$REPORTS/stamp.patch"
    ;;
  integrate)
    test -d "$ROOT/common/drivers" || { echo 'Run prepare first'; exit 1; }
    cd "$ROOT"
    if [ ! -d KernelSU/.git ]; then
      git clone --filter=blob:none --branch "$KSU_TAG" https://github.com/tiann/KernelSU.git KernelSU
    fi
    test "$(git -C KernelSU describe --exact-match --tags 2>/dev/null)" = "$KSU_TAG"
    git -C KernelSU rev-parse HEAD | tee "$REPORTS/kernelsu.commit"
    test -f KernelSU/kernel/Kbuild
    test -f KernelSU/kernel/Kconfig
    # Kleaf's sandbox omits git metadata and Kbuild otherwise uses KSU_VERSION=16.
    # Calculate the proper KernelSU release version before sandboxing.
    if [ "$(git -C KernelSU rev-parse --is-shallow-repository)" = true ]; then
      git -C KernelSU fetch --unshallow
    fi
    KSU_VERSION_COUNT="$(git -C KernelSU rev-list --count HEAD)"
    case "$KSU_VERSION_COUNT" in
      ''|*[!0-9]*) echo "Invalid KernelSU git revision count" >&2; exit 1 ;;
    esac
    KSU_COMPILED_VERSION="$((30000 + KSU_VERSION_COUNT))"
    test "$KSU_COMPILED_VERSION" -gt 30000
    grep -Fqx 'ccflags-y += -DKSU_VERSION=16' KernelSU/kernel/Kbuild || {
      echo "Unknown Kbuild version fallback; refusing blind patch" >&2
      exit 1
    }
    sed -i "s/^ccflags-y += -DKSU_VERSION=16$/ccflags-y += -DKSU_VERSION=$KSU_COMPILED_VERSION/" KernelSU/kernel/Kbuild
    printf '%s\n' "$KSU_COMPILED_VERSION" | tee "$REPORTS/kernelsu.version"
    echo "KernelSU Git count: $KSU_VERSION_COUNT; version: $KSU_COMPILED_VERSION"
    ln -sfn ../../KernelSU/kernel common/drivers/kernelsu
    if ! grep -Fq 'obj-$(CONFIG_KSU) += kernelsu/' common/drivers/Makefile; then
      printf '\nobj-$(CONFIG_KSU) += kernelsu/\n' >> common/drivers/Makefile
    fi
    if ! grep -Fq 'source "drivers/kernelsu/Kconfig"' common/drivers/Kconfig; then
      python3 - <<'PY'
from pathlib import Path
p=Path('common/drivers/Kconfig')
s=p.read_text()
needle='endmenu'
idx=s.rfind(needle)
entry='source "drivers/kernelsu/Kconfig"\n'
p.write_text(s[:idx]+entry+s[idx:] if idx>=0 else s+'\n'+entry)
PY
    fi
    cfg=common/arch/arm64/configs/gki_defconfig
    test -f "$cfg"
    # KernelSU v3.3.1 declares CONFIG_KSU with "default y".
    # gki_defconfig is a *minimal* savedefconfig; adding a default-y
    # option makes Kleaf reject the resulting config as noncanonical.
    # Do not disable the check_defconfig gate or alter KernelSU defaults.
    sed -i '/^CONFIG_KSU=/d; /^# CONFIG_KSU is not set/d' "$cfg"
    grep -Fq 'source "drivers/kernelsu/Kconfig"' common/drivers/Kconfig
    grep -Fq 'obj-$(CONFIG_KSU) += kernelsu/' common/drivers/Makefile
    grep -q '^[[:space:]]*default y' KernelSU/kernel/Kconfig
    readlink -f common/drivers/kernelsu | grep -Fx "$(realpath KernelSU/kernel)"
    git -C common diff -- drivers/Kconfig drivers/Makefile arch/arm64/configs/gki_defconfig > "$REPORTS/integration.patch"
    ;;
  build)
    cd "$ROOT"
    test -x tools/bazel || { echo 'Kleaf tools/bazel not found'; exit 1; }
    set -o pipefail
    tools/bazel run //common:kernel_aarch64_dist -- "--destdir=$DIST" 2>&1 | tee "$REPORTS/bazel.log"
    test -s "$DIST/Image" || { echo 'Missing Image'; exit 1; }
    ;;
  verify)
    test -s "$DIST/Image" || { echo 'No Image, cannot verify'; exit 1; }
    symvers="$DIST/Module.symvers"
    if [ ! -s "$symvers" ]; then
      symvers="$(find "$ROOT/out" -type f -name Module.symvers -size +100k -print -quit 2>/dev/null || true)"
    fi
    test -s "$symvers" || { echo 'Module.symvers not found' >&2; exit 1; }
    cp "$symvers" "$REPORTS/Module.symvers"
    python3 "$HERE/verify_build.py" "$DIST/Image" "$REPORTS/Module.symvers" "$STOCK_RELEASE" "$REPORTS/verify.json"
    ;;
  package)
    test -s "$DIST/Image" || { echo 'No Image, cannot package'; exit 1; }
    ak3="$ROOT/AnyKernel3"
    rm -rf "$ak3"
    git init -q "$ak3"
    git -C "$ak3" fetch -q --depth=1 https://github.com/osm0sis/AnyKernel3 "$AK3_COMMIT"
    git -C "$ak3" checkout -q FETCH_HEAD
    rm -rf "$ak3/.git" "$ak3/.github" "$ak3/README.md" "$ak3/modules" "$ak3/patch" "$ak3/ramdisk"
    cp "$HERE/anykernel.sh" "$ak3/anykernel.sh"
    cp "$DIST/Image" "$ak3/Image"
    ksu_ver="$(cat "$REPORTS/kernelsu.version")"
    zip_name="AK3-xuanyuan-${STOCK_RELEASE%%-android*}-KernelSU-${KSU_TAG}-${ksu_ver}.zip"
    (cd "$ak3" && zip -r9 "$OUT/$zip_name" . -x '.git*')
    cp "$DIST/Image" "$OUT/Image"
    (cd "$OUT" && sha256sum "$zip_name" Image | tee SHA256SUMS)
    ;;
  *)
    echo "Usage: $0 prepare|patch|integrate|build|verify|package"
    exit 2
    ;;
esac
