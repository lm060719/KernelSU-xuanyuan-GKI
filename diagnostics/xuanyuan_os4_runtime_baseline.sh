#!/system/bin/sh
# Xiaomi 15 Ultra / HyperOS 4 root mode & module baseline: READ ONLY.
# No flash, remount, reboot, insmod, property changes or log deletion.
set -u
OUT="/sdcard/Download/xuanyuan_OS4_root_module_baseline_$(date '+%Y%m%d_%H%M%S').txt"
if [ "$(id -u 2>/dev/null)" != 0 ]; then
  echo '先输入 su 获得 root 权限，再通过 sh 执行本脚本。'
  exit 1
fi
{
  echo '=== Device ==='
  date '+%Y-%m-%d %H:%M:%S %z'
  echo 'device:'; getprop ro.product.device
  echo 'build:'; getprop ro.build.version.incremental
  echo 'kernel:'; uname -r
  echo 'slot:'; getprop ro.boot.slot_suffix
  echo '=== Root and LKM hints ==='
  id -Z 2>/dev/null || true
  ps -A -o NAME 2>/dev/null | grep -Ei '(^|/)(ksud|magiskd|apd)([[:space:]]|$)' | head -n 10 || true
  for p in /sys/module/kernelsu /sys/module/ksu /sys/module/ksu_lkm /data/adb/ksu /data/adb/magisk; do
    if [ -e "$p" ]; then echo "present: $p"; else echo "absent: $p"; fi
  done
  echo '=== Actually loaded modules ==='
  if [ -r /proc/modules ]; then
    echo 'count:'; wc -l < /proc/modules
    awk '{print $1}' /proc/modules | grep -Ei 'ksu|kernelsu|susfs|apatch|magisk' || true
    echo 'first 40 loaded names:'; awk 'NR<=40 {print $1}' /proc/modules
  fi
  echo '=== modules.load baseline ==='
  M=/vendor_dlkm/lib/modules/modules.load
  if [ -r "$M" ] && [ -r /proc/modules ]; then
    awk 'NR==FNR{a[$1]=1;next} /^[[:space:]]*($|#)/{next} {s=$1;sub(/^.*\//,"",s);sub(/\.ko([[:space:]].*)?$/,"",s);gsub(/-/,"_",s);if(s=="")next;n++;if(a[s])yes++;else{no++;if(no<=35)b[no]=s}}END{print "listed="n", loaded="yes", not_in_proc_modules="no;for(i=1;i<=no&&i<=35;i++)print b[i]}' /proc/modules "$M"
  fi
  echo '=== Active boot / init_boot SHA256 only ==='
  SLOT="$(getprop ro.boot.slot_suffix)"
  case "$SLOT" in
    _a|_b) for part in boot init_boot; do
      DEV="/dev/block/by-name/${part}${SLOT}"
      if [ -r "$DEV" ]; then sha256sum "$DEV" 2>&1; else echo "unavailable: $DEV"; fi
    done;;
    *) echo 'Active slot unknown; hashes skipped';;
  esac
  echo '=== pstore filenames only ==='
  if [ -d /sys/fs/pstore ]; then ls -1 /sys/fs/pstore 2>&1 | head -n 20; fi
  echo '=== Limitations ==='
  echo 'Loaded-module absence is not always a load failure; some modules are optional.'
  echo 'A different kernel-version prefix in vermagic can be valid with CONFIG_MODVERSIONS.'
  echo 'To identify modifications to init_boot, compare its hash with exact same-firmware stock image.'
  echo 'No raw modules, partition images, private keys, or full logs were collected.'
} > "$OUT" 2>&1
echo "只读采集完成：$OUT"
