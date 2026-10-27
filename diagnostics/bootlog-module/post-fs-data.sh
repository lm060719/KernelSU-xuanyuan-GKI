#!/system/bin/sh
# Boot logger for the experimental kernel. Runs in KernelSU's post-fs-data stage.
#
# The stock kernel loads KernelSU as an LKM ("kernelsu" in /proc/modules); the
# test kernel has it built in. Only log the test kernel so a later stock boot
# cannot overwrite the logs of the failed boot.
grep -q '^kernelsu ' /proc/modules && exit 0

BASE=/data/local/tmp/xuanyuan_bootlog
D=$BASE/boot_$(date +%Y%m%d_%H%M%S)
mkdir -p "$D"

{
  echo "stage=post-fs-data date=$(date)"
  cat /proc/version
  cat /proc/cmdline
  cat /proc/uptime
} > "$D/info.txt" 2>&1
/system/bin/dmesg > "$D/dmesg_post-fs-data.txt" 2>&1
cat /proc/modules > "$D/modules_post-fs-data.txt" 2>&1
cat /proc/mounts > "$D/mounts_post-fs-data.txt" 2>&1
getprop > "$D/getprop_post-fs-data.txt" 2>&1
sync

# post-fs-data blocks boot, so record the rest in the background for 10 minutes.
(
  /system/bin/dmesg -w > "$D/dmesg_stream.txt" 2>&1 &
  dmesg_pid=$!
  (
    # logd may not be ready yet; keep retrying until the time limit.
    while :; do
      /system/bin/logcat -b all -v threadtime >> "$D/logcat.txt" 2>&1
      sleep 2
    done
  ) &
  logcat_pid=$!

  i=0
  while [ $i -lt 60 ]; do
    sleep 10
    i=$((i + 1))
    echo "t=$((i * 10))s boot_completed=$(getprop sys.boot_completed)" \
      "bootanim=$(getprop init.svc.bootanim) zygote=$(getprop init.svc.zygote)" \
      "surfaceflinger=$(getprop init.svc.surfaceflinger)" \
      "system_server=$(pidof system_server)" >> "$D/progress.txt"
    sync
  done

  cat /proc/modules > "$D/modules_end.txt" 2>&1
  /system/bin/dmesg > "$D/dmesg_end.txt" 2>&1
  getprop > "$D/getprop_end.txt" 2>&1
  ls -l /data/tombstones > "$D/tombstones_list.txt" 2>&1
  mkdir -p "$D/tombstones" && cp /data/tombstones/tombstone_* "$D/tombstones/" 2>/dev/null
  kill "$logcat_pid" "$dmesg_pid" 2>/dev/null
  pkill -f 'logcat -b all -v threadtime' 2>/dev/null
  echo "done date=$(date)" >> "$D/info.txt"
  sync
) > /dev/null 2>&1 &

exit 0
