#!/usr/bin/env bash
set -Eeuo pipefail

# Experimental AOSP GKI + KernelSU built-in. NEVER flashes or repacks boot.
ROOT="${GKI_ROOT:-$PWD/gki}"
DIST="${DIST_DIR:-$PWD/dist}"
REPORTS="${REPORT_DIR:-$PWD/reports}"
MANIFEST_BRANCH="${MANIFEST_BRANCH:-common-android15-6.6-2026-01}"
GKI_TAG="${GKI_TAG:-android15-6.6-2026-01_r2}"
KSU_TAG="${KSU_TAG:-v3.3.1}"
JOBS="${JOBS:-3}"
mkdir -p "$DIST" "$REPORTS"

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
    echo "Kernel common remotes:"
    git -C common remote -v || true
    git -C common rev-parse HEAD | tee "$REPORTS/gki.commit"
    git -C common describe --always --tags | tee "$REPORTS/gki.tag"
    df -h "$ROOT"
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
    sed -i '/^CONFIG_KSU=/d; /^# CONFIG_KSU is not set/d' "$cfg"
    printf '\nCONFIG_KSU=y\n' >> "$cfg"
    grep -n 'CONFIG_KSU' "$cfg" | tee "$REPORTS/ksu.defconfig"
    git -C common diff -- drivers/Kconfig drivers/Makefile arch/arm64/configs/gki_defconfig > "$REPORTS/integration.patch"
    ;;
  build)
    cd "$ROOT"
    test -x tools/bazel || { echo 'Kleaf tools/bazel not found'; exit 1; }
    set -o pipefail
    tools/bazel run //common:kernel_aarch64_dist -- "--destdir=$DIST" 2>&1 | tee "$REPORTS/bazel.log"
    test -s "$DIST/Image" || { echo 'Missing Image'; exit 1; }
    ;;
  inspect)
    test -s "$DIST/Image" || { echo 'No Image, cannot inspect'; exit 1; }
    python3 "$(dirname "$0")/inspect_image.py" "$DIST/Image" "$REPORTS/inspection.json"
    ;;
  *)
    echo "Usage: $0 prepare|integrate|build|inspect"
    exit 2
    ;;
esac
