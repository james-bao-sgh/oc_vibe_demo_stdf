#!/usr/bin/env python3
"""Fast STDF yield from HBR records. Prints bin summary + yield."""

import bz2
import struct
import sys


def _cn(buf, pos, end):
    if pos >= end:
        return None, pos
    slen = buf[pos]
    pos += 1
    if slen == 0 or pos + slen > end:
        return None, pos
    return buf[pos:pos + slen].decode('ascii', errors='replace'), pos + slen


def _pf_label(pf: int) -> str:
    if pf == 1:
        return "PASS"
    if pf == 0:
        return "FAIL"
    return ""


def _head_label(h: int) -> str:
    return "ALL" if h == 255 else str(h)


def main() -> None:
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} <path-to-bz2-file>")
        sys.exit(1)

    path = sys.argv[1]

    with bz2.open(path, "rb") as f:
        buf = f.read()

    endian = '>' if len(buf) > 4 and buf[4] == 1 else '<'

    bins = []
    pos = 0
    n = len(buf)

    while pos + 4 <= n:
        rec_len, rec_typ, rec_sub = struct.unpack_from(endian + 'HBB', buf, pos)
        pos += 4
        data_end = pos + rec_len

        if rec_typ == 1 and rec_sub == 40:  # HBR
            if pos + 8 <= data_end:
                head_num = struct.unpack_from(endian + 'B', buf, pos)[0]
                site_num = struct.unpack_from(endian + 'B', buf, pos + 1)[0]
                hbin_num = struct.unpack_from(endian + 'H', buf, pos + 2)[0]
                hbin_cnt = struct.unpack_from(endian + 'I', buf, pos + 4)[0]
                hbin_pf = struct.unpack_from(endian + 'B', buf, pos + 8)[0]
                hbin_nam, _ = _cn(buf, pos + 9, data_end)
                bins.append((head_num, site_num, hbin_num, hbin_cnt, hbin_pf, hbin_nam or ""))

        pos = data_end

    if not bins:
        print("No HBR records found.")
        return

    bins.sort(key=lambda b: b[2])  # sort by bin number

    print(f"\n{'--- Hardware Bin Summary (HBR) ---':^60}")
    total_cnt = 0
    for head, site, num, cnt, pf, name in bins:
        total_cnt += cnt
        print(f"    H={_head_label(head)} S={site}  Bin={num:>4}  Count={cnt:>6}  {_pf_label(pf):>4}  {name}")
    print(f"    {'Total':>19}  Count={total_cnt:>6}")

    bin1_cnt = next((c for h, s, n, c, p, na in bins if n == 1), 0)
    yield_pct = (bin1_cnt / total_cnt * 100) if total_cnt else 0.0
    print(f"\n    Bin1 (pass): {bin1_cnt}")
    print(f"    Yield:       {yield_pct:.2f}%")


if __name__ == "__main__":
    main()
