#!/usr/bin/env python3
"""Read HBR and PCR records from a bz2 STDF file and print HBR info + yield."""

import sys

from stdf_analyzer.parser import parse_hbr_pcr


def _fmt_head(h):
    return "ALL" if h == 255 else str(h)


def _bin_pf(pf):
    if pf == 1:
        return "PASS"
    if pf == 0:
        return "FAIL"
    return ""


def main():
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} <path-to-bz2-file>")
        sys.exit(1)

    bz2_path = sys.argv[1]
    print(f"Opening: {bz2_path}")

    pcr_list, hbr_list = parse_hbr_pcr(bz2_path)

    total_parts = sum(p.part_cnt for p in pcr_list)
    total_good = sum(p.good_cnt for p in pcr_list)
    yield_pct = (total_good / total_parts * 100) if total_parts else 0.0

    sep = "=" * 60
    print(f"\n{sep}")
    print("HBR ANALYSIS (from PCR + HBR records)")
    print(sep)

    print(f"\n--- Hardware Bin Summary (HBR) ---")
    if hbr_list:
        hbr_sorted = sorted(hbr_list, key=lambda r: r.hbin_num)
        total_hbr = 0
        for hbr in hbr_sorted:
            head = _fmt_head(hbr.head_num)
            pf = _bin_pf(hbr.hbin_pf)
            name = hbr.hbin_nam or ""
            total_hbr += hbr.hbin_cnt
            print(f"    H={head} S={hbr.site_num}  Bin={hbr.hbin_num:>4}  Count={hbr.hbin_cnt:>6}  {pf:>4}  {name}")
        print(f"    {'Total':>19}  Count={total_hbr:>6}")
    else:
        print("  (none)")

    print(f"\n  Total parts (from PCR): {total_parts}")
    print(f"  Total good  (from PCR): {total_good}")
    print(f"  Yield                : {yield_pct:.2f}%")

    print(f"\n{sep}")
    print("Analysis complete.")
    print(sep)


if __name__ == "__main__":
    main()
