#!/usr/bin/env python3
# Copyright (C) 2026 h0nda1337
# SPDX-License-Identifier: AGPL-3.0-only
"""Audit the exact UFS boot1 relocation observed in the CPH2205 F.72 case.

Does not create a patch, verify a vendor signature, or connect to a device.
"""

import argparse
import hashlib
import json
import struct
from pathlib import Path

BOOT_SIZE = 0x400000
OLD_OFFSET = 0x1000
NEW_OFFSET = 0x2000
ROMINFO_OFFSET = 0x12EC
RAW_SIZE = 353444
HEADER_CHANGES = {
    0x20D: 0x20, 0x21D: 0x20,
    0x211: 0x10, 0x212: 0x10,
    0x221: 0x10, 0x222: 0x10,
}


def require(condition: bool, reason: str) -> None:
    if not condition:
        raise ValueError(reason)


def audit(original: bytes, independent_copy: bytes, extracted: bytes,
          candidate: bytes) -> dict:
    require(original == independent_copy, 'Independent boot1 backups differ.')
    require(len(original) == BOOT_SIZE and len(candidate) == BOOT_SIZE,
            'Both boot1 files must have the tested 4 MiB size.')
    require(original.startswith(b'UFS_BOOT'), 'Expected UFS_BOOT.')
    require(original[0x200:0x205] == b'BRLYT', 'Missing BRLYT header.')
    require(struct.unpack_from('<I', original, 0x20C)[0] == OLD_OFFSET,
            'Unexpected original preloader offset.')
    require(not any(original[-0x3000:]), 'Relocation would discard nonzero tail data.')
    require(original.find(b'AND_ROMINFO_v') == ROMINFO_OFFSET,
            'Unexpected ROMINFO location; only the tested layout is supported.')
    require(original[ROMINFO_OFFSET + 0x4C] == 0x22,
            'Unexpected original Fastboot flag.')
    require(len(extracted) == RAW_SIZE and extracted.startswith(b'MMM\x01'),
            'Extracted RAW preloader does not have the tested header/size.')
    raw_offset = original.find(extracted)
    require(raw_offset == OLD_OFFSET, 'Extracted preloader differs from original boot1.')

    header = bytearray(original[:OLD_OFFSET])
    for address, value in HEADER_CHANGES.items():
        header[address] = value
    require(candidate[:OLD_OFFSET] == header, 'Unexpected changes in the boot1 header.')
    flag = bytearray(original[ROMINFO_OFFSET:ROMINFO_OFFSET + 0x78])
    flag[0x4C] = 0
    require(candidate[OLD_OFFSET:OLD_OFFSET + 0x78] == flag,
            'Relocated ROMINFO differs from the expected Fastboot flag change.')
    require(not any(candidate[OLD_OFFSET + 0x78:NEW_OFFSET]),
            'Unexpected bytes between ROMINFO and relocated preloader.')
    moved = original[OLD_OFFSET:BOOT_SIZE - 0x3000]
    require(candidate[NEW_OFFSET:NEW_OFFSET + len(moved)] == moved,
            'Relocated original region changed; reject this candidate.')
    require(candidate[NEW_OFFSET:NEW_OFFSET + RAW_SIZE] == extracted,
            'Extracted preloader changed after relocation.')
    require(not any(candidate[NEW_OFFSET + len(moved):]),
            'Unexpected data after relocated region.')
    return {
        'audit_passed': True,
        'device_writes': False,
        'vendor_signature_cryptographically_verified': False,
        'extracted_preloader_identical': True,
        'original_offset': OLD_OFFSET,
        'candidate_offset': NEW_OFFSET,
        'bytes': BOOT_SIZE,
        'original_sha256': hashlib.sha256(original).hexdigest(),
        'candidate_sha256': hashlib.sha256(candidate).hexdigest(),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('original', type=Path)
    parser.add_argument('independent_copy', type=Path)
    parser.add_argument('extracted_preloader', type=Path)
    parser.add_argument('candidate', type=Path)
    args = parser.parse_args()
    try:
        result = audit(args.original.read_bytes(), args.independent_copy.read_bytes(),
                       args.extracted_preloader.read_bytes(), args.candidate.read_bytes())
    except (OSError, ValueError) as error:
        parser.exit(2, f'Refused: {error}\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
