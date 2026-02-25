#!/usr/bin/env python3
"""Build mm_sprint.tap with animated loading screen from original MANIC.TAP.

Assembles a TAP file containing:
  1. BASIC loader (CLEAR 32764, PAPER 0: INK 0: CLS, two LOAD ""CODE, USR 33792)
  2. "mmm" screen attributes block (256 bytes at 0x5900) - extracted from MANIC.TAP
  3. Game code block (32771 bytes at 0x7FFD) - from mm_sprint.bin

The "mmm" block loads colour attributes before the main code, so the animated
border stripes and attribute colours are visible during loading (as in the original).
"""

import hashlib
import struct
import sys
import os

MANIC_TAP = "MANIC.TAP"
SPRINT_BIN = "mm_sprint.bin"
OUTPUT_TAP = "mm_sprint.tap"
OUTPUT_IPS = "mm_sprint.ips"

EXPECTED_BIN_SIZE = 32771
LOAD_ADDR = 0x7FFD

# SHA-256 of the expected MANIC.TAP (Software Projects release)
MANIC_TAP_SHA256 = "0229ca09bb87c58024d68b05a6a5ecd8ac93fb4932d937883722467f86277f4e"


def tap_checksum(data: bytes) -> int:
    """XOR checksum over all bytes."""
    cs = 0
    for b in data:
        cs ^= b
    return cs


def make_tap_block(data: bytes) -> bytes:
    """Wrap data in a TAP block (2-byte LE length prefix)."""
    return struct.pack("<H", len(data)) + data


def make_header_block(data_type: int, name: str, data_len: int,
                      param1: int, param2: int) -> bytes:
    """Create a TAP header block (flag=0x00, 17 payload bytes + checksum)."""
    name_padded = name.ljust(10)[:10].encode("ascii")
    payload = struct.pack("<B B 10s H H H",
                          0x00,        # flag: header
                          data_type,   # 0=program, 3=bytes
                          name_padded,
                          data_len,
                          param1,
                          param2)
    return make_tap_block(payload + bytes([tap_checksum(payload)]))


def make_data_block(data: bytes) -> bytes:
    """Create a TAP data block (flag=0xFF, data, checksum)."""
    payload = b'\xFF' + data
    return make_tap_block(payload + bytes([tap_checksum(payload)]))


def make_basic_loader() -> bytes:
    """Create the BASIC program:
        10 CLEAR 32764
        20 PAPER 0: INK 0: CLS: LOAD ""CODE: LOAD ""CODE
        30 RANDOMIZE USR 33792
    """
    lines = []

    # Line 10: CLEAR 32764
    body = bytes([0xFD,                          # CLEAR token
                  0x0E]) + b"32764" + bytes([    # number as text
                  0x0E, 0x00, 0x00, 0xFC, 0x7F, 0x00,  # 5-byte number (32764)
                  0x0D])                         # end of line
    lines.append(struct.pack(">H", 10) + struct.pack("<H", len(body)) + body)

    # Line 20: PAPER 0: INK 0: CLS: LOAD ""CODE: LOAD ""CODE
    body = bytearray()
    body += bytes([0xDA])           # PAPER token
    body += b"0"
    body += bytes([0x0E, 0x00, 0x00, 0x00, 0x00, 0x00])  # 5-byte number (0)
    body += bytes([0x3A])           # : separator
    body += bytes([0xD9])           # INK token
    body += b"0"
    body += bytes([0x0E, 0x00, 0x00, 0x00, 0x00, 0x00])  # 5-byte number (0)
    body += bytes([0x3A])           # :
    body += bytes([0xFB])           # CLS token
    body += bytes([0x3A])           # :
    body += bytes([0xEF])           # LOAD token
    body += bytes([0x22, 0x22])     # ""
    body += bytes([0xAF])           # CODE token
    body += bytes([0x3A])           # :
    body += bytes([0xEF])           # LOAD token
    body += bytes([0x22, 0x22])     # ""
    body += bytes([0xAF])           # CODE token
    body += bytes([0x0D])           # end of line
    lines.append(struct.pack(">H", 20) + struct.pack("<H", len(body)) + bytes(body))

    # Line 30: RANDOMIZE USR 33792
    body = bytes([0xF9,                          # RANDOMIZE token
                  0xC0,                          # USR token
                  ]) + b"33792" + bytes([        # number as text
                  0x0E, 0x00, 0x00, 0x00, 0x84, 0x00,  # 5-byte number (33792)
                  0x0D])                         # end of line
    lines.append(struct.pack(">H", 30) + struct.pack("<H", len(body)) + body)

    return b"".join(lines)


def extract_mmm_blocks(manic_data: bytes) -> bytes:
    """Extract the "mmm" header+data TAP blocks from MANIC.TAP."""
    # Parse TAP blocks
    off = 0
    blocks = []
    while off < len(manic_data):
        blen = manic_data[off] | (manic_data[off + 1] << 8)
        blocks.append((off, blen))
        off += 2 + blen

    # Blocks 2+3 are the mmm header and data
    if len(blocks) < 4:
        print("ERROR: MANIC.TAP doesn't have enough blocks", file=sys.stderr)
        sys.exit(1)

    mmm_start = blocks[2][0]
    mmm_end = blocks[3][0] + 2 + blocks[3][1]
    return manic_data[mmm_start:mmm_end]


def make_ips_patch(original: bytes, modified: bytes) -> bytes:
    """Create an IPS patch that transforms original into modified.

    IPS format:
      "PATCH" header
      Records: 3-byte BE offset, 2-byte BE size, data bytes
      "EOF" footer
    """
    patch = bytearray(b"PATCH")
    max_len = max(len(original), len(modified))

    # Pad the shorter file with zeros for comparison
    orig = original.ljust(max_len, b'\x00')
    mod = modified.ljust(max_len, b'\x00')

    i = 0
    while i < len(mod):
        # Skip matching bytes
        if i < len(orig) and orig[i] == mod[i]:
            i += 1
            continue

        # Found a difference - collect the run of differing bytes
        start = i
        while i < len(mod) and (i >= len(orig) or orig[i] != mod[i]):
            i += 1
            # Also absorb short matching gaps (< 6 bytes) to avoid record overhead
            if i < len(mod) and i < len(orig):
                gap = 0
                while i + gap < len(mod) and i + gap < len(orig) and orig[i + gap] == mod[i + gap]:
                    gap += 1
                if 0 < gap < 6:
                    i += gap

        # Write records (split at 0xFFFF max record size)
        data = mod[start:i]
        offset = start
        while len(data) > 0:
            chunk = data[:0xFFFF]
            data = data[len(chunk):]
            patch += struct.pack(">I", offset)[1:]  # 3-byte BE offset
            patch += struct.pack(">H", len(chunk))   # 2-byte BE size
            patch += chunk
            offset += len(chunk)

    # If modified is longer, the extra bytes are already handled above.
    # If modified is shorter, IPS can't truncate (limitation of format),
    # but our modified file is larger so this isn't an issue.

    patch += b"EOF"
    return bytes(patch)


def main():
    os.chdir(os.path.dirname(os.path.abspath(__file__)) or ".")

    # Read inputs
    if not os.path.exists(MANIC_TAP):
        print(f"ERROR: {MANIC_TAP} not found", file=sys.stderr)
        sys.exit(1)
    if not os.path.exists(SPRINT_BIN):
        print(f"ERROR: {SPRINT_BIN} not found", file=sys.stderr)
        sys.exit(1)

    manic_data = open(MANIC_TAP, "rb").read()
    bin_data = open(SPRINT_BIN, "rb").read()

    # Verify MANIC.TAP is the expected version
    actual_sha = hashlib.sha256(manic_data).hexdigest()
    if actual_sha != MANIC_TAP_SHA256:
        print(f"ERROR: {MANIC_TAP} does not match expected SHA-256", file=sys.stderr)
        print(f"  Expected: {MANIC_TAP_SHA256}", file=sys.stderr)
        print(f"  Got:      {actual_sha}", file=sys.stderr)
        print(f"  The IPS patch requires the Software Projects TAP release.", file=sys.stderr)
        sys.exit(1)

    if len(bin_data) != EXPECTED_BIN_SIZE:
        print(f"WARNING: {SPRINT_BIN} is {len(bin_data)} bytes, expected {EXPECTED_BIN_SIZE}",
              file=sys.stderr)

    # Build BASIC loader
    basic = make_basic_loader()
    basic_header = make_header_block(0, "ManicMiner", len(basic), 10, len(basic))
    basic_data = make_data_block(basic)

    # Extract mmm blocks from original TAP (already in TAP format with length prefixes)
    mmm_blocks = extract_mmm_blocks(manic_data)

    # Build game code blocks
    code_header = make_header_block(3, "mm1", len(bin_data), LOAD_ADDR, 0x8000)
    code_data = make_data_block(bin_data)

    # Assemble final TAP
    tap = basic_header + basic_data + mmm_blocks + code_header + code_data
    open(OUTPUT_TAP, "wb").write(tap)
    print(f"Created {OUTPUT_TAP} ({len(tap)} bytes)")

    # Generate IPS patch (MANIC.TAP -> mm_sprint.tap)
    ips = make_ips_patch(manic_data, tap)
    open(OUTPUT_IPS, "wb").write(ips)
    print(f"Created {OUTPUT_IPS} ({len(ips)} bytes)")


if __name__ == "__main__":
    main()
