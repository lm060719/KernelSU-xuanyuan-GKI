#!/system/bin/sh
# Experiment for the test kernel only: boot without zram swap, to check whether
# the stock-built zram/zsmalloc modules and Xiaomi's boot-time swap/prepage
# corrupt anonymous memory under the AOSP GKI kernel.
#
# The stock kernel loads KernelSU as an LKM ("kernelsu" in /proc/modules);
# leave it untouched.
grep -q '^kernelsu ' /proc/modules && exit 0

LOG=/data/local/tmp/xuanyuan_bootlog/noswap_$(date +%Y%m%d_%H%M%S).txt
mkdir -p /data/local/tmp/xuanyuan_bootlog

# post-fs-data runs before zram is sized (~7 s after boot). Hiding the zram0
# sysfs directory makes disksize/initstate writes land in a tmpfs, so the
# device stays at 0 bytes and swapon fails.
Z=/sys/devices/virtual/block/zram0
{
  echo "date=$(date) uptime=$(cat /proc/uptime)"
  cat $Z/disksize $Z/initstate 2>&1
  mount -t tmpfs -o size=1m,mode=0755 none "$Z" && echo "zram0 sysfs hidden" || echo "mount failed"
  cat /proc/swaps
} > "$LOG" 2>&1

# Record whether swap still came up, and turn it off if it did.
(
  i=0
  while [ $i -lt 60 ]; do
    sleep 2
    i=$((i + 1))
    if grep -q zram /proc/swaps; then
      echo "t=$((i * 2))s swap active, swapoff" >> "$LOG"
      swapoff /dev/block/zram0 >> "$LOG" 2>&1
    fi
  done
  {
    echo "end uptime=$(cat /proc/uptime)"
    cat /proc/swaps
    grep -E '^Swap' /proc/meminfo
  } >> "$LOG" 2>&1
  sync
) > /dev/null 2>&1 &

exit 0
