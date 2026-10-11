#!/usr/bin/env python3
# Copyright (C) 2026 h0nda1337
# SPDX-License-Identifier: AGPL-3.0-only
"""Prepare a local OEM-permission candidate for the exact FRP format tested.

Never connects to a device or executes a flashing command.
"""

import argparse
import hashlib
import json
import struct
from pathlib import Path

FRP_SIZE = 0x100000
FRP_MAGIC = 0x19901873
DIGEST_SIZE = 32


def digest(block: bytes) -> bytes:
    return hashlib.sha256(bytes(DIGEST_SIZE) + block[DIGEST_SIZE:]).digest()


def prepare(original: bytes, independent_copy: bytes) -> bytes:
    if original != independent_copy:
        raise ValueError('Independent backups differ; stop and obtain verified copies.')
    if len(original) != FRP_SIZE:
        raise ValueError('Expected the tested 1 MiB FRP block; other layouts are unsupported.')
    if original[:DIGEST_SIZE] != digest(original):
        raise ValueError('Original FRP checksum is invalid; do not modify it.')
    magic, data_length = struct.unpack_from('>II', original, DIGEST_SIZE)
    if magic != FRP_MAGIC:
        raise ValueError('Unknown persistent-data-block header.')
    if data_length != 0:
        raise ValueError('FRP data block is not empty; this case is unsupported.')
    if original[-1] != 0:
        raise ValueError('Expected disabled OEM permission (last byte 0).')
    candidate = bytearray(original)
    candidate[-1] = 1
    candidate[:DIGEST_SIZE] = digest(candidate)
    return bytes(candidate)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('original', type=Path)
    parser.add_argument('independent_copy', type=Path)
    parser.add_argument('output', type=Path)
    parser.add_argument('--enable-oem-unlock', action='store_true',
                        help='Explicitly request an offline OEM-permission candidate.')
    args = parser.parse_args()
    if not args.enable_oem_unlock:
        parser.error('Pass --enable-oem-unlock to explicitly request this change.')
    try:
        original = args.original.read_bytes()
        candidate = prepare(original, args.independent_copy.read_bytes())
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with args.output.open('xb') as handle:
            handle.write(candidate)
    except (OSError, ValueError) as error:
        parser.exit(2, f'Refused: {error}\n')
    print(json.dumps({
        'prepared': True,
        'device_writes': False,
        'bytes': len(candidate),
        'original_sha256': hashlib.sha256(original).hexdigest(),
        'candidate_sha256': hashlib.sha256(candidate).hexdigest(),
        'changed_fields': ['checksum bytes 0..31', 'OEM permission last byte 0 -> 1'],
    }, indent=2))


if __name__ == '__main__':
    main()
