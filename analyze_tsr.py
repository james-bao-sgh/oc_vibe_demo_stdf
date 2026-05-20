#!/usr/bin/env python3
"""Read TSR (Test Synopsis Record) from a bz2 STDF file and export to CSV."""

import csv
import os
import sys

from stdf_analyzer.parser import parse_tsr


def main():
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} <path-to-bz2-file> [output.csv]")
        sys.exit(1)

    bz2_path = sys.argv[1]
    csv_path = sys.argv[2] if len(sys.argv) > 2 else bz2_path.replace(".bz2", "_tsr.csv")

    tsr_list = parse_tsr(bz2_path)

    if not tsr_list:
        print("No TSR records found.")
        return

    fields = [
        "test_num", "test_nam", "test_typ", "head_num", "site_num",
        "exec_cnt", "fail_cnt", "alrm_cnt",
        "seq_name", "test_lbl",
        "test_tim", "test_min", "test_max", "tst_sums", "tst_sqrs",
    ]

    with open(csv_path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(fields)
        for tsr in tsr_list:
            w.writerow([
                tsr.test_num,
                tsr.test_nam or "",
                tsr.test_typ,
                tsr.head_num if tsr.head_num != 255 else "ALL",
                tsr.site_num,
                tsr.exec_cnt,
                tsr.fail_cnt,
                tsr.alrm_cnt,
                tsr.seq_name or "",
                tsr.test_lbl or "",
                f"{tsr.test_tim:.4f}" if tsr.test_tim is not None else "",
                tsr.test_min if tsr.test_min is not None else "",
                tsr.test_max if tsr.test_max is not None else "",
                tsr.tst_sums if tsr.tst_sums is not None else "",
                tsr.tst_sqrs if tsr.tst_sqrs is not None else "",
            ])

    total_exec = sum(t.exec_cnt for t in tsr_list)
    total_fail = sum(t.fail_cnt for t in tsr_list)
    total_alrm = sum(t.alrm_cnt for t in tsr_list)

    print(f"Source   : {bz2_path}")
    print(f"Output   : {csv_path}")
    print(f"Records  : {len(tsr_list)}")
    print(f"Exec     : {total_exec}")
    print(f"Fails    : {total_fail}")
    print(f"Alarms   : {total_alrm}")
    print(f"File size: {os.path.getsize(csv_path):,} bytes")


if __name__ == "__main__":
    main()
