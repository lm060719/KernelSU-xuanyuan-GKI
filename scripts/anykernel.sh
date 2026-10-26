### AnyKernel3 Ramdisk Mod Script
## osm0sis @ xda-developers

### AnyKernel setup
# global properties
properties() { '
kernel.string=GKI 6.6.118 + KernelSU built-in for Xiaomi 15 Ultra (xuanyuan) - EXPERIMENTAL
do.devicecheck=1
do.modules=0
do.systemless=0
do.cleanup=1
do.cleanuponabort=0
device.name1=xuanyuan
device.name2=
supported.versions=
supported.patchlevels=
supported.vendorpatchlevels=
'; } # end properties


### AnyKernel install
# boot shell variables
BLOCK=boot;
IS_SLOT_DEVICE=auto;
RAMDISK_COMPRESSION=auto;
# Never touch vbmeta: the bootloader checks the vbmeta blob embedded in boot.
PATCH_VBMETA_FLAG=0;

# import functions/variables and setup patching - see for reference (DO NOT REMOVE)
. tools/ak3-core.sh;

# boot install: GKI boot has no ramdisk, only replace the kernel and keep
# the stock header, patch level, cmdline and AVB footer.
split_boot;

flash_boot;
## end boot install
