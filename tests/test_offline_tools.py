# SPDX-License-Identifier: AGPL-3.0-only
"""Synthetic rejection cases; no firmware or device connection is used."""

import importlib.util
import struct
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / 'tools' / f'{name}.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


oem = load('prepare_oem_permission')
preloader = load('audit_preloader')


def frp(data_length=0, magic=oem.FRP_MAGIC, last_byte=0):
    block = bytearray(oem.FRP_SIZE)
    struct.pack_into('>II', block, 32, magic, data_length)
    block[200:212] = b'KEEP-MY-DATA'
    block[-1] = last_byte
    block[:32] = oem.digest(block)
    return bytes(block)


class OemPermissionTests(unittest.TestCase):
    def test_preserves_every_byte_outside_checksum_and_permission(self):
        original = frp()
        candidate = oem.prepare(original, original)
        self.assertEqual(candidate[32:-1], original[32:-1])
        self.assertEqual(candidate[-1], 1)
        self.assertEqual(candidate[:32], oem.digest(candidate))

    def test_rejects_different_backup(self):
        original = frp()
        with self.assertRaises(ValueError):
            oem.prepare(original, original[:-1] + b'\x01')

    def test_rejects_corrupted_checksum(self):
        original = bytearray(frp())
        original[300] = 1
        with self.assertRaises(ValueError):
            oem.prepare(bytes(original), bytes(original))

    def test_rejects_nonempty_frp_data(self):
        original = frp(data_length=1)
        with self.assertRaises(ValueError):
            oem.prepare(original, original)

    def test_rejects_other_size_header_and_existing_permission(self):
        for original in (frp()[:-1], frp(magic=0), frp(last_byte=1)):
            with self.subTest(length=len(original), last=original[-1]):
                with self.assertRaises(ValueError):
                    oem.prepare(original, original)

    def test_cli_requires_explicit_flag_and_never_overwrites(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            original = root / 'original.bin'
            duplicate = root / 'copy.bin'
            output = root / 'candidate.bin'
            original.write_bytes(frp())
            duplicate.write_bytes(frp())
            args = [sys.executable, str(ROOT / 'tools/prepare_oem_permission.py'),
                    str(original), str(duplicate), str(output)]
            result = subprocess.run(args, capture_output=True)
            self.assertEqual(result.returncode, 2)
            self.assertFalse(output.exists())
            output.write_bytes(b'preserve-existing-file')
            result = subprocess.run(args + ['--enable-oem-unlock'], capture_output=True)
            self.assertEqual(result.returncode, 2)
            self.assertEqual(output.read_bytes(), b'preserve-existing-file')
            self.assertEqual(original.read_bytes(), frp())


class PreloaderAuditTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        original = bytearray(preloader.BOOT_SIZE)
        original[:8] = b'UFS_BOOT'
        original[0x200:0x205] = b'BRLYT'
        struct.pack_into('<I', original, 0x20C, preloader.OLD_OFFSET)
        original[0x1000:0x1004] = b'MMM\x01'
        original[0x12EC:0x12EC + 13] = b'AND_ROMINFO_v'
        original[0x12EC + 0x4C] = 0x22
        original[0x1800:0x180C] = b'SIGNED-BYTES'
        candidate = bytearray(preloader.BOOT_SIZE)
        candidate[:0x1000] = original[:0x1000]
        for address, value in preloader.HEADER_CHANGES.items():
            candidate[address] = value
        candidate[0x1000:0x1078] = original[0x12EC:0x12EC + 0x78]
        candidate[0x104C] = 0
        moved = original[0x1000:-0x3000]
        candidate[0x2000:0x2000 + len(moved)] = moved
        cls.original = bytes(original)
        cls.candidate = bytes(candidate)
        cls.raw = cls.original[0x1000:0x1000 + preloader.RAW_SIZE]

    def test_accepts_exact_relocation(self):
        result = preloader.audit(self.original, self.original, self.raw, self.candidate)
        self.assertTrue(result['audit_passed'])
        self.assertFalse(result['vendor_signature_cryptographically_verified'])

    def test_rejects_changed_relocated_code(self):
        candidate = bytearray(self.candidate)
        candidate[0x2800] ^= 1
        with self.assertRaises(ValueError):
            preloader.audit(self.original, self.original, self.raw, bytes(candidate))

    def test_rejects_unexpected_header_change(self):
        candidate = bytearray(self.candidate)
        candidate[0x210] ^= 1
        with self.assertRaises(ValueError):
            preloader.audit(self.original, self.original, self.raw, bytes(candidate))

    def test_rejects_nonzero_discarded_tail(self):
        original = bytearray(self.original)
        original[-1] = 1
        with self.assertRaises(ValueError):
            preloader.audit(bytes(original), bytes(original), self.raw, self.candidate)

    def test_rejects_wrong_backup_and_raw(self):
        for duplicate, raw in ((b'', self.raw), (self.original, self.raw[:-1])):
            with self.assertRaises(ValueError):
                preloader.audit(self.original, duplicate, raw, self.candidate)

    def test_rejects_wrong_rominfo_flag(self):
        candidate = bytearray(self.candidate)
        candidate[0x104C] = 0x22
        with self.assertRaises(ValueError):
            preloader.audit(self.original, self.original, self.raw, bytes(candidate))


if __name__ == '__main__':
    unittest.main()
