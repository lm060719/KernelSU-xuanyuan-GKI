#!/usr/bin/env python3
"""Validate a plain AOSP GKI Image as a boot-failure control, not flash certification."""
import gzip
import hashlib
import json
from pathlib import Path
import re
import sys

REQUIRED_CONFIG = {
    'CONFIG_ARM64_4K_PAGES': 'y',
    'CONFIG_GKI_DYNAMIC_TASK_STRUCT_SIZE': 'y',
    'CONFIG_GKI_TASK_STRUCT_VENDOR_SIZE_MAX': '1024',
    'CONFIG_ARCH_WANTS_DYNAMIC_TASK_STRUCT': 'y',
    'CONFIG_MODVERSIONS': 'y',
    'CONFIG_MODULES': 'y',
}

def read_ikconfig(raw: bytes) -> str:
    marker = b'IKCFG_ST'
    start = raw.find(marker)
    if start < 0:
        raise ValueError('Kernel IKCONFIG start marker missing')
    start += len(marker)
    end = raw.find(b'IKCFG_ED', start)
    if end < 0:
        raise ValueError('Kernel IKCONFIG end marker missing')
    return gzip.decompress(raw[start:end]).decode('utf-8', 'replace')

def main() -> int:
    if len(sys.argv) != 3:
        print('Usage: inspect_vanilla_image.py Image report.json', file=sys.stderr)
        return 2
    raw = Path(sys.argv[1]).read_bytes()
    report_path = Path(sys.argv[2])
    version = re.search(rb'Linux version (6\.6\.118-android15-8[^\x00\r\n]{0,240})', raw)
    report = {
        'study': 'AOSP GKI 6.6.118 android15-8 r28 without KernelSU',
        'image_bytes': len(raw),
        'image_sha256': hashlib.sha256(raw).hexdigest(),
        'kernel_version': version.group(1).decode('utf-8', 'replace') if version else None,
        'stock_vendor_abi_verified': False,
        'safe_to_flash': False,
    }
    failures = []
    if not version:
        failures.append('Expected Linux 6.6.118-android15-8 banner missing')
    try:
        config_text = read_ikconfig(raw)
        config = dict(line.split('=', 1) for line in config_text.splitlines()
                      if line.startswith('CONFIG_') and '=' in line)
        actual = {k: config.get(k) for k in REQUIRED_CONFIG}
        report['config'] = actual
        report['CONFIG_KSU'] = config.get('CONFIG_KSU', 'unset')
        for key, expected in REQUIRED_CONFIG.items():
            if actual[key] != expected:
                failures.append(f'{key}: expected {expected!r}, got {actual[key]!r}')
        if config.get('CONFIG_KSU') in ('y', 'm'):
            failures.append('Control unexpectedly contains KernelSU: CONFIG_KSU is enabled')
    except (ValueError, EOFError, OSError) as exc:
        failures.append(f'Cannot parse IKCONFIG: {exc}')
    report['checks_passed'] = not failures
    report['failures'] = failures
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if failures:
        print('Vanilla control validation FAILED; image NOT for flashing.', file=sys.stderr)
        return 1
    print('Vanilla GKI control verified (static checks only, NOT for flashing).')
    return 0

if __name__ == '__main__':
    sys.exit(main())
