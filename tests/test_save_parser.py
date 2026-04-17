"""Testes para src.save_parser - funcoes puras de parsing binario."""

import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from save_parser import _read_float32, _read_uint32


def test_read_uint32_little_endian():
    data = struct.pack("<I", 42)
    assert _read_uint32(data, 0) == 42


def test_read_uint32_retorna_zero_se_offset_fora_dos_limites():
    data = b"\x01\x02"
    assert _read_uint32(data, 0) == 0
    assert _read_uint32(data, 100) == 0


def test_read_float32_little_endian():
    data = struct.pack("<f", 3.14)
    resultado = _read_float32(data, 0)
    assert abs(resultado - 3.14) < 0.01


def test_read_float32_retorna_zero_se_offset_fora_dos_limites():
    data = b"\x01\x02"
    assert _read_float32(data, 0) == 0.0
    assert _read_float32(data, 100) == 0.0


def test_read_uint32_usa_offset_corretamente():
    data = struct.pack("<II", 10, 20)
    assert _read_uint32(data, 0) == 10
    assert _read_uint32(data, 4) == 20


def test_read_float32_usa_offset_corretamente():
    data = struct.pack("<ff", 1.5, 2.5)
    assert abs(_read_float32(data, 0) - 1.5) < 0.001
    assert abs(_read_float32(data, 4) - 2.5) < 0.001
